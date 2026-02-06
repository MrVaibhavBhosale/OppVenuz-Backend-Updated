from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, status
from admin_master.models import (
    CompanyTypeMaster, 
    StatusMaster, 
    App_version, 
    State_master, 
    City_master, 
    CelebrityProfession, 
    TentativeBudget, 
    PreferredEventType, 
    Terms_and_condition_master, 
    OnboardingScreens,
    Language,

)
from admin_master.serializers import (
    AppVersionSerializer, 
    StateSerializer, 
    TermsConditionSerializer, 
    OnboardingScreenSerializer,

)
from .utils import (
    calculate_file_hash, 
    upload_to_s3, 
    generate_numeric_otp, 
    mask_email, 
    mask_phone, 
    send_otp_email, 
    send_otp_sms

)
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from .models import (
    EmailVerification, 
    PhoneVerification,
    CelebrityMedia, 
    CelebrityDocument,
    CelebrityRegistration,
    RefreshTokenStore, 
    BlacklistedToken

)
from .serializers import (
    RequestEmailOTPSerializer,
    RequestPhoneOTPSerializer,
    VerifyEmailOTPSerializer,
    VerifyPhoneOTPSerializer,
    CelebritySignupSerializer,
    CelebrityMediaSerializer,
    CelebrityDocumentSerializer,
    CelebrityLoginSerializer,
    CelebrityLogoutSerializer,

)
from .authentication import CelebrityJWTAuthentication
import logging
logger = logging.getLogger("django")
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response


from oauth2_provider.contrib.rest_framework import OAuth2Authentication
import boto3
import uuid
import os
from decouple import config
from oauth2_provider.contrib.rest_framework.authentication import OAuth2Authentication
from drf_yasg import openapi
from jwt_utils import create_jwt
from rest_framework.generics import GenericAPIView
from celebrity.authentication import CelebrityJWTAuthentication
from django.db import IntegrityError
class CelebrityMediaUploadAPIView(APIView):

    permission_classes = (AllowAny,)
    authentication_classes = (JWTAuthentication, OAuth2Authentication)

    MAX_IMAGE_COUNT = 5
    MAX_VIDEO_COUNT = 2
    MAX_IMAGE_SIZE = 5 * 1024 * 1024      # 5 MB
    MAX_VIDEO_SIZE = 40 * 1024 * 1024     # 40 MB

    def post(self, request):
        try:
            phone = request.data.get("celebrity_business_no")
            media_type = request.data.get("media_type")  # IMAGE / VIDEO
            files = request.FILES.getlist("files")

            if not phone or not media_type or not files:
                return Response(
                    {"status": False, "message": "Missing required fields"},
                    status=400
                )

            if media_type not in ["IMAGE", "VIDEO"]:
                return Response(
                    {"status": False, "message": "Invalid media_type"},
                    status=400
                )

            verification = PhoneVerification.objects.filter(
                phone=phone,
                is_verified=True
            ).first()

            if not verification:
                return Response(
                    {"status": False, "message": "Phone not verified"},
                    status=400
                )

            # TEMP media count only
            existing_images = CelebrityMedia.objects.filter(
                verification=verification,
                media_type="IMAGE",
                status="TEMP"
            ).count()

            existing_videos = CelebrityMedia.objects.filter(
                verification=verification,
                media_type="VIDEO",
                status="TEMP"
            ).count()

            if media_type == "IMAGE" and existing_images + len(files) > self.MAX_IMAGE_COUNT:
                return Response(
                    {"status": False, "message": "Maximum 5 images allowed"},
                    status=400
                )

            if media_type == "VIDEO" and existing_videos + len(files) > self.MAX_VIDEO_COUNT:
                return Response(
                    {"status": False, "message": "Maximum 2 videos allowed"},
                    status=400
                )

            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret"),
            )
            bucket = config("S3_BUCKET_NAME")

            uploaded_media = []

            for file in files:

                if media_type == "IMAGE" and file.size > self.MAX_IMAGE_SIZE:
                    return Response(
                        {"status": False, "message": "Image size must be ≤ 5MB"},
                        status=400
                    )

                if media_type == "VIDEO" and file.size > self.MAX_VIDEO_SIZE:
                    return Response(
                        {"status": False, "message": "Video size must be ≤ 40MB"},
                        status=400
                    )

                ext = os.path.splitext(file.name)[1].lower()

                if media_type == "IMAGE" and ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                    return Response(
                        {"status": False, "message": "Invalid image format"},
                        status=400
                    )

                if media_type == "VIDEO" and ext not in [".mp4"]:
                    return Response(
                        {"status": False, "message": "Invalid video format"},
                        status=400
                    )

                key = f"celebrity_media/{phone}/{uuid.uuid4().hex}{ext}"

                s3.upload_fileobj(
                    file,
                    bucket,
                    key,
                    ExtraArgs={"ACL": "public-read"}
                )

                media_url = f"https://{bucket}.s3.amazonaws.com/{key}"

                media = CelebrityMedia.objects.create(
                    verification=verification,
                    media_type=media_type,
                    media_url=media_url,
                    status="TEMP"
                )

                uploaded_media.append(media)

            serializer = CelebrityMediaSerializer(uploaded_media, many=True)

            return Response({
                "status": True,
                "message": f"{media_type} uploaded successfully",
                "data": serializer.data
            }, status=201)

        except Exception as e:
            return Response(
                {"status": False, "error": str(e)},
                status=500
            )


class CelebrityDocumentUploadAPIView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ( JWTAuthentication,OAuth2Authentication)

    def post(self, request, *args, **kwargs):
        try:
            phone = request.data.get("celebrity_business_no")
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
            CelebrityDocument.objects.filter(status='TEMP', expires_at__lt=now).update(status='DELETED')

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
            key = f"celebrity_documents/{phone}/{unique_name}"

            s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})
            document_url = f"https://{bucket}.s3.amazonaws.com/{key}"

            # Step 5: Save in DB
            doc = CelebrityDocument.objects.create(
                verification=verification,
                company_type=company_type_obj,
                document_type=document_type,
                document_url=document_url,
                status="TEMP",
                celebrity_business_no=phone,
                expires_at=timezone.now() + timedelta(hours=1),
            )

            serializer = CelebrityDocumentSerializer(doc)
            return Response({
                "message": f"{document_type} uploaded successfully.",
                "document": serializer.data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(name='post', decorator=swagger_auto_schema(tags=['sendEmail- otp']))
class RequestEmailOTPView(APIView):
    permission_classes = []

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
            "Phone": masked_phone,
            "is_phone_verified": verified,
        }, status=status.HTTP_200_OK)
    

class CelebrityBaseAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            app_version = AppVersionSerializer(
                App_version.objects.filter(status=1),
                many=True
            ).data

            states = StateSerializer(
                State_master.objects.filter(status=1),
                many=True
            ).data

            for state in states:
                state["cities"] = list(
                    City_master.objects.filter(
                        state_id=state["id"],
                        status=1
                    ).values("id", "city_name", "latitude", "longitude")
                )

            professions = CelebrityProfession.objects.filter(
                is_active=True
            ).values("id", "name")

            # location_preferences = LocationPreferenceMaster.objects.filter(
            #     status__status_type="Active"
            # ).values("id", "name", "code")

            tentative_budget = TentativeBudget.objects.filter(
                is_active=True
            ).values("id", "label", "min_amount", "max_amount")

            preferred_event_type = PreferredEventType.objects.filter(
                status=1
            ).values("id", "name")

            languages = Language.objects.filter(
                status__status_type="Active"
            ).values("id", "language_name")

            terms_conditions = TermsConditionSerializer(
                Terms_and_condition_master.objects.filter(
                    status__status_type="Active"
                ),
                many=True
            ).data

            gif = OnboardingScreens.objects.filter(
                status=1, type=1
            ).first()

            flash = OnboardingScreens.objects.filter(
                status=1, type=2
            ).order_by("order")

            return Response({
                "status": True,
                "data": {
                    "app_version": app_version,
                    "states": states,
                    "profession": list(professions),
                    # "location_preferences": list(location_preferences),
                    "tentative_budget": list(tentative_budget),
                    "preferred_event_type": list(preferred_event_type),
                    "languages": list(languages),
                    "terms_and_conditions": terms_conditions,
                    "onboarding": {
                        "gif": OnboardingScreenSerializer(gif).data if gif else None,
                        "flash_screens": OnboardingScreenSerializer(flash, many=True).data
                    }
                }
            })

        except Exception as e:
            logger.error(e)
            return Response({
                "status": False,
                "message": "Base API failed",
                "error": str(e)
            }, status=500)

class CelebritySignupView(APIView):
    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):

        # ---------------- VALIDATE REGISTRATION DATA ----------------
        serializer = CelebritySignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "status": False,
                "errors": serializer.errors
            }, status=400)

        contact_no = serializer.validated_data.get("contact_no")

        # ---------------- VERIFY PHONE ----------------
        verification = PhoneVerification.objects.filter(
            phone=contact_no,
            is_verified=True
        ).first()

        if not verification:
            return Response({
                "status": False,
                "message": "Phone not verified"
            }, status=400)

        # ============================================================
        # ================= DOCUMENT MATCH (VENDOR STYLE) ============
        # ============================================================

        contact_persons = request.data.get("contact_persons", [])
        matched_doc_ids = []

        for person in contact_persons:
            person_contact_no = person.get("contact_no")
            documents = person.get("documents", [])

            if not person_contact_no:
                continue

            uploaded_docs = CelebrityDocument.objects.filter(
                celebrity_business_no=person_contact_no,
                status="TEMP"
            )

            for doc in documents:
                doc_type = doc.get("document_type", "").strip()
                doc_url = doc.get("document_url", "").split("?")[0]

                if not doc_type or not doc_url:
                    continue

                qs = uploaded_docs.filter(
                    document_type__iexact=doc_type,
                    document_url__iexact=doc_url
                )

                if qs.exists():
                    matched_doc_ids.extend(
                        qs.values_list("id", flat=True)
                    )

        matched_doc_ids = list(set(matched_doc_ids))

        if not matched_doc_ids:
            return Response({
                "status": False,
                "message": "No valid document matched"
            }, status=400)

        # TEMP → VERIFIED
        CelebrityDocument.objects.filter(
            id__in=matched_doc_ids
        ).update(status="VERIFIED")

        # ============================================================
        # ================= MEDIA MATCH (VENDOR STYLE) ===============
        # ============================================================

        media_data = request.data.get("media", [])
        matched_media_ids = []

        uploaded_media = CelebrityMedia.objects.filter(
            verification=verification,
            status="TEMP"
        )

        for media in media_data:
            media_type = media.get("media_type", "").strip()
            media_url = media.get("media_url", "").split("?")[0]

            if not media_type or not media_url:
                continue

            qs = uploaded_media.filter(
                media_type__iexact=media_type,
                media_url__iexact=media_url
            )

            if qs.exists():
                matched_media_ids.extend(
                    qs.values_list("id", flat=True)
                )

        matched_media_ids = list(set(matched_media_ids))
        if not matched_media_ids:
            return Response({
                "status": False,
                "message": "No valid media matched"
            }, status=400)

        # TEMP → ACTIVE
        CelebrityMedia.objects.filter(
            id__in=matched_media_ids
        ).update(status="ACTIVE")

        # ============================================================
        # ================= CREATE CELEBRITY =========================
        # ============================================================

        celebrity = serializer.save(
            profile_status="PENDING",
            is_active=True
        )

        return Response({
            "status": True,
            "message": "Celebrity registered successfully",
            "celebrity_id": celebrity.id
        }, status=201)


class CelebrityLoginAPIView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = CelebrityLoginSerializer  

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # -------- TOKENS --------
        access = create_jwt({
            "user_id": user.id,
            "token_type": "access"
        })

        refresh = create_jwt({
            "user_id": user.id,
            "token_type": "refresh"
        })

        # -------- SINGLE SESSION --------
        RefreshTokenStore.objects.filter(user_id=user).delete()
        RefreshTokenStore.objects.create(
            user_id=user,
            refresh_token=refresh,
            token=access
        )

        return Response({
            "status": True,
            "message": "Login successful",
            "data": {
                "id": user.id,
                "email": user.email,
                "mobile_no": user.contact_no,
                "access": access,
                "refresh": refresh
            }
        }, status=status.HTTP_200_OK)

class CelebrityLogoutView(GenericAPIView):
    authentication_classes = [CelebrityJWTAuthentication]
    serializer_class = CelebrityLogoutSerializer  

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"status": False,"error": "Refresh token missing"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Delete refresh token
        deleted, _ = RefreshTokenStore.objects.filter(
            user_id=request.user,
            refresh_token=refresh
        ).delete()

        if deleted == 0:
            return Response(
                {"status": False,"error": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Blacklist access token
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.strip()

            if token.lower().startswith("bearer "):
                token = token.split(" ", 1)[1].strip()

            try:
                BlacklistedToken.objects.get_or_create(
                    user_id=request.user,
                    token=token
                )
            except IntegrityError as e:
                return Response(
                    {"status": False,"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(
            {"status": True, "message": "Logout successful"},
            status=status.HTTP_200_OK
        )