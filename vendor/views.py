from django.http import JsonResponse
from rest_framework import generics, permissions, status
from django.db import transaction
from django.db.models import Q
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from admin_master.models import CompanyTypeMaster, StatusMaster
from admin_master.utils import get_status
from decouple import config
from oauth2_provider.contrib.rest_framework.authentication import OAuth2Authentication
from vendor.authentication import VendorJWTAuthentication
from datetime import timedelta
import traceback
from concurrent.futures import ThreadPoolExecutor
from .permissions import IsVendor
import json
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from .filters import OrderFilter
from user.models import Order
from .models import (
    Vendor, 
    VendorDevice, 
    Vendor_registration, 
    PhoneVerification,
    EmailVerification,
    VendorDocument,
    VenderBusinessDescription,
    ReadyToSellItem,
    VendorSocialMedia,
    VendorMedia,
    VendorProduct,
    ProductAddition,
    BlacklistedToken,
    RefreshTokenStore,
    VendorBankAccount,
    VendorFeedbackReply,
    VendorFeedback,
    AdminUser,
    CelebrityBanner,
    BestDealBanner,
    CakeOptions,
    DeliveryOptions,

)

from .serializers import (
    VendorSerializer,
    VendorBasicSerializer,
    VenderBusinessDescriptionSerializer,
    VendorSignupSerializer,
    VendorLoginSerializer,
    VendorDataSerializer,
    VerifyEmailOTPSerializer,
    VerifyPhoneOTPSerializer,
    RequestEmailOTPSerializer,
    RequestPhoneOTPSerializer,
    VendorDocumentSerializer,
    ForgotMPINRequestSerializer,
    ChangeMPINSerializer,
    ReadyToSellItemSerializer,
    VendorRegistrationSerializer,
    VendorBasicDetailsSerializer,
    VendorSocialMediaSerializer,
    VendorMediaSerializer,
    VendorServiceSerializer,
    ProductAdditionSerializer,
    MPINVerifySerializer,
    VerifyVendorSerializer,
    VendorBankAccountSerializer,
    VendorFeedbackSerializer,
    VendorFeedbackReplySerializer,
    OrderListSerializer,
    OrderListByIdSerializer,
    UpdateOrderStatusSerializer,
    VendorContactUpdateSerializer,
    VendorLocationUpdateSerializer,
    VendorDocumentUpdateSerializer,
    CakeOptionsSerializer,
    DeliveryOptionsSerializer,
    CelebrityBannerSerializer,
    BestDealBannerSerializer,

)

from .utils import (
    generate_numeric_otp,
    send_otp_email, 
    send_otp_sms,
    mask_email,
    mask_phone,
    VerifyIsRegistered,
    UserIdentifierhelper,
    calculate_file_hash,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from user_agents import parse
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
import logging
import boto3
import uuid
import os
from rest_framework.views import APIView
from user.models import OrderStatus

logger = logging.getLogger("django")


class VendorBasicDetailsAPI(generics.CreateAPIView, generics.UpdateAPIView):
    serializer_class = VendorBasicSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "message": "Vendor basic details created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        instance = Vendor.objects.get(id=kwargs.get('id'))
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "message": "Vendor basic details updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Vendor Details']))
class GetVendorDescriptionAPI(generics.GenericAPIView):
    serializer_class = VenderBusinessDescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        vendor = request.user   

        if not vendor:
            return Response({
                "status": False,
                "message": "Vendor not found."
            }, status=status.HTTP_404_NOT_FOUND)

        description_obj, _ = VenderBusinessDescription.objects.get_or_create(
            vendor=vendor,
            vendor_reg_id=vendor.vendor_id
        )

        serializer = self.get_serializer(description_obj)

        return Response({
            "status": True,
            "message": "Vendor description fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Vendor Details']))
class VendorDescriptionAPI(generics.GenericAPIView):
    serializer_class = VenderBusinessDescriptionSerializer
    permission_classes = [IsAuthenticated]

    def put(self, request):
        vendor = request.user  

        if not vendor:
            return Response({
                "status": False,
                "message": "Vendor not found."
            }, status=status.HTTP_404_NOT_FOUND)

        description_obj, created = VenderBusinessDescription.objects.get_or_create(
            vendor=vendor,
            vendor_reg_id=vendor.vendor_id
        )

        serializer = self.get_serializer(description_obj, data=request.data, partial=True)

        if serializer.is_valid():
            instance = serializer.save(updated_by=request.user.email)

            if created and not instance.created_by:
                instance.created_by = request.user.email
                instance.save(update_fields=['created_by'])

            return Response({
                "status": True,
                "message": "Vendor description updated successfully.",
                "data": self.get_serializer(instance).data
            }, status=status.HTTP_200_OK)

        return Response({
            "status": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class VendorListCreateAPI(generics.ListCreateAPIView):
    serializer_class = VendorSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Vendor.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "message": "Fetched all vendors",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "message": "Vendor created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

class VendorRetrieveUpdateDeleteAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = VendorSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Vendor.objects.all()
    lookup_field = "id"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            "status": "success",
            "message": "Vendor fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            "status": "success",
            "message": "Vendor updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({
            "status": "success",
            "message": "Vendor deleted successfully"
        }, status=status.HTTP_200_OK)
    
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Vendor Signup']))
class VendorSignupView(generics.GenericAPIView):
    serializer_class = VendorSignupSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": False,
                "message": "Validation failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        contact_no = serializer.validated_data.get("contact_no")
        documents_data = request.data.get("documents", [])

        # Check TEMP documents exist
        uploaded_docs = VendorDocument.objects.filter(
            vendor_business_no=str(contact_no),
            status="TEMP"
        )

        if not uploaded_docs.exists():
            return Response({
                "error": "Please upload at least one document before registration."
            }, status=status.HTTP_400_BAD_REQUEST)

        matched_doc_ids = []

        for doc in documents_data:
            doc_type = doc.get("document_type", "")
            doc_url = doc.get("document_url", "")

            #skip completely invalid entries
            if not doc_type or not doc_url:
                continue
            doc_type = str(doc_type).strip()
            doc_url = str(doc_url).strip()

            # skip empty/blank values
            if not doc_type or not doc_url:
                continue

            # match by type & full static url
            clen_url = doc_url.split("?")[0
                                          ]
            matching_docs = uploaded_docs.filter(
                document_type__iexact=doc_type,
                document_url__iexact=clen_url    #safer match
            )

            if matching_docs.exists():
                matched_doc_ids.extend(
                    list(matching_docs.values_list("id", flat=True))
                )

        matched_doc_ids = list(set(matched_doc_ids))  # remove duplicates

        if not matched_doc_ids:
            return Response({
                "error": "No valid uploaded document matched."
            },
            status=status.HTTP_400_BAD_REQUEST)

        # Collect device info
        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(user_agent_string)
        if user_agent.is_mobile:
            device_type = "Mobile"
        elif user_agent.is_tablet:
            device_type = "Tablet"
        elif user_agent.is_pc:
            device_type = "Desktop"
        else:
            device_type = "Other"
            
        os_family = user_agent.os.family or ""
        if "Android" in os_family:
            os_type = "Android"
        elif "iOS" in os_family:
            os_type = "iOS"
        else:
            os_type = os_family or "Other"

        device_info = {
            "device_type": device_type,
            "os_version": user_agent.os.version_string,
            "browser_name": user_agent.browser.family,
            "browser_version": user_agent.browser.version_string,
            "os_type": os_type,
        }

        # create vendor only after all validations passed
        vendor = serializer.save()

        #convert TEMP -> PERMANENT for matched documents
        VendorDocument.objects.filter(
            id__in=matched_doc_ids).update(status="PERMANENT")
        
        vendor.document_id = matched_doc_ids
        vendor.save(update_fields=["document_id"])

        VendorDevice.objects.update_or_create(
            vendor_id=vendor,
            device_type=device_info["device_type"],
            os_version=device_info["os_version"],
            browser_name=device_info["browser_name"],
            os_type=device_info["os_type"],
            defaults={"browser_version": device_info["browser_version"]}
        )

        # refresh = RefreshToken.for_user(AdminUser)
        refresh = RefreshToken.for_user(vendor.auth_user)
        vendor_data = self.get_serializer(vendor).data
        vendor_data.update({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "device_info": device_info
        })

        return Response({
            "status": True,
            "message": "Vendor registered successfully.",
            "data": vendor_data
        }, status=status.HTTP_201_CREATED)



@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Vendor login']))
class VendorLoginView(generics.GenericAPIView):
    serializer_class = VendorLoginSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            errors = serializer.errors.get("non_field_errors")
            error = errors[0] if errors else "Invalid data"
            return Response({
                "status": False,
                "errors": error
            }, status=status.HTTP_400_BAD_REQUEST)

        # user = serializer.validated_data['user']
        admin_user = serializer.validated_data["admin_user"]
        vendor = serializer.validated_data["vendor"]


        user_agent_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(user_agent_string)

        if user_agent.is_mobile:
            device_type = "Mobile"
        elif user_agent.is_tablet:
            device_type = "Tablet"
        elif user_agent.is_pc:
            device_type = "Desktop"
        else:
            device_type = "Other"

        os_family = user_agent.os.family or ""
        if "Android" in os_family:
            os_type = "Android"
        elif "iOS" in os_family:
            os_type = "iOS"
        else:
            os_type = os_family or "Other"

        device_info = {
        "device_type": device_type,
        "os_version": user_agent.os.version_string,
        "browser_name": user_agent.browser.family,
        "browser_version": user_agent.browser.version_string,
        "os_type": os_type

        }

        # Save or update device
        VendorDevice.objects.update_or_create(
            vendor_id=vendor,
            device_type=device_info["device_type"],
            os_version=device_info["os_version"],
            browser_name=device_info["browser_name"],
            os_type=device_info["os_type"],
            defaults={
                "browser_version": device_info["browser_version"],
            }
            )
        # RefreshTokenStore.objects.filter(user=user).delete()
        admin_user = vendor.auth_user
        refresh = RefreshToken.for_user(admin_user)
        # Create new refresh+access tokens
        # refresh = RefreshToken.for_user(user)
        RefreshTokenStore.objects.create(
            user=admin_user,
            refresh_token= str(refresh)

        )
        vendor_data = VendorDataSerializer(vendor).data
        vendor_data.update({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "device_info": device_info
        })

        return Response({
            "status": True,
            "message": "Login successful",
            "data": vendor_data
        }, status=status.HTTP_200_OK)


@method_decorator(name='post', decorator=swagger_auto_schema(tags=['sendEmail- otp']))
class RequestEmailOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RequestEmailOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        masked_email = mask_email(email)

        try:
            with transaction.atomic():
                # Get or create verification record first
                verification, created = EmailVerification.objects.get_or_create(email=email)

                 # Check if the user is temporarily blocked
                remaining_block = verification._is_blocked()
                if remaining_block:
                    return Response({
                        "status": False,
                        "message": f"Too many failed attempts. Try again after {remaining_block} seconds."
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Cooldown check (60 seconds)
                if not verification.can_request_new_otp():
                    return Response({
                        "status": False,
                        "message": "Please wait at least 60 seconds before requesting another OTP."
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # generate and set OTP using model method
                otp = str(123456) #generate_numeric_otp()
                verification.set_otp(otp)

        except Exception as e:
            logger.exception("Error generating email OTP")
            return Response({
                "status": False,
                "message": f"Failed to process OTP: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # send email OTP
        email_sent = send_otp_email(email, otp)
        return Response({
            "status": True,
            "message": f"OTP sent successfully to {masked_email}",
            "email_sent": email_sent == 202
        }, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['sendPhone otp'])) 
class RequestPhoneOTPView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RequestPhoneOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data.get('phone')
        masked_phone = mask_phone(phone)

        try:
            with transaction.atomic():
                # Get or create verification record first
                verification, created = PhoneVerification.objects.get_or_create(phone=phone)

                # Check if the user is temporarily blocked
                remaining_block = verification._is_blocked()
                if remaining_block:
                    return Response({
                        "status": False,
                        "message": f"Too many failed attempts. Try again after {remaining_block} seconds."
                    }, status=status.HTTP_403_FORBIDDEN)
                
                # Cooldown check (60 seconds)
                if not verification.can_request_new_otp():
                    return Response({
                        "status": False,
                        "message": "Please wait at least 60 seconds before requesting another OTP."
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)

                # Generate and set OTP
                otp = str(123456) #generate_numeric_otp()
                verification.set_otp(otp)

        except Exception as e:
            logger.exception("Error generating phone OTP")
            return Response({
                "status": False,
                "message": f"Failed to process OTP: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Send SMS OTP
        sms_sent = True #send_otp_sms(phone, otp)

        return Response({
            "status": True,
            "message": f"OTP sent successfully to {masked_phone}",
            "sms_sent": sms_sent
        }, status=status.HTTP_200_OK)
    

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['VerifyOTP - Email']))
class VerifyEmailOTPView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = VerifyEmailOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        raw_otp = serializer.validated_data['otp']
        masked_email = mask_email(email)

        verification = get_object_or_404(EmailVerification, email=email)

        remaining_block = verification._is_blocked()
        if remaining_block:
            return Response({
                "status": False,
                "message": f"Too many failed attempts. Try again after {remaining_block} seconds."
                }, status=status.HTTP_403_FORBIDDEN)
        
        # validate OTP
        if not verification.check_otp(raw_otp):
            verification.mark_attempt()
            return Response({
                "status": False,
                "message": "Invalid or expired OTP."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # mark email as verified
        with transaction.atomic():
            verified = verification.mark_verified()

        return Response({
            "status": True,
            "message": "Email Verified successfully.",
            "email": masked_email,
            "is_email_verified": verified
        }, status=status.HTTP_200_OK)
    
    
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['VerifyOTP - Phone']))
class VerifyPhoneOTPView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = VerifyPhoneOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone = serializer.validated_data['phone']
        otp = serializer.validated_data['otp']  
        masked_phone = mask_phone(phone)

        verification = get_object_or_404(PhoneVerification, phone=phone)

        #check if temporary blocked
        remaining_block = verification._is_blocked()
        if remaining_block:
            return Response({
                "status": False,
                "message": f"Too many failed attempts. Try again after {remaining_block} seconds."
            }, status=status.HTTP_403_FORBIDDEN)

        #validate OTP
        if not verification.check_otp(otp):
            verification.mark_attempt()
            return Response({
                "status": False,
                "message": "Invalid or Expired OTP."
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        #mark phone as verified
        with transaction.atomic():
            verified = verification.mark_verified()
            
        return Response({
            "status": True,
            "message": "Phone verified successfully.",
            "Phone:": masked_phone,
            "is_phone_verified": verified,
        }, status=status.HTTP_200_OK)

class VendorDocumentUploadAPIView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = (OAuth2Authentication, JWTAuthentication)

    def post(self, request, *args, **kwargs):
        try:
            phone = request.data.get("vendor_business_no")
            document_type = request.data.get("document_type")
            section_type = request.data.get("section_type")
            image = request.FILES.get("file")
            company_type_id = request.data.get("company_type")

            if not all([phone, document_type, image, company_type_id]):
                return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 1: Get verification entry using phone
            verification = PhoneVerification.objects.filter(phone=phone, is_verified=True).first()
            if not verification:
                return Response({"error": "Phone number not verified"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 2: Get CompanyTypeMaster instance using id
            try:
                company_type_obj = CompanyTypeMaster.objects.get(id=company_type_id)
            except CompanyTypeMaster.DoesNotExist:
                return Response({"error": "Invalid company_type id"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 3: Delete expired TEMP docs
            now = timezone.now()
            VendorDocument.objects.filter(status='TEMP', expires_at__lt=now).update(status='DELETED')

            # Step 4: Upload to S3
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret"),
            )
            bucket = config("S3_BUCKET_NAME")

            # Generate unique filename
            file_ext = os.path.splitext(image.name)[1] 
            unique_name = f"{uuid.uuid4().hex}{file_ext}"  
            key = f"vendor_documents/{phone}/{unique_name}"

            s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})
            document_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            # Step 5: Save in DB
            doc = VendorDocument.objects.create(
                verification=verification,
                company_type=company_type_obj,
                document_type=document_type,
                document_url=document_url,
                status="TEMP",
                vendor_business_no=phone,
                expires_at=timezone.now() + timedelta(hours=1),
            )

            serializer = VendorDocumentSerializer(doc)
            return Response({
                "message": f"{document_type} uploaded successfully.",
                "document": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['ForgotMPIN']))
class ForgotMPINView(APIView):

    def post(self, request):
        serializer = ForgotMPINRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        phone = serializer.validated_data.get('phone')

        if email:
            channel = 'email'
            verification = EmailVerification.objects.filter(email=email, is_verified=True).first()
        else:
            channel = 'phone'
            verification = PhoneVerification.objects.filter(phone=phone, is_verified=True).first()

        if not verification:
            return Response({
                "status": False,
                "message": "No verified record found. Please verify your email or phone first."
            }, status=status.HTTP_404_NOT_FOUND)
        
        if verification._is_blocked():
            return Response({
                "status": False,
                "message": "Too many failed attempts. Please try again later."
            }, status=status.HTTP_403_FORBIDDEN)

        if not verification.can_request_new_otp():
            return Response({
                "status": False,
                "message": "Please wait at least 60 seconds before requesting another OTP."
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        otp = str(123456) #generate_numeric_otp()
        verification.set_otp(otp)

        # Send OTP
        if channel == 'email':
            email_sent = send_otp_email(email, otp)
            masked_email = mask_email(email)
            message = f"OTP sent successfully to {masked_email}"
            return Response({
                "status": True,
                "message": message,
                "email_sent": email_sent
            }, status=status.HTTP_200_OK)

        else:
            sms_sent = send_otp_sms(phone, otp)
            masked_phone = mask_phone(phone)
            message = f"OTP sent successfully to {masked_phone}"
            return Response({
                "status": True,
                "message": message,
                "sms_sent": True #sms_sent
            }, status=status.HTTP_200_OK)


@method_decorator(name='post', decorator=swagger_auto_schema(tags=['VerifyOTP - Forgot MPIN']))
class VerifyMPINOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')
        phone = request.data.get('phone')
        otp = request.data.get('otp')

        if not otp:
            return Response({
                "status": False,
                "message": "OTP is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not email and not phone:
            return Response({
                "status": False,
                "message": "Email or phone is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine which verification model to use
        if email:
            verification = get_object_or_404(EmailVerification, email=email)
            channel = "email"
            masked_value = mask_email(email)
        else:
            verification = get_object_or_404(PhoneVerification, phone=phone)
            channel = "phone"
            masked_value = mask_phone(phone)

        remaining_block = verification._is_blocked()
        if remaining_block:
            return Response({
                "status": False,
                "message": f"Too many failed attempts. Try again after {remaining_block} seconds."
            }, status=status.HTTP_403_FORBIDDEN)

        if not verification.check_otp(otp):
            verification.mark_attempt()
            return Response({
                "status": False,
                "message": "Invalid or expired OTP."
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "status": True,
            "message": f"{channel.title()} verified successfully.",
            channel: masked_value,
            f"is_{channel}_verified": True
        }, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['ResetMPIN']))
class ChangeMPINView(APIView):
    def post(self, request):
        serializer = ChangeMPINSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()

            return Response({
                "status": True,
                "message": "MPIN changed successfully."
            },
            status=status.HTTP_200_OK)

        return Response({
            "status": False,
            "errors": serializer.errors
        },
        status=status.HTTP_400_BAD_REQUEST)

class UploadDefaultVendorImageAPIView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Please upload a file."}, status=status.HTTP_400_BAD_REQUEST)

        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('s3AccessKey'),
            aws_secret_access_key=os.getenv('s3Secret')
        )

        file_key = os.getenv('DEFAULT_VENDOR_IMAGE_PATH', 'defaults/vendor_default.png')
        bucket_name = os.getenv('S3_BUCKET_NAME')

        try:
            # Upload file to S3 in the defined default path
            s3.upload_fileobj(file_obj, bucket_name, file_key, ExtraArgs={'ACL': 'public-read'})

            image_url = f"https://{bucket_name}.s3.amazonaws.com/{file_key}"

            return Response({
                "status": True,
                "message": "Default vendor image uploaded successfully.",
                "default_image_url": image_url
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                "status": False,
                "message": f"Upload failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VendorProfileImageUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "Please upload an image file."}, status=status.HTTP_400_BAD_REQUEST)

        max_size = 4 * 1024 * 1024
        if file_obj.size > max_size:
            return Response(
                {"error": "File size exceeds 4 MB limit."},
                status=status.HTTP_400_BAD_REQUEST
            )

        vendor = request.user
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("s3AccessKey"),
            aws_secret_access_key=os.getenv("s3Secret"),
        )

        bucket = os.getenv("S3_BUCKET_NAME")

        ext = os.path.splitext(file_obj.name)[1]
        unique_name = f"{uuid.uuid4().hex}{ext}"

        file_key = f"vendors/{vendor.vendor_id}/{unique_name}"

        try:
            s3.upload_fileobj(file_obj, bucket, file_key, ExtraArgs={'ACL': 'public-read'})
            image_url = f"https://{bucket}.s3.amazonaws.com/{file_key}"

            vendor.profile_image = image_url
            vendor.save(update_fields=['profile_image'])

            return Response({
                "status": True,
                "message": "Profile image uploaded successfully.",
                "profile_image": image_url
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "status": False,
                "message": f"Upload failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorProfileImageDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        vendor = request.user
        default_image = os.getenv('DEFAULT_VENDOR_IMAGE_PATH')

        vendor.profile_image = default_image
        vendor.save(update_fields=['profile_image'])

        return Response({
            "status": True,
            "message": "Profile image reset to default.",
            "profile_image": default_image
        }, status=status.HTTP_200_OK)

# Base class for S3 Upload
class ReadyToSellBaseView(APIView):
    def upload_to_s3(self, file_obj):
        """Uploads a file to S3 and returns its public URL."""
        s3 = boto3.client(
            "s3",
            aws_access_key_id=config("s3AccessKey"),
            aws_secret_access_key=config("s3Secret"),
        )
        bucket = config("S3_BUCKET_NAME")
        key = f"ready_to_sell/{file_obj.name}"
        s3.upload_fileobj(file_obj, bucket, key, ExtraArgs={"ACL": "public-read"})
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['ready_to_sell']))
class CreateReadyToSellItemView(ReadyToSellBaseView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        product_name = request.data.get("product_name")
        price = request.data.get("price")
        description = request.data.get("description", "")
        files = request.FILES.getlist("images")

        if not product_name or not price:
            return Response({
                "status": False,
                "message": "Product name and price are required.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        allowed_ext = (".png", ".jpg", ".jpeg", ".gif")
        invalid_files = [f.name for f in files if not f.name.lower().endswith(allowed_ext)]
        if invalid_files:
            return Response({
                "status": False,
                "message": f"Invalid file type(s): {', '.join(invalid_files)}. Only images are allowed.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        uploaded_urls = []
        if files:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.upload_to_s3, f) for f in files]
                for future in futures:
                    uploaded_urls.append(future.result())

        status_obj = get_status("Active")
        item = ReadyToSellItem.objects.create(
            product_name=product_name.strip(),
            price=price,
            description=description.strip(),
            image_urls=uploaded_urls,
            status=status_obj,
        )

        return Response({
            "status": True,
            "message": "Item created successfully.",
            "data": ReadyToSellItemSerializer(item).data
        }, status=status.HTTP_201_CREATED)

@method_decorator(name="get", decorator=swagger_auto_schema(tags=["ready_to_sell"]))
class GetAllReadyToSellItemsView(generics.ListAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ReadyToSellItemSerializer

    def get_queryset(self):
        """Fetch only non-deleted items"""
        active_status = get_status("Active")
        return ReadyToSellItem.objects.filter(status=active_status).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "Active items fetched successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)

@method_decorator(name="get", decorator=swagger_auto_schema(tags=["ready_to_sell"]))
class GetReadyToSellItemByIDView(generics.RetrieveAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ReadyToSellItemSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Exclude deleted items"""
        deleted_status = get_status("Deleted")
        return ReadyToSellItem.objects.exclude(status=deleted_status)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_queryset().get(id=kwargs["id"])
        except ReadyToSellItem.DoesNotExist:
            return Response({
                "status": False,
                "message": "Item not found or has been deleted.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response({
            "status": True,
            "message": "Item fetched successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['ready_to_sell']))
class UpdateReadyToSellItemView(ReadyToSellBaseView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def put(self, request, id):
        try:
            item = ReadyToSellItem.objects.get(id=id)
        except ReadyToSellItem.DoesNotExist:
            return Response({
                "status": False,
                "message": "Item not found.",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        product_name = request.data.get("product_name", item.product_name)
        price = request.data.get("price", item.price)
        description = request.data.get("description", item.description)
        status_name = request.data.get("status")

        status_obj = get_status(status_name) if status_name else item.status

        files = request.FILES.getlist("images")
        if files:
            allowed_ext = (".png", ".jpg", ".jpeg", ".gif")
            new_urls = []
            for f in files:
                if not f.name.lower().endswith(allowed_ext):
                    return Response({
                        "status": False,
                        "message": f"Invalid file type for {f.name}.",
                        "data": None
                    }, status=status.HTTP_400_BAD_REQUEST)
                new_urls.append(self.upload_to_s3(f))
            item.image_urls.extend(new_urls)

        item.product_name = product_name
        item.price = price
        item.description = description
        item.status = status_obj
        item.updated_at = timezone.now()
        item.save()

        return Response({
            "status": True,
            "message": "Item updated successfully.",
            "data": ReadyToSellItemSerializer(item).data
        }, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['ready_to_sell']))
class DeleteReadyToSellItemView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def delete(self, request, id):
        """
        delete an item by marking its status as 'Deleted'.
        """
        try:
            item = ReadyToSellItem.objects.get(id=id)
        except ReadyToSellItem.DoesNotExist:
            return Response({
                "status": False,
                "message": "Item not found.",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_status = get_status("Deleted")
        if item.status == deleted_status:
            return Response({
                "status": False,
                "message": "Item is already deleted.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        item.status = deleted_status
        item.updated_at = timezone.now()
        item.save(update_fields=["status", "updated_at"])

        return Response({
            "status": True,
            "message": "Item deleted successfully.",
            "data": None
        }, status=status.HTTP_200_OK)
    
class VendorRegistrationProfileAPIView(generics.GenericAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = VendorRegistrationSerializer

    def get(self, request, *args, **kwargs):
        user_email = getattr(request.user, 'email', None)
        user_username = getattr(request.user, 'username', None)

        vendor = None
        if user_email:
            vendor = Vendor_registration.objects.filter(email__iexact=user_email).first()
        if not vendor and user_username:
            vendor = Vendor_registration.objects.filter(contact_no__iexact=user_username).first()

        if not vendor:
            return Response({
                "status": False,
                "message": "Vendor profile not found for the authenticated user."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(vendor)
        return Response({
            "status": True,
            "message": "Vendor profile fetched successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
class VendorBasicDetailsUpdateAPIView(generics.UpdateAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = VendorBasicDetailsSerializer

    def get_object(self):
        user_email = getattr(self.request.user, 'email', None)
        user_username = getattr(self.request.user, 'username', None)

        vendor = None
        if user_email:
            vendor = Vendor_registration.objects.filter(email__iexact=user_email).first()
        if not vendor and user_username:
            vendor = Vendor_registration.objects.filter(contact_no__iexact=user_username).first()

        return vendor

    def update(self, request, *args, **kwargs):
        vendor = self.get_object()
        if not vendor:
            return Response({
                "status": False,
                "message": "Vendor not found."
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(vendor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": True,
                "message": "Basic details updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "status": False,
            "message": "Validation failed.",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class VendorSocialMediaView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = VendorSocialMediaSerializer

    def get(self, request):
        try:
            vendor = Vendor_registration.objects.filter(
                email=request.user.email
            ).first()

            if not vendor:
                return Response({
                    "status": False,
                    "message": "Vendor not found for this user."
                }, status=status.HTTP_404_NOT_FOUND)

            social_media, _ = VendorSocialMedia.objects.get_or_create(
                vendor=vendor,
                vendor_reg_id=vendor.vendor_id
            )

            serializer = self.get_serializer(social_media)
            return Response({
                "status": True,
                "message": "Social media details fetched successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            traceback.print_exc()
            return Response({
                "status": False,
                "message": f"Error fetching social media: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        try:
            vendor = Vendor_registration.objects.filter(
                email=request.user.email
            ).first()

            if not vendor:
                return Response({
                    "status": False,
                    "message": "Vendor not found for this user."
                }, status=status.HTTP_404_NOT_FOUND)

            social_media, created = VendorSocialMedia.objects.get_or_create(
                vendor=vendor,
                vendor_reg_id=vendor.vendor_id
            )

            serializer = self.get_serializer(social_media, data=request.data, partial=True)
            if serializer.is_valid():
                instance = serializer.save(updated_by=request.user.email)

                if created and not instance.created_by:
                    instance.created_by = request.user.email
                    instance.save(update_fields=["created_by"])

                return Response({
                    "status": True,
                    "message": "Social media details updated successfully.",
                    "data": self.get_serializer(instance).data
                }, status=status.HTTP_200_OK)

            return Response({
                "status": False,
                "message": "Invalid data.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            traceback.print_exc()
            return Response({
                "status": False,
                "message": f"Error updating social media: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


class VendorMediaUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    MAX_IMAGE_COUNT = 10
    MAX_VIDEO_COUNT = 3
    MAX_IMAGE_SIZE_MB = 5
    MAX_VIDEO_SIZE_MB = 20

    def post(self, request):
        try:
            vendor = request.user   
            vendor_id = vendor.vendor_id

            images = request.FILES.getlist("images")
            videos = request.FILES.getlist("videos")

            if not images and not videos:
                return Response({"error": "No files uploaded"}, status=400)

            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret")
            )
            bucket = config("S3_BUCKET_NAME")

            uploaded_items = []
            skipped_duplicates = []

            # ---------------------------
            # IMAGES
            # ---------------------------
            existing_img = VendorMedia.objects.filter(
                vendor=vendor,
                media_type="IMAGE",
                status="ACTIVE"
            ).count()

            if images:
                if existing_img + len(images) > self.MAX_IMAGE_COUNT:
                    return Response({"error": f"Max {self.MAX_IMAGE_COUNT} images allowed"}, status=400)

                for img in images:
                    file_hash = calculate_file_hash(img)

                    duplicate = VendorMedia.objects.filter(
                        vendor=vendor,
                        file_hash=file_hash,
                        status="ACTIVE"
                    ).exists()

                    if duplicate:
                        skipped_duplicates.append(img.name)
                        continue  # ← Duplicate skip, upload NO stop

                    if img.size > self.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                        skipped_duplicates.append(img.name + " (size too large)")
                        continue

                    ext = os.path.splitext(img.name)[1]
                    unique = f"{uuid.uuid4().hex}{ext}"
                    key = f"vendor_media/{vendor_id}/{unique}"

                    s3.upload_fileobj(img, bucket, key, ExtraArgs={"ACL": "public-read"})
                    url = f"https://{bucket}.s3.amazonaws.com/{key}"

                    media = VendorMedia.objects.create(
                        vendor=vendor,
                        file_url=url,
                        file_name=unique,
                        media_type="IMAGE",
                        file_hash=file_hash
                    )
                    uploaded_items.append(VendorMediaSerializer(media).data)

            # ---------------------------
            # VIDEOS
            # ---------------------------
            existing_vid = VendorMedia.objects.filter(
                vendor=vendor,
                media_type="VIDEO",
                status="ACTIVE"
            ).count()

            if videos:
                if existing_vid + len(videos) > self.MAX_VIDEO_COUNT:
                    return Response({"error": f"Max {self.MAX_VIDEO_COUNT} videos allowed"}, status=400)

                for vid in videos:
                    file_hash = calculate_file_hash(vid)

                    duplicate = VendorMedia.objects.filter(
                        vendor=vendor,
                        file_hash=file_hash,
                        status="ACTIVE"
                    ).exists()

                    if duplicate:
                        skipped_duplicates.append(vid.name)
                        continue

                    if vid.size > self.MAX_VIDEO_SIZE_MB * 1024 * 1024:
                        skipped_duplicates.append(vid.name + " (size too large)")
                        continue

                    ext = os.path.splitext(vid.name)[1]
                    unique = f"{uuid.uuid4().hex}{ext}"
                    key = f"vendor_media/{vendor_id}/{unique}"

                    s3.upload_fileobj(vid, bucket, key, ExtraArgs={"ACL": "public-read"})
                    url = f"https://{bucket}.s3.amazonaws.com/{key}"

                    media = VendorMedia.objects.create(
                        vendor=vendor,
                        file_url=url,
                        file_name=unique,
                        media_type="VIDEO",
                        file_hash=file_hash
                    )
                    uploaded_items.append(VendorMediaSerializer(media).data)

            return Response({
                "message": "Upload completed",
                "uploaded": uploaded_items,
                "skipped_duplicates": skipped_duplicates
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class VendorMediaListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request):
        vendor = request.user

        media = VendorMedia.objects.filter(
            vendor=vendor,
            status="ACTIVE"
        ).order_by("-created_at")

        return Response({
            "status": True,
            "count": media.count(),
            "media": VendorMediaSerializer(media, many=True).data
        }, status=200)


class VendorMediaDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def delete(self, request, media_id):
        vendor = request.user

        try:
            media = VendorMedia.objects.get(
                id=media_id,
                vendor=vendor,
                status="ACTIVE"
            )
        except VendorMedia.DoesNotExist:
            return Response({
                "status": False,
                "message": "Media not found"
            }, status=404)

        media.status = "DELETED"
        media.save(update_fields=["status"])

        return Response({
            "status": True,
            "message": "Media deleted successfully"
        }, status=200)
        
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Product Details']))
class VendorServiceCreateAPIView(generics.CreateAPIView):
    queryset = VendorProduct.objects.all()
    serializer_class = VendorServiceSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def post(self, request, *args, **kwargs):
        user = request.user

        # Only vendors can create services
        if not isinstance(user, Vendor_registration):
            return Response(
                {"message": "Only vendors can create product.", "status": False},
                status=status.HTTP_403_FORBIDDEN
            )

        # Parse and validate 'data'
        service_data = request.data.get("data", {})
        if isinstance(service_data, str):
            try:
                service_data = json.loads(service_data)
            except Exception:
                return Response({"message": "Invalid JSON for 'data' field.", "status": False}, status=400)
        if not isinstance(service_data, dict):
            service_data = {}

        if "images" not in service_data or not isinstance(service_data["images"], list):
            service_data["images"] = []

        # Handle S3 images
        images = request.FILES.getlist("image")
        if images:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret"),
            )
            bucket = config("S3_BUCKET_NAME")
            for image in images:
                key = f"vendor_Products/{image.name}"
                try:
                    s3.upload_fileobj(
                        Fileobj=image,
                        Bucket=bucket,
                        Key=key,
                        ExtraArgs={"ACL": "public-read", "ContentType": image.content_type}
                    )
                    image_url = f"https://{bucket}.s3.amazonaws.com/{key}"
                    service_data["images"].append(image_url)
                except Exception as e:
                    logger.error(f"S3 upload failed: {str(e)}")

        # Prepare serializer input
        serializer_input = {
            "data": service_data,
            "status": request.data.get("status", 1)
        }

        serializer = self.get_serializer(data=serializer_input, context={"request": request})
        serializer.is_valid(raise_exception=True)
        service = serializer.save()

        response_serializer = self.get_serializer(service)
        return Response({
            "message": "Product Added successfully.",
            "data": response_serializer.data,
            "status": True
        }, status=status.HTTP_201_CREATED)
    

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Product Details']))
class VendorServiceListAPIView(generics.ListAPIView):
    serializer_class = VendorServiceSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        vendor = self.request.user
        product_id = self.kwargs.get('product_id')

        if not product_id:
            raise PermissionDenied("Product ID is required.")

        try:
            active_status = StatusMaster.objects.get(status_type__iexact='Active')
        except StatusMaster.DoesNotExist:
            logger.warning("[VendorServiceListAPIView] 'Active' status not found in StatusMaster")
            raise PermissionDenied("Active status not found in the system")

        # Filter by vendor, active status, and product_id inside the data JSONField
        queryset = VendorProduct.objects.filter(
            vendor_id=vendor.id,
            status=active_status,
            id=product_id  
        )
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "message": "product fetched successfully",
                "data": serializer.data,
                "status": True
            })
        except PermissionDenied as e:
            logger.warning(f"[VendorServiceListAPIView] Permission denied: {str(e)}")
            return Response({
                "message": str(e),
                "status": False
            }, status=403)
        except Exception as e:
            logger.exception(f"[VendorServiceListAPIView] Unexpected error while listing vendor product: {str(e)}")
            return Response({
                "message": "An unexpected error occurred while fetching vendor Product.",
                "error": str(e),
                "status": False
            }, status=500)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Product Details']))
class VendorServiceUpdateAPIView(generics.UpdateAPIView):
    serializer_class = VendorServiceSerializer
    permission_classes = [IsAuthenticated, IsVendor]
    parser_classes = (MultiPartParser, FormParser)  

    def get_object(self):
        vendor = self.request.user
        product_id = self.kwargs.get('product_id')

        if not product_id:
            raise PermissionDenied("Product ID is required.")

        try:
            active_status = StatusMaster.objects.get(status_type__iexact='Active')
        except StatusMaster.DoesNotExist:
            raise PermissionDenied("Active status not found in the system")

        try:
            service = VendorProduct.objects.get(
                id=product_id,
                vendor_id=vendor.id,
                status=active_status
            )
        except VendorProduct.DoesNotExist:
            raise PermissionDenied("Product not found for this vendor.")

        return service

    def update(self, request, *args, **kwargs):
        try:
            service = self.get_object()

            service_data = request.data.get("data", {})
            if isinstance(service_data, str):
                service_data = json.loads(service_data)

            if "images" not in service_data or not isinstance(service_data["images"], list):
                service_data["images"] = []

            # ---- STEP 1: Load old images from DB ----
            old_data = service.data or {}
            old_images = old_data.get("images", [])

            # ---- STEP 2: Identify which images user kept ----
            images_user_kept = service_data["images"]

            # Images removed by user:
            removed_images = [img for img in old_images if img not in images_user_kept]


            # ---- STEP 3: Upload new images from request.FILES ----
            images = request.FILES.getlist("image")
            if images:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret"),
                )
                bucket = config("S3_BUCKET_NAME")

                for image in images:
                    key = f"vendor_products/{image.name}"
                    s3.upload_fileobj(
                        Fileobj=image,
                        Bucket=bucket,
                        Key=key,
                        ExtraArgs={"ACL": "public-read", "ContentType": image.content_type}
                    )
                    image_url = f"https://{bucket}.s3.amazonaws.com/{key}"
                    images_user_kept.append(image_url)

            # ---- STEP 4: Final list of images to save ----
            service_data["images"] = list(set(images_user_kept))

            # ---- STEP 5: Save updated product ----
            serializer = self.get_serializer(service, data={"data": service_data}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save(updated_by=request.user.username)

            return Response({
                "message": "Product updated successfully",
                "data": serializer.data,
                "status": True
            })

        except Exception as e:
            logger.exception(str(e))
            return Response({"message": "Error", "error": str(e), "status": False}, status=500)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Product Details']))       
class VendorServiceAllAPIView(generics.ListAPIView):
    serializer_class = VendorServiceSerializer
    permission_classes = [IsAuthenticated, IsVendor]

    def get_queryset(self):
        vendor = self.request.user

        try:
            # Get the Active status
            active_status = StatusMaster.objects.get(status_type__iexact='Active')
            
            # Only return services with Active status
            queryset = VendorProduct.objects.filter(vendor_id=vendor.id, status=active_status).order_by('id')

        except StatusMaster.DoesNotExist:
            # If Active status does not exist, return empty queryset
            logger.warning("[VendorServiceAllAPIView] 'Active' status not found. Returning empty list.")
            queryset = VendorProduct.objects.none()
        except Exception as e:
            logger.exception(f"[VendorServiceAllAPIView] Error fetching Product: {str(e)}")
            queryset = VendorProduct.objects.none()

        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "message": "Active vendor Product fetched successfully",
                "data": serializer.data,
                "status": True
            })
        except Exception as e:
            logger.exception(f"[VendorServiceAllAPIView] Unexpected error: {str(e)}")
            return Response({
                "message": "An unexpected error occurred while fetching vendor Product.",
                "error": str(e),
                "status": False
            }, status=500)
        

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Product Details']))
class VendorServiceDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsVendor]

    def get_object(self):
        vendor = self.request.user
        product_id = self.kwargs.get('product_id')

        if not product_id:
            raise PermissionDenied("Product ID is required.")

        try:
            service = VendorProduct.objects.get(vendor_id=vendor.id, id=product_id)
        except VendorProduct.DoesNotExist:
            raise PermissionDenied("product ID not found or you don't have permission to delete it.")

        return service

    def delete(self, request, *args, **kwargs):
        try:
            service = self.get_object()

            # Get Inactive status
            try:
                inactive_status = StatusMaster.objects.get(status_type__iexact='Inactive')
            except StatusMaster.DoesNotExist:
                return Response({
                    "message": "'Inactive' status not defined in the system.",
                    "status": False
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Soft delete the service
            service.status = inactive_status
            service.save()

            return Response({
                "message": "Product deleted successfully",
                "status": True
            })

        except PermissionDenied as e:
            return Response({"message": str(e), "status": False}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.exception(f"[VendorServiceSoftDeleteAPIView] Error deleting Product: {str(e)}")
            return Response({
                "message": "An unexpected error occurred while deleting the Product.",
                "error": str(e),
                "status": False
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ProductAdditionBaseView(APIView):
    def upload_to_s3(self, file_obj):
        """Uploads image to S3 and returns URL."""
        s3 = boto3.client(
            "s3",
            aws_access_key_id=config("s3AccessKey"),
            aws_secret_access_key=config("s3Secret"),
        )
        bucket = config("S3_BUCKET_NAME")
        key = f"product_additions/{file_obj.name}"
        s3.upload_fileobj(file_obj, bucket, key, ExtraArgs={"ACL": "public-read"})
        return f"https://{bucket}.s3.amazonaws.com/{key}"


@method_decorator(name='post', decorator=swagger_auto_schema(tags=['product_additions']))
class CreateProductAdditionView(ProductAdditionBaseView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):

        addon_name = request.data.get("addon_name")
        price = request.data.get("price")
        description = request.data.get("description", "")
        files = request.FILES.getlist("images")

        if not addon_name or not price:
            return Response({
                "status": False,
                "message": "Addon name and price are required.",
                "data": None,
            }, status=status.HTTP_400_BAD_REQUEST)

        allowed_ext = (".png", ".jpg", ".jpeg", ".gif")
        invalid_files = [f.name for f in files if not f.name.lower().endswith(allowed_ext)]
        if invalid_files:
            return Response({
                "status": False,
                "message": f"Invalid file type(s): {', '.join(invalid_files)}. Only images are allowed.",
                "data": None,
            }, status=status.HTTP_400_BAD_REQUEST)

        uploaded_urls = []
        if files:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(self.upload_to_s3, f) for f in files]
                for future in futures:
                    uploaded_urls.append(future.result())

        status_obj = get_status("Active")
        addition = ProductAddition.objects.create(
            addon_name=addon_name.strip(),
            price=price,
            image_urls=uploaded_urls,
            status=status_obj,
        )

        return Response({
            "status": True,
            "message": "Product addition created successfully.",
            "data": ProductAdditionSerializer(addition).data,
        }, status=status.HTTP_201_CREATED)


@method_decorator(name="get", decorator=swagger_auto_schema(tags=["product_additions"]))
class GetAllProductAdditionsView(generics.ListAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProductAdditionSerializer

    def get_queryset(self):
        """Fetch only non-deleted (Active) items"""
        active_status = get_status("Active")
        return ProductAddition.objects.filter(status=active_status).order_by("-created_at")

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": True,
            "message": "product additions fetched successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)


@method_decorator(name="get", decorator=swagger_auto_schema(tags=["product_additions"]))
class GetProductAdditionByIDView(generics.RetrieveAPIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ProductAdditionSerializer
    lookup_field = "id"

    def get_queryset(self):
        """Exclude deleted ones"""
        deleted_status = get_status("Deleted")
        return ProductAddition.objects.exclude(status=deleted_status)

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_queryset().get(id=kwargs["id"])
        except ProductAddition.DoesNotExist:
            return Response({
                "status": False,
                "message": "Product addition not found or has been deleted.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        return Response({
            "status": True,
            "message": "Product addition fetched successfully.",
            "data": serializer.data,
        }, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['product_additions']))
class UpdateProductAdditionView(ProductAdditionBaseView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def put(self, request, id):
        try:
            addition = ProductAddition.objects.get(id=id)
        except ProductAddition.DoesNotExist:
            return Response({
                "status": False,
                "message": "Product addition not found.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)

        addon_name = request.data.get("addon_name", addition.addon_name)
        price = request.data.get("price", addition.price)
        status_name = request.data.get("status")

        status_obj = get_status(status_name) if status_name else addition.status

        files = request.FILES.getlist("images")
        if files:
            allowed_ext = (".png", ".jpg", ".jpeg", ".gif")
            new_urls = []
            for f in files:
                if not f.name.lower().endswith(allowed_ext):
                    return Response({
                        "status": False,
                        "message": f"Invalid file type for {f.name}.",
                        "data": None,
                    }, status=status.HTTP_400_BAD_REQUEST)
                new_urls.append(self.upload_to_s3(f))
            addition.image_urls.extend(new_urls)

        addition.addon_name = addon_name
        addition.price = price
        addition.status = status_obj
        addition.updated_at = timezone.now()
        addition.save()

        return Response({
            "status": True,
            "message": "Product addition updated successfully.",
            "data": ProductAdditionSerializer(addition).data,
        }, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['product_additions']))
class DeleteProductAdditionView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def delete(self, request, id):
        try:
            addition = ProductAddition.objects.get(id=id)
        except ProductAddition.DoesNotExist:
            return Response({
                "status": False,
                "message": "Product addition not found.",
                "data": None,
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_status = get_status("Deleted")
        if addition.status == deleted_status:
            return Response({
                "status": False,
                "message": "Product addition is already deleted.",
                "data": None,
            }, status=status.HTTP_400_BAD_REQUEST)

        addition.status = deleted_status
        addition.updated_at = timezone.now()
        addition.save(update_fields=["status", "updated_at"])

        return Response({
            "status": True,
            "message": "Product addition deleted successfully.",
            "data": None,
        }, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['vendor logout']))
class VendorLogoutAPIView(APIView):
    permission_classes = [IsAuthenticated, IsVendor]
    authentication_classes = [VendorJWTAuthentication]

    def post(self, request):

        # ACCESS TOKEN
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return Response({"error": "Authorization header missing"}, status=400)

        try:
            _, access_token = auth_header.split()
        except:
            return Response({"error": "Invalid Authorization header"}, status=400)

        # BLACKLIST ACCESS TOKEN
        BlacklistedToken.objects.create(
            user=request.user,
            token=access_token
        )

        # REFRESH TOKEN
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=400)

        # Check if refresh token exists
        try:
            stored = RefreshTokenStore.objects.get(refresh_token=refresh_token)
        except RefreshTokenStore.DoesNotExist:
            return Response({"error": "Invalid refresh token"}, status=400)

        # BLACKLIST REFRESH TOKEN
        BlacklistedToken.objects.create(
            user=request.user,
            token=refresh_token
        )

        # Delete stored token
        stored.delete()

        return Response({"message": "Logout Successful"}, status=200)

    
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Generate new access Token']))
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            raise AuthenticationFailed("Refresh token required.")

        # CHECK IF TOKEN IS BLACKLISTED
        if BlacklistedToken.objects.filter(token=refresh_token).exists():
            raise AuthenticationFailed("Refresh token is blacklisted.")

        # Decode refresh token to extract user_id
        try:
            decoded = RefreshToken(refresh_token)
            user_id = decoded["user_id"]
        except Exception:
            raise AuthenticationFailed("Invalid refresh token format.")
        
        try:
            admin_user = AdminUser.objects.get(id=user_id)
        except AdminUser.DoesNotExist:
            raise AuthenticationFailed("Admin User Not Found")

        # CHECK IF USER EXISTS
        try:
            user = Vendor_registration.objects.get(auth_user=admin_user)
        except Vendor_registration.DoesNotExist:
            raise AuthenticationFailed("User not found.")

        # Ensure token matches the LATEST stored refresh token
        stored = RefreshTokenStore.objects.filter(user=admin_user).last()

        if not stored:
            raise AuthenticationFailed("No active refresh token for this user.")

        if stored.refresh_token != refresh_token:
            raise AuthenticationFailed("Old or invalid refresh token.")
        
        # issue NEW access token
        return super().post(request, *args, **kwargs)
    
class VerifyMPINAPIView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = MPINVerifySerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(f"MPIN verification failed. Errors: {serializer.errors}")
            return Response({
                "status": False,
                "message": "Invalid credentials",
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            "status": True,
            "message": "MPIN verified successfully"
        },
        status=status.HTTP_200_OK)
    
class IsVendorRegisteredView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyVendorSerializer(data=request.data)

        if not serializer.is_valid():
            logger.war("Invaid input : %s", serializer.errors)
            return Response({
                "status": False,
                "message": "invalid input",
                "error": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        identifier = serializer.validated_data["identifier"]

        # Detect Email or Phone
        identifier_type = UserIdentifierhelper.detect_type(identifier)

        if identifier_type is None:
            logger.warning("Invalid identifier format: %s", identifier_type)
            return Response({
                "status": False,
                "error": "Invalid email or phone format"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if vendor registered
        is_registered = VerifyIsRegistered.check(identifier)

        if not is_registered:
            logger.warning("Not registred : %s", identifier, identifier_type)
            return Response({
                "status": False,
                "is_registered": False,
                "message": (
                    "You are not registered with this email"
                    if identifier_type == "email"
                    else "You are not registered with this Phone Number"
                )
            }, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "status": True,
            "is_registered": True,
            "message": "You are registered"
        }, status=status.HTTP_200_OK)
    
class AddBankAccountAPIView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            vendor_id = request.data.get("vendor_id")
            if not vendor_id:
                return Response({"status": False, "message": "vendor_id is required"}, status=400)

            try:
                vendor = Vendor_registration.objects.get(id=vendor_id)
            except Vendor_registration.DoesNotExist:
                return Response({"status": False, "message": "Vendor not found"}, status=404)

            data = request.data.copy()
            data["vendor"] = vendor.id
            data["status"] = get_status("Active").id         

            serializer = VendorBankAccountSerializer(data=data)
            if serializer.is_valid():
                serializer.save()

                return Response({
                    "status": True,
                    "message": "Bank account added successfully",
                    "data": serializer.data
                }, status=201)

            return Response({"status": False, "errors": serializer.errors}, status=400)

        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=500)

class GetBankAccountAPIView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, vendor_id):
        accounts = VendorBankAccount.objects.filter(
            vendor_id=vendor_id,
            status=get_status("Active")  
        )

        if not accounts.exists():
            return Response({"status": False, "message": "No bank account found"}, status=404)

        serializer = VendorBankAccountSerializer(accounts, many=True)
        return Response({"status": True, "data": serializer.data}, status=200)


class UpdateBankAccountAPIView(APIView):
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            account = VendorBankAccount.objects.get(pk=pk)
        except VendorBankAccount.DoesNotExist:
            return Response({"status": False, "message": "Bank account not found"}, status=404)

        serializer = VendorBankAccountSerializer(account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": True,
                "message": "Bank account updated successfully",
                "data": serializer.data
            }, status=200)

        return Response({"status": False, "errors": serializer.errors}, status=400)


class DeleteBankAccountAPIView(APIView):
    authentication_classes = [VendorJWTAuthentication]        
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            account = VendorBankAccount.objects.get(id=pk)
        except VendorBankAccount.DoesNotExist:
            return Response({
                "status": False,
                "message": "Bank account not found.",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)

        deleted_status = get_status("Deleted")

        if account.status == deleted_status:
            return Response({
                "status": False,
                "message": "Bank account is already deleted.",
                "data": None
            }, status=status.HTTP_400_BAD_REQUEST)

        account.status = deleted_status
        account.updated_at = timezone.now()
        account.save(update_fields=["status", "updated_at"])

        return Response({
            "status": True,
            "message": "Bank account deleted successfully.",
            "data": None
        }, status=status.HTTP_200_OK)

class FeedbackPagination(PageNumberPagination):
    page_size = 20  
    page_size_query_param = 'page_size'  
    max_page_size = 100


class AddVendorFeedback(APIView):
    def post(self, request):
        serializer = VendorFeedbackSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Feedback submitted successfully!", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetVendorFeedback(APIView):
    def get(self, request, vendor_id):
        feedbacks = VendorFeedback.objects.filter(
            vendor_id=vendor_id, is_visible=True
        ).order_by("-id")

        paginator = FeedbackPagination()
        paginated_feedback = paginator.paginate_queryset(feedbacks, request)

        serializer = VendorFeedbackSerializer(paginated_feedback, many=True)

        return paginator.get_paginated_response({
            "vendor_id": vendor_id,
            "feedbacks": serializer.data
        })


class AddFeedbackReply(APIView):
    def post(self, request, feedback_id):
        try:
            feedback = VendorFeedback.objects.get(id=feedback_id)
        except VendorFeedback.DoesNotExist:
            return Response({"error": "Feedback not found"}, status=status.HTTP_404_NOT_FOUND)

        if request.data.get("reply_by") == "VENDOR":
            vendor_id_from_request = request.data.get("vendor_id")
            if str(feedback.vendor_id) != str(vendor_id_from_request):
                return Response(
                    {"error": "Permission denied: You cannot reply to feedback of another vendor."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = VendorFeedbackReplySerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(feedback=feedback)
            return Response(
                {"message": "Reply posted successfully!", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class OrderListAPIView(generics.ListAPIView):
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter
    permission_classes = [IsAuthenticated, IsVendor]
    pagination_class = FeedbackPagination

    def get_queryset(self):
        token = self.request.auth
        if not token:
            raise NotFound("Token missing")

        vendor_id = token.get("user_id")

        if not vendor_id:
            raise NotFound("vendor_id is missing")

        return Order.objects.filter(vendor_id=vendor_id).order_by("id")

    def list(self, request, *args, **kwargs):

        valid_fields = ["order_status", "page", "page_size"]
        for key in request.query_params.keys():
            if key not in valid_fields:

                return Response({
                    "success": False,
                    "message": f"Invalid filter parameter '{key}'"
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            queryset = self.get_queryset()

            # Summary
            total_count = queryset.count()
            completed_count = queryset.filter(order_status=OrderStatus.COMPLETED).count()
            cancelled_count = queryset.filter(order_status=OrderStatus.CANCELLED).count()

            # Filter logic
            order_status_param = request.query_params.get("order_status")
            filter_applied = False

            if order_status_param is not None:
                try:
                    order_status_param = int(order_status_param)
                except:
                    return Response({
                        "success": False,
                        "message": "order_status must be an integer"
                    }, status=status.HTTP_400_BAD_REQUEST)

                valid_status_ids = [choice[0] for choice in OrderStatus.CHOICES]
                if order_status_param not in valid_status_ids:
                    return Response({
                        "success": False,
                        "message": f"Invalid order_status ID '{order_status_param}'"
                    }, status=status.HTTP_400_BAD_REQUEST)

                queryset = queryset.filter(order_status=order_status_param)
                filter_applied = True

            # APPLY PAGINATION
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response({
                "success": True,
                "message": "Order list fetched successfully",
                "filter_applied": filter_applied,
                "total_count_before_filter": total_count,
                "filtered_count": queryset.count(),
                "completed_orders": completed_count,
                "cancelled_orders": cancelled_count,
                "data": serializer.data
            })

        except Exception as e:
            logger.error(f"OrderListAPIView Error: {str(e)}", exc_info=True)
            return Response({
                "success": False,
                "message": "Something went wrong while fetching orders",
                "details": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrderListByIdView(generics.RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderListByIdSerializer
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated, IsVendor]
    lookup_field = 'id'

    def get_object(self):
        user = self.request.user
        order_id = self.kwargs.get("id")
        
        try:
            order = Order.objects.get(id=order_id)

            if order.vendor_id != user.id:
                logger.warning(f"[OrderDetails] Vendor {user.id} tried to access order {order_id}")
                raise PermissionDenied("This order does ot belongs to you")
        
            return order
    
        except Order.DoesNotExist:
            logger.error(f"[orderDetails] order {order_id} does not exist")
            raise NotFound("order not found")
        
    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()
        seriailizer = self.get_serializer(order)

        return Response({
            "status": True,
            "message": "Order details fetched successfully.",
            "data": seriailizer.data
        },
        status=status.HTTP_200_OK)

class updateOrderStatusAPIView(generics.UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = UpdateOrderStatusSerializer
    authentication_classes = [VendorJWTAuthentication]
    permission_classes = [IsAuthenticated, IsVendor]
    lookup_field = 'id'

    def get_object(self):
        user = self.request.user
        order_id = self.kwargs.get("id")

        try:
            order = Order.objects.get(id=order_id)

            if order.vendor_id != user.id:
                logger.error("[updateOrderStatus] User authentication failed")
                raise AuthenticationFailed("This order does not belongs to you.")
        
            return order

        except Order.DoesNotExist:
            logger.exception(f"[updateOrderStatus] error updating order #{order_id}")
            raise NotFound("order not found")
        
    def update(self, request, *args, **kwargs):
        order_id = self.kwargs.get("id")

        try:
            response = super().update(request, *args, **kwargs)

            return Response({
                "status": True,
                "message": "status updated successfully.",
                "order_id": order_id,
                "data": response.data
            },
            status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"[updateOrderDetails] error updating order #{order_id}: {str(e)}")
            raise

class VendorContactUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        vendor = request.user 

        serializer = VendorContactUpdateSerializer(
            vendor,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Contact Information Updated Successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreateBestDealBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def post(self, request):
        try:
            title = request.data.get("title")
            image = request.FILES.get("image")

            if not title or not image:
                return Response({"error": "Title & image are required"}, status=status.HTTP_400_BAD_REQUEST)

            # S3 setup
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret")
            )
            bucket = config("S3_BUCKET_NAME")

            ext = os.path.splitext(image.name)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            key = f"best_deal_banners/{unique_name}"

            # Upload to S3
            s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})
            image_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            banner = BestDealBanner.objects.create(
                title=title,
                image=image_url
            )

            return Response({
                "message": "Best Deal banner created successfully",
                "banner": BestDealBannerSerializer(banner).data
            }, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

class GetAllBestDealBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request):
        banners = BestDealBanner.objects.all().order_by('-id')
        serializer = BestDealBannerSerializer(banners, many=True)
        return Response({"banners": serializer.data}, status=200)

class GetBestDealBannerByIdAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request, id):
        try:
            banner = BestDealBanner.objects.get(id=id)
            return Response({"banner": BestDealBannerSerializer(banner).data}, status=200)
        except BestDealBanner.DoesNotExist:
            return Response({"error": "Banner not found"}, status=404)

class UpdateBestDealBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def put(self, request, id):
        try:
            banner = BestDealBanner.objects.get(id=id)

            title = request.data.get("title", banner.title)
            image = request.FILES.get("image")

            banner.title = title

            # If new image provided, upload again to S3
            if image:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret")
                )
                bucket = config("S3_BUCKET_NAME")

                ext = os.path.splitext(image.name)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                key = f"best_deal_banners/{unique_name}"

                s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})
                banner.image = f"https://{bucket}.s3.amazonaws.com/{key}"

            banner.save()
            return Response({"message": "Updated", "banner": BestDealBannerSerializer(banner).data}, status=200)

        except BestDealBanner.DoesNotExist:
            return Response({"error": "Banner not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class DeleteBestDealBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def delete(self, request, id):
        try:
            banner = BestDealBanner.objects.get(id=id)
            banner.delete()
            return Response({"message": "Banner deleted successfully"}, status=200)
        except BestDealBanner.DoesNotExist:
            return Response({"error": "Banner not found"}, status=404)

class GetVendorBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request):
        try:
            vendor = request.user  # current logged-in vendor

            # Latest Celebrity Banner
            celebrity = CelebrityBanner.objects.order_by('-id').first()
            celebrity_url = celebrity.image if celebrity else None

            # Latest Best Deal Banner
            best_deal = BestDealBanner.objects.order_by('-id').first()
            best_deal_url = best_deal.image if best_deal else None

            response_data = {
                "business_name": vendor.business_name,
                "celebrity_banner": celebrity_url,
                "best_deal_banner": best_deal_url
            }

            return Response({
                "status": True,
                "message": "Base API Data fetched successfully",
                "data": response_data
            }, status=200)

        except Exception as e:
            return Response({
                "status": False,
                "message": "Something went wrong",
                "error": str(e)
            }, status=500)
        
class VendorLocationUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    # authentication_classes = [VendorJWTAuthentication]  # uncomment if you use custom JWT auth

    def put(self, request, *args, **kwargs):
        """
        Replace vendor location fields.
        """
        serializer = VendorLocationUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": False,
                "message": "Validation failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        vendor = request.user  # assume request.user is Vendor_registration instance

        # safe update in transaction
        try:
            with transaction.atomic():
                vendor.state_id = validated['state_obj']
                vendor.city_id = validated['city_obj']
                vendor.pincode = validated.get('pincode') or vendor.pincode
                vendor.address = validated.get('address') or vendor.address
                if 'latitude' in validated:
                    vendor.latitude = validated.get('latitude')
                if 'longitude' in validated:
                    vendor.longitude = validated.get('longitude')

                # Set profile_status to pending for re-approval after location change
                vendor.profile_status = 'PENDING'
                # updated_by — prefer user email or contact_no
                vendor.updated_by = getattr(request.user, 'email', None) or getattr(request.user, 'contact_no', None)

                vendor.save(update_fields=[
                    'state_id', 'city_id', 'pincode', 'address', 'latitude', 'longitude',
                    'profile_status', 'updated_by', 'updated_at'
                ])
        except Exception as e:
            return Response({
                "status": False,
                "message": "Failed to update location.",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # reuse existing representation
        vendor_data = VendorSignupSerializer(vendor).data

        return Response({
            "status": True,
            "message": "Location updated successfully. Changes sent for approval.",
            "data": vendor_data
        }, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        # Allow partial updates via PATCH as well.
        return self.put(request, *args, **kwargs)

class VendorDocumentListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def get(self, request):
        vendor = request.user
        phone = vendor.contact_no

        docs = VendorDocument.objects.filter(
            vendor_business_no=phone,
            status__in=["PERMANENT"]
        )

        serializer = VendorDocumentSerializer(docs, many=True)
        return Response({
            "status": True,
            "documents": serializer.data
        }, status=status.HTTP_200_OK)

class VendorDocumentUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def put(self, request, doc_id):
        try:
            vendor = request.user
            phone = vendor.contact_no

            try:
                document = VendorDocument.objects.get(
                    id=doc_id,
                    vendor_business_no=phone,
                    status="PERMANENT"
                )
            except VendorDocument.DoesNotExist:
                return Response({"error": "Document not found or not owned by you"}, status=404)

            serializer = VendorDocumentUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            new_file = request.FILES.get("file")
            new_doc_type = serializer.validated_data.get("document_type")
            company_type_id = serializer.validated_data.get("company_type")

            # -------- Update company type --------
            if company_type_id:
                try:
                    company_type_obj = CompanyTypeMaster.objects.get(id=company_type_id)
                    document.company_type = company_type_obj
                except CompanyTypeMaster.DoesNotExist:
                    return Response({"error": "Invalid company_type id"}, status=400)

            # -------- Update document type --------
            if new_doc_type:
                document.document_type = new_doc_type

            # -------- Replace document file S3 --------
            if new_file:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret"),
                )

                bucket = config("S3_BUCKET_NAME")

                file_ext = os.path.splitext(new_file.name)[1]
                unique_name = f"{uuid.uuid4().hex}{file_ext}"
                key = f"vendor_documents/{phone}/{unique_name}"

                s3.upload_fileobj(new_file, bucket, key, ExtraArgs={"ACL": "public-read"})
                new_url = f"https://{bucket}.s3.amazonaws.com/{key}"

                # Update document URL
                document.document_url = new_url

            document.save()

            # --- UPDATE vendor_registration.document_id ----
            valid_docs = VendorDocument.objects.filter(
                vendor_business_no=phone,
                status="PERMANENT"
            ).values_list("id", flat=True)

            vendor.document_id = list(valid_docs)
            vendor.save(update_fields=["document_id"])

            return Response({
                "status": True,
                "message": "Document updated successfully",
                "document": VendorDocumentSerializer(document).data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)

class VendorDocumentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [VendorJWTAuthentication]

    def delete(self, request, doc_id):
        vendor = request.user
        phone = vendor.contact_no

        try:
            document = VendorDocument.objects.get(
                id=doc_id,
                vendor_business_no=phone,
                status="PERMANENT"
            )
        except VendorDocument.DoesNotExist:
            return Response({"error": "Document not found"}, status=404)

        # Mark deleted
        document.status = "DELETED"
        document.save()

        # Update vendor document list
        valid_docs = VendorDocument.objects.filter(
            vendor_business_no=phone,
            status="PERMANENT"
        ).values_list("id", flat=True)

        vendor.document_id = list(valid_docs)
        vendor.save(update_fields=["document_id"])

        return Response({
            "status": True,
            "message": "Document deleted successfully"
        })

class CakeMasterDataAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request):

        cake = CakeOptions.objects.first()
        delivery = DeliveryOptions.objects.first()

        cake_data = CakeOptionsSerializer(cake).data if cake else {}
        delivery_data = DeliveryOptionsSerializer(delivery).data if delivery else {}

        return Response({
            "cake_options": cake_data,
            "delivery_options": delivery_data
        })
    
class CreateCelebrityBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]  
    def post(self, request):
        try:
            title = request.data.get("title")
            image = request.FILES.get("image")

            if not title or not image:
                return Response({"error": "Title & image are required"}, status=status.HTTP_400_BAD_REQUEST)

            # S3 config
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret")
            )
            bucket = config("S3_BUCKET_NAME")

            # Unique filename
            ext = os.path.splitext(image.name)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            key = f"celebrity_banners/{unique_name}"

            # Upload
            s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})
            image_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            # Save in DB
            banner = CelebrityBanner.objects.create(title=title, image=image_url)

            return Response({
                "message": "Banner created successfully",
                "banner": CelebrityBannerSerializer(banner).data
            }, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
class UpdateCelebrityBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]  

    def put(self, request, pk):
        try:
            try:
                banner = CelebrityBanner.objects.get(id=pk)
            except CelebrityBanner.DoesNotExist:
                return Response({"error": "Banner not found"}, status=404)

            title = request.data.get("title")
            new_image = request.FILES.get("image")

            if title:
                banner.title = title

            bucket = config("S3_BUCKET_NAME")

            # If new image uploaded
            if new_image:
                # delete old
                try:
                    old_key = banner.image.split(f"https://{bucket}.s3.amazonaws.com/")[1]
                    s3 = boto3.client(
                        "s3",
                        aws_access_key_id=config("s3AccessKey"),
                        aws_secret_access_key=config("s3Secret")
                    )
                    s3.delete_object(Bucket=bucket, Key=old_key)
                except:
                    pass  # ignore delete errors

                # upload new
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret")
                )
                ext = os.path.splitext(new_image.name)[1]
                unique_name = f"{uuid.uuid4().hex}{ext}"
                new_key = f"celebrity_banners/{unique_name}"

                s3.upload_fileobj(new_image, bucket, new_key, ExtraArgs={"ACL": "public-read"})
                new_url = f"https://{bucket}.s3.amazonaws.com/{new_key}"

                banner.image = new_url

            banner.save()

            return Response({
                "message": "Banner updated successfully",
                "banner": CelebrityBannerSerializer(banner).data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=500)
class DeleteCelebrityBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]  

    def delete(self, request, pk):
        try:
            try:
                banner = CelebrityBanner.objects.get(id=pk)
            except CelebrityBanner.DoesNotExist:
                return Response({"error": "Banner not found"}, status=404)

            bucket = config("S3_BUCKET_NAME")

            # Delete S3 image
            try:
                key = banner.image.split(f"https://{bucket}.s3.amazonaws.com/")[1]
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret")
                )
                s3.delete_object(Bucket=bucket, Key=key)
            except:
                pass

            banner.delete()

            return Response({"message": "Banner deleted successfully"})

        except Exception as e:
            return Response({"error": str(e)}, status=500)
class GetAllCelebrityBannerAPIView(APIView):
    permission_classes = ()
    authentication_classes = [VendorJWTAuthentication]  

    def get(self, request):
        try:
            banners = CelebrityBanner.objects.all().order_by("-id")
            serializer = CelebrityBannerSerializer(banners, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        