from rest_framework import serializers
from admin_master.models import AdminUser, State_master, City_master, StatusMaster
from .models import Manager_register
from team_head.models import TeamHead_register
from manager.models import Manager_register
from executive.models import Executive_register
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.db.models import Q
import re
from .models import (
    AdminUser,
    Manager_register,
    RefreshTokenStore,
)
from .utils import upload_to_s3
from multiRole.models import (
    BankAccount,
    AadhaarDetails
)
from multiRole.serializers import (
    BankDetailsReadSerializer, 
    AadhaarDetailsReadSerializer, 
    BankDetailsUpdateSerializer,
    AadhaarDetailsUpdateSerializer
)

class EmployeeRegisterSerializer(serializers.Serializer):
    # ---------------- AUTH ----------------
    email = serializers.EmailField()
    email_address = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    mobile_no = serializers.CharField()
    full_name = serializers.CharField()
    profile_image = serializers.ImageField(required=False)

    # ---------------- EMPLOYEE ----------------
    role = serializers.ChoiceField(choices=["manager", "team_head", "executive"])
    joining_date = serializers.DateField(required=False)
    employment_type = serializers.CharField(required=False)
    work_mode = serializers.CharField(required=False)
    branch = serializers.CharField(required=False)
    city = serializers.PrimaryKeyRelatedField(
        queryset=City_master.objects.all(), required=False
    )
    state = serializers.PrimaryKeyRelatedField(
        queryset=State_master.objects.all(), required=False
    )
    reporting_to = serializers.IntegerField(required=False, allow_null=True)

    # ---------------- BANK (optional) ----------------
    account_holder_name = serializers.CharField(required=False)
    bank_name = serializers.CharField(required=False)
    account_number = serializers.CharField(required=False)
    ifsc_code = serializers.CharField(required=False)

    # ---------------- AADHAAR (required) ----------------
    aadhaar_number = serializers.CharField(required=True)
    aadhaar_card_url = serializers.ImageField(required=True)

    def validate_ifsc_code(self, value):
        if not value:
            return value  # optional field

        value = value.strip().upper()
        pattern = r'^[A-Z]{4}0[A-Z0-9]{6}$'

        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Invalid IFSC code. It must be 11 characters (e.g. HDFC0001234)."
            )
        return value
    
    def validate_aadhaar_number(self, value):
        value = value.strip()

        if not value.isdigit() or len(value) != 12:
            raise serializers.ValidationError(
                "Aadhaar number must be exactly 12 digits."
            )

        if AadhaarDetails.objects.filter(aadhaar_number=value).exists():
            raise serializers.ValidationError(
                "Aadhaar number already exists."
            )

        return value

    def validate(self, data):
        # Strip all string fields
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = value.strip()

        email = data.get("email")
        mobile = data.get("mobile_no")
        email_address = data.get("email_address")
        role = data.get("role")
        reporting_to_id = data.get("reporting_to")

        # Check for duplicate email or mobile
        if AdminUser.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        if AdminUser.objects.filter(mobile_no=mobile).exists():
            raise serializers.ValidationError({"mobile_no": "Mobile number already exists"})

        # Role-based validation
        if role == "manager":
            if Manager_register.objects.filter(email_address=email_address).exists():
                raise serializers.ValidationError({"email_address": "Email_Address already exists"})
            if reporting_to_id and not AdminUser.objects.filter(id=reporting_to_id, role="admin").exists():
                raise serializers.ValidationError({"reporting_to": "Manager must report to an Admin"})
        elif role == "team_head":
            if TeamHead_register.objects.filter(email_address=email_address).exists():
                raise serializers.ValidationError({"email_address": "Email_Address already exists"})
            if not reporting_to_id:
                raise serializers.ValidationError({"reporting_to": "Team Head must report to a Manager"})
            if not Manager_register.objects.filter(id=reporting_to_id).exists():
                raise serializers.ValidationError({"reporting_to": "Invalid Manager selected"})
        elif role == "executive":
            if Executive_register.objects.filter(email_address=email_address).exists():
                raise serializers.ValidationError({"email_address": "Email_Address already exists"})
            if not reporting_to_id:
                raise serializers.ValidationError({"reporting_to": "Executive must report to a Team Head"})
            if not TeamHead_register.objects.filter(id=reporting_to_id).exists():
                raise serializers.ValidationError({"reporting_to": "Invalid Team Head selected"})

        # BANK validation (optional but complete)
        bank_fields = ["account_holder_name", "bank_name", "account_number", "ifsc_code"]
        if any(data.get(f) for f in bank_fields):
            missing = [f for f in bank_fields if not data.get(f)]
            if missing:
                raise serializers.ValidationError({"bank_account": f"Missing bank fields: {', '.join(missing)}"})

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        created_by = request.user.email if request and request.user else None
        updated_by = created_by

        # Extract and remove fields
        role = validated_data.pop("role")
        password = validated_data.pop("password")
        profile_image = validated_data.pop("profile_image", None)
        reporting_to_id = validated_data.pop("reporting_to", None)

        # Bank fields
        bank_fields = {
            "account_holder_name": validated_data.pop("account_holder_name", None),
            "bank_name": validated_data.pop("bank_name", None),
            "account_number": validated_data.pop("account_number", None),
            "ifsc_code": validated_data.pop("ifsc_code", None),
        }

        # Aadhaar fields
        aadhaar_number = validated_data.pop("aadhaar_number")
        aadhaar_card_url = validated_data.pop("aadhaar_card_url")

        folder_map = {
            "manager": "employees/manager",
            "team_head": "employees/team_head",
            "executive": "employees/executive",
        }

        with transaction.atomic():
            # 1️⃣ Create Auth User
            admin_user = AdminUser.objects.create_user(
                email=validated_data["email"],
                password=password,
                mobile_no=validated_data["mobile_no"],
                full_name=validated_data["full_name"],
                role=role,
                is_active=True
            )
            # Upload to S3
            aadhaar_url = upload_to_s3(
                aadhaar_card_url,
                folder="employees/aadhaar"
            )
            # 2️⃣ Create Aadhaar (required)
            AadhaarDetails.objects.create(
                user=admin_user,
                aadhaar_number=aadhaar_number,
                aadhaar_card_url=aadhaar_url,
                created_by=created_by,
                updated_by=updated_by,
            )

            # 3️⃣ Create BankAccount only if any field is provided
            if any(bank_fields.values()):
                BankAccount.objects.create(
                    user=admin_user,
                    created_by=created_by,
                    updated_by=updated_by,
                    status=StatusMaster.objects.get(status_type="Active"),
                    **bank_fields
                )

            # 4️⃣ Upload profile image if provided
            image_url = None
            if profile_image:
                folder = folder_map.get(role)
                image_url = upload_to_s3(profile_image, folder)

            # 5️⃣ Create Role-based employee
            employee_data = {
                "auth_user": admin_user,
                "full_name": validated_data["full_name"],
                "email_address": validated_data["email_address"],
                "email_id": validated_data["email"],
                "mobile_no": validated_data["mobile_no"],
                "password": make_password(password),
                "profile_image_url": image_url,
                "joining_date": validated_data.get("joining_date"),
                "employment_type": validated_data.get("employment_type"),
                "work_mode": validated_data.get("work_mode"),
                "branch": validated_data.get("branch"),
                "city": validated_data.get("city"),
                "state": validated_data.get("state"),
                "created_by": created_by,
                "updated_by": updated_by,
            }

            if role == "manager":
                employee_data["reporting_to"] = AdminUser.objects.get(id=reporting_to_id) if reporting_to_id else None
                employee = Manager_register.objects.create(**employee_data)
            elif role == "team_head":
                employee_data["reporting_to"] = Manager_register.objects.get(id=reporting_to_id)
                employee = TeamHead_register.objects.create(**employee_data)
            elif role == "executive":
                employee_data["reporting_to"] = TeamHead_register.objects.get(id=reporting_to_id)
                employee = Executive_register.objects.create(**employee_data)
            else:
                raise serializers.ValidationError("Invalid employee type")

        return employee
    
class EmployeeReadSerializer(serializers.Serializer):
    role = serializers.CharField(
        source="auth_user.role",
        read_only=True
    )

    id = serializers.IntegerField()
    emp_id = serializers.CharField()
    full_name = serializers.CharField()
    email_address = serializers.EmailField()
    email_id = serializers.EmailField()
    mobile_no = serializers.CharField()
    profile_image = serializers.URLField(
        source="profile_image_url",
        allow_null=True
    )
    joining_date = serializers.DateField()
    employment_type = serializers.CharField()
    work_mode = serializers.CharField()
    branch = serializers.CharField()
    city = serializers.StringRelatedField()
    state = serializers.StringRelatedField()
    status = serializers.StringRelatedField()
    reporting_to = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()
    bank_details = serializers.SerializerMethodField()
    aadhaar_details = serializers.SerializerMethodField()

    def get_reporting_to(self, obj):
        return str(obj.reporting_to) if obj.reporting_to else None  
    
    def get_bank_details(self, obj):
        bank = (
            obj.auth_user.bank_accounts
            .filter(status__status_type__iexact="Active")
            .first()
        )
        if not bank:
            return None
        return BankDetailsReadSerializer(bank).data
        
    def get_aadhaar_details(self, obj):
        try:
            aadhaar = obj.auth_user.aadhaar_details
        except AadhaarDetails.DoesNotExist:
            return None
        return AadhaarDetailsReadSerializer(aadhaar).data


class BaseEmployeeUpdateSerializer(serializers.ModelSerializer):
    bank_details = BankDetailsUpdateSerializer(required=False)
    aadhaar_details = AadhaarDetailsUpdateSerializer(required=False)

    class Meta:
        model = None  # will be set dynamically
        fields = [
            "full_name", "email_address", "mobile_no", "employment_type",
            "work_mode", "branch", "city", "reporting_to",
            "bank_details", "aadhaar_details"
        ]
        read_only_fields = ["status"]

    def update(self, instance, validated_data):
        # Update Employee
        for attr in ["full_name", "email_address", "mobile_no"]:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        # Update BankAccount
        bank_attrs = ["bank_account_holder_name", "bank_bank_name", "bank_account_number", "bank_ifsc_code"]
        if any(attr in validated_data for attr in bank_attrs):
            bank_obj = instance.auth_user.bank_accounts.first()
            if not bank_obj:
                bank_obj = BankAccount.objects.create(user=instance.auth_user)
            for attr in bank_attrs:
                field_name = attr.replace("bank_", "")
                if attr in validated_data:
                    setattr(bank_obj, field_name, validated_data[attr])
            bank_obj.save()

        # Update Aadhaar
        aadhaar_attrs = ["aadhaar_number", "aadhaar_card_url"]
        if any(attr in validated_data for attr in aadhaar_attrs):
            try:
                aadhaar_obj = instance.auth_user.aadhaar_details
            except AadhaarDetails.DoesNotExist:
                aadhaar_obj = AadhaarDetails.objects.create(user=instance.auth_user)
            for attr in aadhaar_attrs:
                field_name = attr.replace("aadhaar_", "")
                if attr in validated_data:
                    setattr(aadhaar_obj, field_name, validated_data[attr])
            aadhaar_obj.save()

        return instance

def get_employee_update_serializer(model_cls):
    class EmployeeUpdateSerializer(BaseEmployeeUpdateSerializer):
        class Meta(BaseEmployeeUpdateSerializer.Meta):
            model = model_cls
    return EmployeeUpdateSerializer