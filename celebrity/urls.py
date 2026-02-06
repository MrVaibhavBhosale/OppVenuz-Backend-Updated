from django.urls import path
from .views import (
    CelebrityMediaUploadAPIView,
    CelebrityDocumentUploadAPIView,
    RequestEmailOTPView,
    RequestPhoneOTPView,
    VerifyEmailOTPView,
    VerifyPhoneOTPView,
    CelebrityBaseAPIView,
    CelebritySignupView,
    CelebrityLoginAPIView,
    CelebrityLogoutView
)

urlpatterns = [
    path("uploadMedia/", CelebrityMediaUploadAPIView.as_view(), name="upload-media"),
    path("uploadDocuments/", CelebrityDocumentUploadAPIView.as_view(), name="upload-documents"),

    path("sendEmailOtp/", RequestEmailOTPView.as_view(), name="send-email-otp"),
    path("sendPhoneOtp/", RequestPhoneOTPView.as_view(), name="send-phone-otp"),
    path("verifyEmailOtp/", VerifyEmailOTPView.as_view(), name="verify-email-otp"),
    path("verifyPhoneOtp/", VerifyPhoneOTPView.as_view(), name="verify-phone-otp"),

    path("baseApi/", CelebrityBaseAPIView.as_view(), name="celebrity-base-info"),
    path("signup/", CelebritySignupView.as_view(), name="celebrity-signup"),

    path('login/', CelebrityLoginAPIView.as_view(), name="login"),
    path('logout/', CelebrityLogoutView.as_view(), name="logout"),
]