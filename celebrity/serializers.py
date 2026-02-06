from rest_framework import serializers
from .models import CelebrityMedia, CelebrityDocument, EmailVerification, PhoneVerification, CelebrityRegistration
from admin_master.models import (
    AdminUser,
    PreferredEventType,
    Language,
    State_master, City_master

)
from .models import CelebrityRegistration, RefreshTokenStore
from django.contrib.auth.hashers import make_password
from rest_framework.exceptions import ValidationError
class CelebrityMediaSerializer(serializers.ModelSerializer):

    phone = serializers.CharField(
        source="verification.phone",
        read_only=True
    )

    class Meta:
        model = CelebrityMedia
        fields = [
            'id',
            'phone',
            'media_type',
            'media_url',
            'status',
            'uploaded_at'
        ]



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

class CelebrityDocumentSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="verification.phone", read_only=True)
    company_type = serializers.CharField(source="company_type.company_type", read_only=True)
    class Meta:
        model = CelebrityDocument
        fields = ['id', 'phone', 'company_type', 'document_type', 'document_url', 'status']



class CelebritySignupSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)


    class Meta:
        model = CelebrityRegistration
        fields = [
            "email",
            "contact_no",
            "whatsapp_no",
            "mpin",

            "display_name",
            "gender",
            "profession",

            "is_pan_india",
            "is_out_of_india",

            "state",
            "city",

            "description",
            "story",

            "facebook_url",
            "instagram_url",
            "twitter_url",
            "youtube_url",

            "tentative_budget",
            "preferred_event_type",

            "bank_account_name",
            "bank_account_number",
            "ifsc_code",
            "bank_name",

            "terms_conditions"
        ]

    def create(self, validated_data):
        mpin = validated_data.pop("mpin")
        user = CelebrityRegistration(**validated_data)
        user.set_mpin(mpin)  
        user.save()
        return user
    
class CelebrityLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    mobile_no = serializers.CharField(required=False)
    mpin = serializers.CharField()

    def validate(self, data):
        email = data.get("email")
        mobile = data.get("mobile_no")
        mpin = data.get("mpin")

        if not email and not mobile:
            raise ValidationError(detail={
                "status": False,
                "message": "Email or mobile number is required."
            })

        try:
            if email:
                user = CelebrityRegistration.objects.get(email=email)
            else:
                user = CelebrityRegistration.objects.get(contact_no=mobile)
        except CelebrityRegistration.DoesNotExist:
            raise ValidationError(detail={
                "status": False,
                "message": "User not found."
            })

        if not user.check_mpin(mpin):
            raise ValidationError(detail={
                "status": False,
                "message": "Invalid MPIN."
            })

        data["user"] = user
        return data

class CelebrityLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate_refresh(self, value):
        if not RefreshTokenStore.objects.filter(refresh_token=value).exists():
            raise serializers.ValidationError("Refresh token not found or already logged out.")
        return value
       