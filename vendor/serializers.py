from rest_framework import serializers
from .models import (
    Vendor, 
    Vendor_registration, 
    VendorDocument,
    PhoneVerification,
    EmailVerification,
    VenderBusinessDescription,
    VendorDevice,
    ReadyToSellItem,
    ProductAddition,
    VendorSocialMedia,
    VendorMedia,
    VendorProduct,
    VendorBankAccount,
    VendorFeedbackReply,
    VendorFeedback,
    AdminUser,
    CakeOptions,
    CelebrityBanner,
    BestDealBanner,
    DeliveryOptions,
    
    )
from django.contrib.auth import authenticate
import re
from django.db import models
import os
from django.db.models import Q
from admin_master.models import (
    CompanyTypeMaster,
    Best_suited_for,
    State_master,
    City_master,
)
from user.models import(
    Order,
    OrderItem,
    OrderStatus
)
from user.serializers import(
    AddressSerializer
)
class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"

class VendorBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "business_name", "email", "contact_number", "working_since", "years_of_experience"]

class VendorDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = ["id", "description"]


class LocationSerializer(serializers.Serializer):
    pincode = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    latitude = serializers.DecimalField(max_digits=13, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=13, decimal_places=6, required=True)


class VendorDocumentSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="verification.phone", read_only=True)
    company_type = serializers.CharField(source="company_type.company_type", read_only=True)
    class Meta:
        model = VendorDocument
        fields = ['id', 'phone', 'company_type', 'document_type', 'document_url', 'status']

class VendorSignupSerializer(serializers.ModelSerializer):
    location = LocationSerializer(write_only=True)
    mpin = serializers.CharField(write_only=True, required=True)
    date_of_birth = serializers.DateField(input_formats=['%Y-%m-%d', '%d-%m-%Y'])
    documents = VendorDocumentSerializer(many=True, required=False)
    best_suited = serializers.PrimaryKeyRelatedField(
        queryset=Best_suited_for.objects.all(),
        required=False,
        many=True
    )

    class Meta:
        model = Vendor_registration
        fields = [
            'first_name', 'middle_name', 'last_name', 'email', 'contact_no', 'whatsapp_no',
            'gender', 'date_of_birth', 'mpin',
            'business_name', 'service_id', 'best_suited', 'city_id', 'state_id',
            'location', 'working_since', 'year_of_experience',
            'documents', 'payment_status','profile_status'
        ]
        extra_kwargs = {
            # 'terms_conditions': {'required': True},
            # 'privacy_policy': {'required': True},
            # 'payment_cancellation': {'required': True},
        }

    # ---------------- VALIDATIONS ----------------
    def validate_email(self, value):
        if value and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', value):
            raise serializers.ValidationError("Invalid email format.")
        return value

    def validate_contact_no(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Contact number must contain digits only.")
        if not 10 <= len(value) <= 12:
            raise serializers.ValidationError("Contact number must be between 10 and 12 digits.")
        return value

    def validate_whatsapp_no(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("WhatsApp number must contain digits only.")
        if value and not 10 <= len(value) <= 12:
            raise serializers.ValidationError("WhatsApp number must be between 10 and 12 digits.")
        return value

    def validate_mpin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("MPIN must contain only digits.")
        if len(value) != 6:
            raise serializers.ValidationError("MPIN must be 6 digits long.")
        return value

    def validate_year_of_experience(self, value):
        if value < 0:
            raise serializers.ValidationError("Year of experience cannot be negative.")
        return value

    def validate(self, attrs):
        email = attrs.get('email')
        contact_no = attrs.get('contact_no')
        service_id = attrs.get('service_id')

        if Vendor_registration.objects.filter(
            models.Q(email=email) | models.Q(contact_no=contact_no),
            service_id=service_id
        ).exists():
            raise serializers.ValidationError(
                "Vendor with this email or contact number is already registered for this service."
            )
        return attrs

    # ---------------- CREATE ----------------
    def create(self, validated_data):
        best_suited = validated_data.pop("best_suited", [])
        # Handle location (pincode, address, lat/lon)
        location = validated_data.pop('location', None)
        if location:
            validated_data['pincode'] = location.get('pincode')
            validated_data['address'] = location.get('address')
            validated_data['latitude'] = location.get('latitude')
            validated_data['longitude'] = location.get('longitude')

        # Handle documents (if provided)
        document_ids = validated_data.pop("documents", [])

        # Handle MPIN securely
        mpin = validated_data.pop('mpin')

        auth_user = AdminUser.objects.create_user(
            email=validated_data.get("email"),
            password=mpin,  # vendor uses MPIN as password
            role="vendor",
            full_name=f"{validated_data.get('first_name')} {validated_data.get('last_name')}",
            is_active=True,
            mobile_no=validated_data.get("contact_no"),
        )

        #  CREATE VENDOR ENTRY 
        vendor = Vendor_registration.objects.create(
            auth_user=auth_user, **validated_data  
        )

        if best_suited:
            vendor.best_suited.set(best_suited)

        # Create vendor instance
        # vendor = Vendor_registration(is_active=True, **validated_data)
        vendor.set_mpin(mpin)
        vendor.save()

        # ✅ Default image set (if not given)
        if not vendor.profile_image:
            vendor.profile_image = os.getenv('DEFAULT_VENDOR_IMAGE_PATH')
        vendor.save()

        uploaded_docs = VendorDocument.objects.filter(
            vendor_business_no=str(vendor.contact_no),
            status="TEMP"
        )

        if uploaded_docs.exists():
            document_ids = list(uploaded_docs.values_list("id", flat=True))
            vendor.document_id = document_ids
            vendor.save(update_fields=["document_id"])        

        vendor.refresh_from_db()
        return vendor

    # ---------------- RESPONSE ----------------
    def to_representation(self, instance):
        best_suited_name = None

        if instance.best_suited:
            best_suited_names = instance.best_suited.values_list("name", flat=True)

        return {
            "vendor_id": instance.vendor_id,
            "business_name": instance.business_name,
            "first_name": instance.first_name,
            "middle_name": instance.middle_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "contact_no": instance.contact_no,
            "whatsapp_no": instance.whatsapp_no,
            "gender": instance.gender,
            "date_of_birth": instance.date_of_birth,
            "city": getattr(instance.city_id, 'city_name', None),
            "state": getattr(instance.state_id, 'state_name', None),
            "pincode": instance.pincode,
            "address": instance.address,
            "service_name": getattr(instance.service_id, 'service_name', None),
            "best_suited_for": list(best_suited_names),
            "working_since": instance.working_since,
            "year_of_experience": instance.year_of_experience,
            "referral_code": instance.referral_code,
            "document_id": instance.document_id,
            "payment_status": instance.payment_status,
            "profile_status": instance.profile_status,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "documents": VendorDocumentSerializer(
                VendorDocument.objects.filter(
                    vendor_business_no=instance.contact_no, status="PERMANENT"
                ),
                many=True
            ).data,
        }

    

class VendorLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    mpin = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        username = attrs.get('username')
        mpin = attrs.get('mpin')

        try:
            user = Vendor_registration.objects.get(
                Q(contact_no=username) | Q(email=username)
            )
        except Vendor_registration.DoesNotExist:
            raise serializers.ValidationError(
                "No account found with this contact number or email."
            )
        
        if not user.check_mpin(mpin):
            raise serializers.ValidationError(
                "Invalid MPIN"
            )

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        
        vendor = Vendor_registration.objects.filter(
            Q(vendor_id=username) |
            Q(contact_no=username) |
            Q(whatsapp_no=username) |
            Q(email=username)
        ).first()

        if not vendor:
            raise serializers.ValidationError("Vendor not found")

        # Check MPIN from vendor table
        if not vendor.check_mpin(mpin):
            raise serializers.ValidationError("Invalid MPIN")

        admin_user = vendor.auth_user

        if not admin_user or not admin_user.is_active:
            raise serializers.ValidationError("Admin user inactive or missing")

        attrs["admin_user"] = admin_user
        attrs["vendor"] = vendor

        return attrs
    

class VendorDataSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)
    documents = VendorDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Vendor_registration
        fields = '__all__'

    def to_representation(self, instance):
        return {
            "vendor_id": instance.vendor_id,
            "business_name": instance.business_name,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "email": instance.email,
            "contact_no": instance.contact_no,
            "gender": instance.gender,
            "date_of_birth": instance.date_of_birth,
            "city": getattr(instance.city_id, 'city_name', None),
            "state": getattr(instance.state_id, 'state_name', None),
            "pincode": instance.pincode,
            "address": instance.address,
            "service_name": getattr(instance.service_id, 'service_name', None),
            "best_suited_for": getattr(instance.best_suited, 'subcat_name', None),
            "working_since": instance.working_since,
            "year_of_experience": instance.year_of_experience,
            "referral_code": instance.referral_code,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "payment_status": instance.payment_status,
            "profile_status": instance.profile_status,
            "profile_image": instance.profile_image,
            "documents": VendorDocumentSerializer(
                VendorDocument.objects.filter(
                    vendor_business_no=instance.contact_no, status="PERMANENT"
                ),
                many=True
            ).data,
        }


class RequestEmailOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ['email']
        extra_kwargs = {
            'email': {'validators': []}
        }

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("Email is required.")
        return value
    
class RequestPhoneOTPSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhoneVerification
        fields = ['phone']
        extra_kwargs = {
            'phone': {'validators': []}
        }

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits long.")
        return value

    
class VerifyEmailOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=10)

class VerifyPhoneOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(max_length=10)
   
class ForgotMPINRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    def validate(self, data):
        email = data.get('email')
        phone = data.get('phone')

        if not email and not phone:
            raise serializers.ValidationError("Email or phone is required.")

        if email:
            verification = EmailVerification.objects.filter(email=email, is_verified=True).first()
            if not verification:
                raise serializers.ValidationError("Email not verified or not found.")

        elif phone:
            verification = PhoneVerification.objects.filter(phone=phone, is_verified=True).first()
            if not verification:
                raise serializers.ValidationError("Phone number not verified or not found.")

        return data

class ChangeMPINSerializer(serializers.ModelSerializer):
    new_mpin = serializers.CharField(write_only=True, required=True)
    email = serializers.EmailField(required=False)
    contact_no = serializers.CharField(required=False)

    class Meta:
        model = Vendor_registration
        fields = ['email', 'contact_no', 'new_mpin']

    def validate_new_mpin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("MPIN must contain only digits.")
        if len(value) != 6:
            raise serializers.ValidationError("MPIN must be exactly 6 digits long.")
        return value

    def validate(self, attrs):
        email = attrs.get('email')
        contact_no = attrs.get('contact_no')

        if not email and not contact_no:
            raise serializers.ValidationError("Either email or contact_no required")
        
        if email and contact_no:
            raise serializers.ValidationError("Provide only one of email and contact_no, not both")
        
        try:
            if email:
                vendor = Vendor_registration.objects.get(email=email)
            else:
                vendor = Vendor_registration.objects.get(contact_no=contact_no)
        except Vendor_registration.DoesNotExist:
            raise serializers.ValidationError("No vendor found with this email or contact_no")
        
        attrs['vendor'] = vendor
        return attrs

    def save(self, **kwargs):
        vendor = self.validated_data["vendor"]
        new_mpin = self.validated_data["new_mpin"]
        vendor.set_mpin(new_mpin)
        vendor.save(update_fields=['mpin'])
        return vendor

class VenderBusinessDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VenderBusinessDescription
        fields = ['id', 'vendor_reg_id', 'description']
        read_only_fields = ['vendor_reg_id']

class ReadyToSellItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadyToSellItem
        fields = "__all__"

class ProductAdditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAddition
        fields = '__all__'

class VendorRegistrationSerializer(serializers.ModelSerializer):
    state_name = serializers.CharField(source='state_id.state_name', read_only=True)
    city_name = serializers.CharField(source='city_id.city_name', read_only=True)
    service_name = serializers.CharField(source='service_id.service_name', read_only=True)
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Vendor_registration
        fields = [
            'id', 'vendor_id', 'business_name',
            'first_name', 'middle_name', 'last_name',
            'email', 'contact_no', 'whatsapp_no',
            'gender', 'date_of_birth',
            'state_id', 'state_name', 'city_id', 'city_name',
            'pincode', 'address', 'latitude', 'longitude',
            'service_id', 'service_name', 'best_suited',
            'working_since', 'year_of_experience',
            'is_active', 'created_at', 'updated_at',
            'documents'
        ]

    def get_documents(self, obj):
        try:
            docs = VendorDocument.objects.filter(vendor_business_no=obj.contact_no)
            return [
                {
                    "id": doc.id,
                    "document_type": doc.document_type,
                    "document_url": doc.document_url,
                    "status": doc.status,
                    "company_type": doc.company_type.company_type if doc.company_type else None,
                    "uploaded_at": doc.uploaded_at,
                    "expires_at": doc.expires_at,
               }
               for doc in docs
           ]
        except Exception as e:
            return []

class VendorBasicDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor_registration
        fields = [
            'first_name', 'middle_name', 'last_name',
            'business_name', 'gender', 'date_of_birth',
            'service_id', 'best_suited', 'year_of_experience'
        ]

class VendorSocialMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorSocialMedia
        fields = '__all__'

class VendorMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorMedia
        fields = "__all__"
        read_only_fields = [
            "id",
            "vendor",
            "vendor_code",
            "status",
            "created_at",
            "updated_at"
        ]


class VendorServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProduct
        fields = '__all__'
        extra_kwargs = {
            'created_by': {'required': False},
            'updated_by': {'required': False},
            'vendor_id': {'required': False},  
        }

    def validate_data(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Data must be a JSON object")
        return value

    def create(self, validated_data):
        # Automatically set vendor_id from request.user
        request = self.context.get('request')
        if request and hasattr(request.user, 'vendor_registration'):
            validated_data['vendor_id'] = request.user.vendor_registration
        elif request and isinstance(request.user, Vendor_registration):
            validated_data['vendor_id'] = request.user
        else:
            raise serializers.ValidationError("Vendor not found for this user.")

        validated_data['created_by'] = request.user.email if request.user else None
        validated_data['updated_by'] = request.user.email if request.user else None

        return super().create(validated_data)
    

class MPINVerifySerializer(serializers.Serializer):
    phone = serializers.CharField(required=False)
    email = serializers.CharField(required=False)
    mpin = serializers.CharField()

    def validate(self, attrs):
        phone = attrs.get("phone")
        email = attrs.get("email")
        mpin = attrs.get("mpin")

        if not phone and not email:
            raise serializers.ValidationError("Phone or Email is required")
        
        try:
            if phone:
                user = Vendor_registration.objects.get(contact_no=phone)
            else:
                user = Vendor_registration.objects.get(email=email)
        except Vendor_registration.DoesNotExist:
            raise serializers.ValidationError("User not found")
        
        if not user.check_mpin(mpin):
            raise serializers.ValidationError({"mpin": "Invalid MPIN"})
        
        attrs["user"] = user
        return attrs
    
class VerifyVendorSerializer(serializers.Serializer):
    identifier = serializers.CharField(
        required=True,
        allow_blank=False,
        error_messages={
            "required": "Identifier (email or phone) is required",
            "blank": "Identifier cannot be empty"
        }
    )

    def validate_identifier(self, value):
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError("Invalid identifier")

        return value
    
class VendorBankAccountSerializer(serializers.ModelSerializer):
    confirm_account_number = serializers.CharField(write_only=True)

    class Meta:
        model = VendorBankAccount
        fields = [
            "id",
            "vendor",
            "full_name",
            "account_number",
            "confirm_account_number",
            "ifsc_code",
            "bank_name",
            "status",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, data):
        if data["account_number"] != data["confirm_account_number"]:
            raise serializers.ValidationError("Account numbers do not match.")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_account_number", None)
        return VendorBankAccount.objects.create(**validated_data)

    def update(self, instance, validated_data):
        validated_data.pop("confirm_account_number", None)
        return super().update(instance, validated_data)

class VendorFeedbackReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorFeedbackReply
        fields = ['id', 'feedback', 'reply_text', 'reply_by', 'replied_at']
        read_only_fields = ['feedback']


class VendorFeedbackSerializer(serializers.ModelSerializer):
    replies = VendorFeedbackReplySerializer(many=True, read_only=True)

    class Meta:
        model = VendorFeedback
        fields = [
            'id', 'vendor', 'customer_name', 'customer_email',
            'message', 'rating', 'is_visible', 'created_at', 'replies'
        ]

class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(default="P. priyanka Mehta", read_only=True)
    customer_phone = serializers.CharField(default="8970998765", read_only=True)
    order_status = serializers.CharField(source="get_order_status_display", read_only=True)
    delivery_address = AddressSerializer(read_only=True)
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    product_weight = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "order_number", "customer_name", "customer_phone", 
                  "delivery_address", "product_name", "product_image", 
                  "product_weight", "grand_total", "order_status", "order_date",]
        
    def get_product_name(self, obj):
        first_item = obj.items.first()
        return first_item.product_name if first_item else None
        
    def get_product_image(self, obj):
        first_image = obj.items.first()
        return first_image.product_image if first_image else None
    
    def get_product_weight(self, obj):
        weight = obj.items.first()
        return weight.product_weight if weight else None


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"

class OrderListByIdSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery_address = AddressSerializer(read_only=True)
    order_status = serializers.CharField(source='get_order_status_display', read_only=True)
    class Meta:
        model = Order
        fields = [
            "id", "order_number", "customer", "delivery_address",
             "order_status", "subtotal", "packaging_fee",
            "delivery_fee", "platform_fee", "discount", "grand_total",
            "payment_method", "created_by", "items"
        ]

class UpdateOrderStatusSerializer(serializers.ModelSerializer):
    order_status_name = serializers.CharField(
        source="get_order_status_display",
        read_only=True
    )

    reason = serializers.CharField(
        required=False, allow_blank=True, write_only=False  # make it readable
    )

    class Meta:
        model = Order
        fields = ["order_status", "order_status_name", "reason"]

    def validate(self, attrs):
        order_status = attrs.get("order_status")
        reason = attrs.get("reason", "")

        allowed_statuses = [1, 2, 3, 4]  # 4 = Cancelled

        # Validate order_status
        if order_status not in allowed_statuses:
            raise serializers.ValidationError({
                "order_status": "Invalid order status. Allowed: 1, 2, 3, 4 (Cancelled)."
            })

        # Require reason only for Cancelled
        if order_status == 4 and not reason:
            raise serializers.ValidationError({
                "reason": "Cancellation reason is required when order is Cancelled."
            })

        # Do not allow reason for non-cancelled statuses
        if order_status != 4 and reason:
            raise serializers.ValidationError({
                "reason": "Reason should only be provided when order is Cancelled."
            })

        return attrs

    def update(self, instance, validated_data):
        instance.order_status = validated_data.get("order_status", instance.order_status)

        if instance.order_status == 4:
            instance.reason = validated_data.get("reason")
        else:
            instance.reason = ""  # clear reason if not cancelled

        instance.save()
        return instance

    def to_representation(self, instance):
        """Show reason only if order is cancelled"""
        data = super().to_representation(instance)
        if instance.order_status != 4:
            data.pop("reason", None)
        return data

class CelebrityBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = CelebrityBanner
        fields = "__all__"

class VendorContactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor_registration
        fields = ['contact_no', 'whatsapp_no', 'email']
        extra_kwargs = {
            'contact_no': {'required': False},
            'whatsapp_no': {'required': False},
            'email': {'required': False},
        }

    def validate(self, attrs):
        instance = self.instance
        
        # Email unique validation
        if 'email' in attrs:
            email = attrs['email']
            if Vendor_registration.objects.exclude(pk=instance.pk).filter(email=email).exists():
                raise serializers.ValidationError({"email": "Email already exists."})

        # Contact unique validation
        if 'contact_no' in attrs:
            c_no = attrs['contact_no']
            if Vendor_registration.objects.exclude(pk=instance.pk).filter(contact_no=c_no).exists():
                raise serializers.ValidationError({"contact_no": "Contact number already exists."})

        # WhatsApp unique validation
        if 'whatsapp_no' in attrs:
            w_no = attrs['whatsapp_no']
            if Vendor_registration.objects.exclude(pk=instance.pk).filter(whatsapp_no=w_no).exists():
                raise serializers.ValidationError({"whatsapp_no": "WhatsApp number already exists."})

        return attrs
    
class BestDealBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BestDealBanner
        fields = "__all__"

class VendorLocationUpdateSerializer(serializers.Serializer):
    state_id = serializers.IntegerField(required=True)
    city_id = serializers.IntegerField(required=True)
    pincode = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    address = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    latitude = serializers.DecimalField(max_digits=13, decimal_places=6, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=13, decimal_places=6, required=False, allow_null=True)

    def validate(self, attrs):
        state_id = attrs.get('state_id')
        city_id = attrs.get('city_id')

        try:
            state = State_master.objects.get(pk=state_id, status=1)
        except State_master.DoesNotExist:
            raise serializers.ValidationError({"state_id": "Invalid state_id or state not active."})

        try:
            city = City_master.objects.get(pk=city_id, status=1)
        except City_master.DoesNotExist:
            raise serializers.ValidationError({"city_id": "Invalid city_id or city not active."})

        # Check city belongs to state
        if getattr(city, 'state_id_id', None) and city.state_id_id != state_id:
            # depending on your City_master field name, adjust above; commonly City_master has state_id FK
            raise serializers.ValidationError({"city_id": "Selected city does not belong to selected state."})

        attrs['state_obj'] = state
        attrs['city_obj'] = city
        return attrs
    
class VendorDocumentUpdateSerializer(serializers.Serializer):
    document_type = serializers.CharField(required=False)
    file = serializers.FileField(required=False)
    company_type = serializers.IntegerField(required=False)

class CakeOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CakeOptions
        fields = ['flavors', 'shapes', 'types', 'combo_items']


class DeliveryOptionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryOptions
        fields = ['same_day_available', 'fixed_time_slots', 'pre_midnight_slots']

