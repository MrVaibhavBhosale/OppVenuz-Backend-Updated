from django.db import models, transaction
from django.contrib.postgres.fields import ArrayField 
from django.utils import timezone
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from admin_master.models import (
    Service_master,
    State_master,
    City_master, 
    Best_suited_for,
    CompanyTypeMaster,
    StatusMaster,
    AdminUser,
    CelebrityProfession,
    PreferredEventType,
    Language,
)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password

class CelebrityMedia(models.Model):

    MEDIA_TYPE_CHOICES = (
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    )

    STATUS_CHOICES = (
        ('TEMP', 'Temporary'),
        ('ACTIVE', 'Active'),
        ('DELETED', 'Deleted'),
    )

    id = models.AutoField(primary_key=True)

    verification = models.ForeignKey(
        'PhoneVerification',
        on_delete=models.CASCADE,
        related_name='celebrity_media'
    )

    media_type = models.CharField(
        max_length=10,
        choices=MEDIA_TYPE_CHOICES
    )

    media_url = models.URLField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='TEMP'
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.verification.phone} - {self.media_type}"


class CelebrityDocument(models.Model):
    STATUS_CHOICES = [
        ('TEMP', 'Temporary'),
        ('VERIFIED', 'Verified'),
        ('DELETED', 'Deleted'),
    ]

    id = models.AutoField(primary_key=True)
    verification = models.ForeignKey(
        "PhoneVerification",
        on_delete=models.CASCADE,
        related_name="documents",
        null=True,
        blank=True,
    )

    company_type = models.ForeignKey(
        'admin_master.CompanyTypeMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    document_type = models.CharField(max_length=100)
    document_url = models.URLField(default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='TEMP')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    celebrity_business_no = models.CharField(max_length=20, default="")    
    def default_expiry():
        return timezone.now() + timedelta(hours=1)
    expires_at = models.DateTimeField(default=default_expiry)
    def __str__(self):
        phone = self.verification.phone if self.verification else "NoPhone"
        return f"{phone} - {self.document_type}"


class AbstractVerification(models.Model):
    otp = models.CharField(max_length=128, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_expired_at = models.DateTimeField(null=True, blank=True)
    attempts = models.IntegerField(default=0)
    is_blocked_until = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    MAX_ATTEMPTS = 5
    OTP_TTL_SECONDS = 600       
    BLOCK_SECONDS = 3600       

    class Meta:
        abstract = True

    # ========= OTP LOGIC =========

    def set_otp(self, raw_otp):
        """Save a new hashed OTP and reset block/attempt counters"""
        now = timezone.now()
        self.otp = make_password(raw_otp)
        self.otp_created_at = now
        self.otp_expired_at = now + timedelta(seconds=self.OTP_TTL_SECONDS)
        self.attempts = 0
        self.is_blocked_until = None
        self.save(update_fields=[
            'otp', 'otp_created_at', 'otp_expired_at',
            'attempts', 'is_blocked_until', 'is_verified'
        ])

    def check_otp(self, raw_otp):
        """Validate OTP correctness and expiry"""
        now = timezone.now()

        if not self.otp or not self.otp_expired_at:
            return False

        if now > self.otp_expired_at:
            return False

        try:
            return check_password(str(raw_otp), self.otp)
        except (TypeError, ValueError):
            return False

    def _is_blocked(self):
        """Return remaining block seconds if still blocked, else False"""
        if self.is_blocked_until and timezone.now() < self.is_blocked_until:
            remaining = (self.is_blocked_until - timezone.now()).seconds
            return remaining
        return False

    def mark_attempt(self):
        """Track OTP verification attempts"""
        self.attempts += 1
        if self.attempts >= self.MAX_ATTEMPTS:
            self.is_blocked_until = timezone.now() + timedelta(seconds=self.BLOCK_SECONDS)
            self.attempts = 0
        self.save(update_fields=['attempts', 'is_blocked_until'])

    def can_request_new_otp(self, cooldown_seconds=60):
        """Prevent users from spamming OTP requests"""
        now = timezone.now()
        if self.otp_created_at:
            return (now - self.otp_created_at).total_seconds() > cooldown_seconds
        return True

    def mark_verified(self):
        """Mark OTP as successfully verified"""
        self.is_verified = True
        self.save(update_fields=['is_verified'])
        return True
    

class EmailVerification(AbstractVerification):
    email = models.EmailField(max_length=255,unique=True, blank=True, null=True)

    def __str__(self):
        return self.email or "Email Verification"
        
class PhoneVerification(AbstractVerification):
    phone = models.CharField(max_length=12, unique=True, null=True, blank=True)

    def __str__(self):
        return self.phone or "Phone Verification"
    

class CelebrityRegistration(models.Model):

    # Auth / Contact
    email = models.EmailField(null=True, blank=True, unique=True)
    contact_no = models.CharField(max_length=12, unique=True)
    whatsapp_no = models.CharField(max_length=12, null=True, blank=True)
    mpin = models.CharField(max_length=255, editable=False)

    # Basic Details
    display_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=20)

    profession = models.ForeignKey(
        'admin_master.CelebrityProfession',
        on_delete=models.PROTECT
    )

    is_pan_india = models.BooleanField(default=False)
    is_out_of_india = models.BooleanField(default=False)

    state = models.ForeignKey(
        'admin_master.State_master',
        on_delete=models.PROTECT
    )

    city = models.ForeignKey(
        'admin_master.City_master',
        on_delete=models.PROTECT
    )

    # Description & Story
    description = models.TextField()
    story = models.TextField()

    # Social Media Links
    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    twitter_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)

    # Languages (IDs from Base API)
    language_ids = ArrayField(
        models.IntegerField(),
        default=list,
        blank=True
    )

    # Event Preferences
    tentative_budget = models.ForeignKey(
        'admin_master.TentativeBudget',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    preferred_event_type = models.ForeignKey(
        'admin_master.PreferredEventType',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )

    # Bank Details
    bank_account_name = models.CharField(max_length=150)
    bank_account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)

    # Terms & Conditions
    terms_conditions = models.BooleanField(default=True)

    # Status
    PROFILE_STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    profile_status = models.CharField(
        max_length=20,
        choices=PROFILE_STATUS_CHOICES,
        default='PENDING'
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # MPIN Helpers
    def set_mpin(self, raw_mpin):
        self.mpin = make_password(raw_mpin)

    def check_mpin(self, raw_mpin):
        return check_password(raw_mpin, self.mpin)

    def __str__(self):
        return f"{self.display_name} ({self.contact_no})"


class BlacklistedToken(models.Model):
    user_id = models.ForeignKey('celebrity.CelebrityRegistration', on_delete=models.CASCADE, blank=True)                   
    token = models.TextField(unique=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id}  - {self.token[:20]}"

class RefreshTokenStore(models.Model):
    user_id = models.ForeignKey('celebrity.CelebrityRegistration', on_delete=models.CASCADE, blank=True)           
    refresh_token = models.TextField(unique=True)
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.refresh_token[:20]}"
    