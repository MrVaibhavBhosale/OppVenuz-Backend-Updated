from rest_framework import serializers
from rest_framework.serializers import ValidationError
from django.contrib.auth import authenticate, get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from .models import (
Role_master, 
Service_master, 
Best_suited_for, 
State_master, 
Payment_type,
document_type,
City_master,
Article_type,
Delivery_option,
Best_deal,
App_version,
CakeMaster,
CompanyTypeMaster,
VenueTypeMaster,
StatusMaster,
OppvenuzChoiceMaster,
GstMaster,
OnboardingScreens,
Terms_and_condition_master,
Social_media_master,
Oppvenuz_ques_ans_master,
CompanyDocumentMapping,
AdminUser,
BlacklistedAdminAccessToken,
AdminRefreshTokenStore,
EmploymentType,
WorkMode,
TentativeBudget,
CelebrityProfession,
Language,
CommissionMaster,
PreferredEventType,
MessageTemplate,
TaskType,
VendorResponse,
TaskStatus,
ReasonForTask,
LeadSource,
)
from vendor.models import Vendor_registration
import os
import boto3

 # Role serializers
class RoleMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_role_name(self, value):
        if Role_master.objects.filter(role_name=value, status__in=[1,2]).exists():
            raise ValidationError("Role name already exists.")
        return value

 # Best suited for serializers
class BestSuitedForSerializer(serializers.ModelSerializer):
    class Meta:
        model = Best_suited_for
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Best_suited_for.objects.filter(name=value, status__in=[1,2]).exists():
            raise ValidationError("Name already exists.")
        return value

 # State serializers
class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if State_master.objects.filter(state_name=value).exists():
            raise ValidationError("State already exists.")
        return value

 # City serializers
class CitySerializer(serializers.ModelSerializer):
    state = serializers.PrimaryKeyRelatedField(
        queryset=State_master.objects.all(),
        required=True,
        help_text="ID of the State this city belongs to."
    )

    state_name = serializers.CharField(source='state.state_name', read_only=True)
    class Meta:
        model = City_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_city_name(self, value):
        city_id = self.instance.id if self.instance else None
        if City_master.objects.filter(city_name__iexact=value).exclude(id=city_id).exists():
            raise ValidationError("City with this name already exists.")
        return value
    
 # Payment Type serializers
class PaymentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment_type
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Payment_type.objects.filter(payment_type=value).exists():
            raise ValidationError("Payment Type already exists.")
        return value
    

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def validate_service_name(self, value):
        value = value.strip()
        qs = Service_master.objects.filter(service_name__iexact=value, status__in=[1, 2])

        # Exclude current instance if updating
        instance = getattr(self, 'instance', None)
        if instance:
            qs = qs.exclude(id=instance.id)

        if qs.exists():
            raise ValidationError("Service name already exists among active/inactive services")
        return value

    def validate(self, data):
        registration_charges = data.get("registration_charges")
        if registration_charges is not None and registration_charges < 0:
            raise ValidationError({"registration_charges": "Registration charges cannot be negative"})
        return data

class SocialMediaSerializer(serializers.ModelSerializer):
    media_image = serializers.CharField(required=False)
    class Meta:
        model = Social_media_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def validate_media_name(self, value):
        value = value.strip().strip('"').strip("'")
        qs = Social_media_master.objects.filter(media_name__iexact=value, status__in=[1])

        instance = getattr(self, 'instance', None)
        if instance:
            qs = qs.exclude(id=instance.id)

        if qs.exists():
            raise ValidationError("Media name already exists")
        return value

    def validate_media_image(self, value):
        if not value.lower().endswith(('.png', '.jpg', '.jpeg', '.svg', '.webp')):
            raise ValidationError("Only image URLs ending with .png, .jpg, .jpeg, .svg, or .webp are allowed.")
        return value
    
class TermsConditionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Terms_and_condition_master
        fields = [
            'id', 'title', 'content', 'slug',
            'status', 'status_display',
            'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by')

    def validate(self, data):
        title = data.get('title')
        status = data.get('status')

        if status == 1:
            existing = Terms_and_condition_master.objects.filter(title__iexact=title, status__in=[1, 2])
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            if existing.exists():
                raise serializers.ValidationError(
                    {"title": "Terms & Conditions with the same title already exists."}
                )

        return data

class document_typeSerializer(serializers.ModelSerializer):
    class Meta:
        model = document_type
        fields = ['id', 'document_type', 'status', 'created_by', 'updated_by', 'updated_at']
        read_only_fields = ['created_by', 'updated_by', 'updated_at']

 # Article Type serializers
class ArticleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article_type
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Article_type.objects.filter(article_type=value).exists():
            raise ValidationError("Article Type already exists.")
        return value

 # Delivery Option serializers
class DeliveryOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Delivery_option
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Delivery_option.objects.filter(delivery_option=value).exists():
            raise ValidationError("Delivery Option already exists.")
        return value

 # Best Deal serializers
class BestDealSerializer(serializers.ModelSerializer):
    class Meta:
        model = Best_deal
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Best_deal.objects.filter(deal_name=value).exists():
            raise ValidationError("Deal Name already exists.")
        return value

 # Best Deal serializers
class AppVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = App_version
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if App_version.objects.filter(app_version=value).exists():
            raise ValidationError("Version already exists.")
        return value
    
class StatusMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusMaster
        fields = ['id', 'status_type']


# ------------------ Cake Master ------------------
class CakeMasterSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = CakeMaster
        fields = ['id', 'shape_name', 'cake_type', 'flavor', 'status', 'created_at', 'updated_at']

    def get_status(self, obj):
        return obj.status.status_type if obj.status else None


# ------------------ Company Type Master ------------------
class CompanyTypeMasterSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = CompanyTypeMaster
        fields = ['id', 'company_type', 'status', 'created_at', 'updated_at']

    def get_status(self, obj):
        return obj.status.status_type if obj.status else None


# ------------------ Venue Type Master ------------------
class VenueTypeMasterSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = VenueTypeMaster
        fields = ['id', 'venue_type', 'status', 'created_at', 'updated_at']

    def get_status(self, obj):
        return obj.status.status_type if obj.status else None


# ------------------ Oppvenuz Choice Master ------------------
class OppvenuzChoiceMasterSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    average_percentage = serializers.SerializerMethodField()

    class Meta:
        model = OppvenuzChoiceMaster
        fields = ['id', 'choice_name', 'minimum_comments_count', 'archived_comments_count', 'average_percentage', 'status', 'created_at', 'updated_at']

    def get_status(self, obj):
        if hasattr(obj, 'status') and obj.status:
            return obj.status.status_type
        return "Active" if obj.status else "Inactive"

    def get_average_percentage(self, obj):
        return f"{obj.average_percentage:.0f}%"


# ------------------ GST Master ------------------
class GstMasterSerializer(serializers.ModelSerializer):
    gst_percentage = serializers.SerializerMethodField()
    gst_percentage_input = serializers.IntegerField(write_only=True)
    status = serializers.CharField(source='status.status_type', read_only=True)

    class Meta:
        model = GstMaster
        fields = ['id', 'gst_percentage', 'gst_percentage_input', 'status']

    def get_gst_percentage(self, obj):
        return f"{obj.gst_percentage}%"

    def validate_gst_percentage_input(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("GST percentage must be between 0 and 100.")
        return value

    def create(self, validated_data):
        value = validated_data.pop('gst_percentage_input')
        return GstMaster.objects.create(gst_percentage=value)

    def update(self, instance, validated_data):
        value = validated_data.pop('gst_percentage_input', None)
        if value is not None:
            instance.gst_percentage = value
            instance.save()
        return instance
    
 # Oppvenuz question answer for serializers
class  QuestionAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Oppvenuz_ques_ans_master
        fields = '__all__'
        read_only_fields = ('created_at', 'created_by', 'updated_at', 'updated_by','status')

    def validate_name(self, value):
        if Oppvenuz_ques_ans_master.objects.filter(name=value, status__in=[1,2]).exists():
            raise ValidationError("Name already exists.")
        return value

class OnboardingScreenSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingScreens
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at", "status")

class CompanyDocumentMappingSerializer(serializers.ModelSerializer):
    company_type_name = serializers.CharField(source='company_type.company_type', read_only=True)
    document_type_name = serializers.CharField(source='document_type.document_type', read_only=True)

    class Meta:
        model = CompanyDocumentMapping
        fields = ['id', 'company_type', 'company_type_name', 'document_type', 'document_type_name', 'status', 'created_by', 'updated_by', 'updated_at']

AdminUser = get_user_model()


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        email = data["email"]
        password = data["password"]

        try:
            user = AdminUser.objects.get(email=email)
        except AdminUser.DoesNotExist:
            raise serializers.ValidationError("Admin not found")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid password")
        if not user.is_active:
            raise serializers.ValidationError("User account disabled")

        data["user"] = user
        return data


class AddAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = AdminUser
        fields = (
            "id",
            "admin_uid",
            "email",
            "mobile_no",
            "full_name",
            "role",
            "profile_image",
            "password",
        )
        read_only_fields = ("admin_uid",)

    def validate_role(self, value):
        value = value.lower()
        if value not in ("admin", "super_admin"):
            raise serializers.ValidationError("Invalid role")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        image = validated_data.pop("profile_image", None)

        user = AdminUser.objects.create_user(
            password=password,
            **validated_data
        )

        # Upload image AFTER admin_uid is created
        if image:
            image_url = self.upload_to_s3(image, user.admin_uid)
            user.profile_image = image_url
            user.save(update_fields=["profile_image"])

        return user

    def upload_to_s3(self, file_obj, admin_uid):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("s3AccessKey"),
            aws_secret_access_key=os.getenv("s3Secret"),
            region_name=os.getenv("AWS_REGION"),
        )

        bucket = os.getenv("S3_BUCKET_NAME")

        ext = os.path.splitext(file_obj.name)[1]
        file_key = f"admin_profiles/{admin_uid}{ext}"

        s3.upload_fileobj(
            file_obj,
            bucket,
            file_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file_obj.content_type,
            },
        )

        return f"https://{bucket}.s3.amazonaws.com/{file_key}"

class UpdateAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        min_length=6
    )
    profile_image = serializers.ImageField(required=False)

    class Meta:
        model = AdminUser
        fields = (
            "email",
            "mobile_no",
            "full_name",
            "role",
            "profile_image",
            "password",
            "is_active",
        )

    #  Role validation
    def validate_role(self, value):
        if value not in ("admin", "super_admin"):
            raise serializers.ValidationError("Invalid role")
        return value

    # Unique email validation (exclude current admin)
    def validate_email(self, value):
        user = self.instance
        if AdminUser.objects.exclude(id=user.id).filter(email=value, status=1).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    # Unique mobile validation (exclude current admin)
    def validate_mobile_no(self, value):
        user = self.instance
        if AdminUser.objects.exclude(id=user.id).filter(mobile_no=value, status=1).exists():
            raise serializers.ValidationError("Mobile number already exists.")
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        image = validated_data.pop("profile_image", None)

        # Update normal fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Update password
        if password:
            instance.set_password(password)

        # Upload profile image to S3 (overwrite old image)
        if image:
            image_url = self.upload_to_s3(image, instance.admin_uid)
            instance.profile_image = image_url

        # Auto-assign flags based on role
        if instance.role == "super_admin":
            instance.is_staff = True
            instance.is_superuser = True
        else:
            instance.is_staff = False
            instance.is_superuser = False

        instance.save()
        return instance

    def upload_to_s3(self, file_obj, admin_uid):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("s3AccessKey"),
            aws_secret_access_key=os.getenv("s3Secret"),
            region_name=os.getenv("AWS_REGION"),
        )

        bucket = os.getenv("S3_BUCKET_NAME")

        ext = os.path.splitext(file_obj.name)[1]
        file_key = f"admin_profiles/{admin_uid}{ext}"

        s3.upload_fileobj(
            file_obj,
            bucket,
            file_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file_obj.content_type,
            },
        )

        return f"https://{bucket}.s3.amazonaws.com/{file_key}"

class AdminLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate_refresh(self, value):
        if not AdminRefreshTokenStore.objects.filter(refresh_token=value).exists():
            raise serializers.ValidationError("Refresh token not found or already logged out.")
        return value
       
class EmploymentTypeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='status.name', read_only=True)

    class Meta:
        model = EmploymentType
        fields = [
            'id',
            'employment_type',
            'code',
            'working_hours',
            'status',
            'status_display',
            'created_at'
        ]
        read_only_fields = ('created_at',)

class WorkModeSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='status.name',
        read_only=True
    )

    class Meta:
        model = WorkMode
        fields = [
            'id',
            'work_mode_name',
            'code',
            'location_type',
            'working_rule',
            'status',
            'status_display',
            'created_at'
        ]
        read_only_fields = ('created_at',)

class TentativeBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = TentativeBudget
        fields = [
            "id",
            "label",
            "min_amount",
            "max_amount"
        ]

class CelebrityProfessionSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    updated_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CelebrityProfession
        fields = [
            "id",
            "name",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        qs = CelebrityProfession.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                "Profession already exists."
            )
        return value    
class LanguageSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source='status.name',
        read_only=True
    )

    class Meta:
        model = Language
        fields = [
            'id',
            'language_name',
            'code',
            'status',
            'status_display',
            'created_at'
        ]
        read_only_fields = ('created_at',)
class CommissionMasterSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(
        source="service.service_name", read_only=True
    )

    class Meta:
        model = CommissionMaster
        fields = "__all__"


class ForgotPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    def validate_email(self, value):
        # Check login record exists & active
        if not AdminUser.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError(
                "No active account found with this email address."
            )
        return value

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=5, max_length=16)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Password do not match")
        return data
    
class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    old_password = serializers.CharField()

class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

class TaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskType
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

class VendorResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorResponse
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

class ReasonForTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReasonForTask
        fields = "__all__"
        read_only_fields = (
            "id",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )

class LeadSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeadSource
        fields = "__all__"
        read_only_fields = ("created_by", "updated_by", "created_at", "updated_at")

class VendorListSerializer(serializers.ModelSerializer):
    city = serializers.CharField(source="city_id.city_name", read_only=True)
    service = serializers.CharField(source="service_id.service_name", read_only=True)
    state = serializers.CharField(source="state_id.state_name", read_only=True)
    status= serializers.CharField(source="status.status_type", read_only=True)
    best_suited = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")

    class Meta:
        model = Vendor_registration
        fields = ["id", "vendor_id", "first_name", "middle_name", "last_name", 
                  "business_name", "date_of_birth", "address", "city",
                   "state", "service", "best_suited", "gender", "status",
                  "email", "contact_no", "whatsapp_no", "profile_status", "payment_status"]

class VendorStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor_registration
        fields = ['profile_status',"updated_by"]