from django.db import models, transaction
from .managers import VendorManager
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.contrib.postgres.fields import ArrayField
from admin_master.models import (
    Service_master,
    State_master,
    City_master, 
    Best_suited_for,
    CompanyTypeMaster,
    StatusMaster,
    AdminUser,
)
from django.utils import timezone
import random
from datetime import timedelta
from django.conf import settings


class Vendor(models.Model):
    business_name = models.CharField(max_length=255)
    email = models.EmailField()
    contact_number = models.CharField(max_length=20)
    working_since = models.IntegerField()  # Year
    years_of_experience = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'vendor'

    def __str__(self):
        return self.business_name
    

    
class Vendor_registration(models.Model): 
    auth_user = models.OneToOneField(
        AdminUser, on_delete=models.CASCADE, related_name="vendor_registration", null=True, blank=True
    )
    email = models.EmailField(null=True, blank=True, unique=True)
    contact_no = models.CharField(max_length=12, null=True, blank=True, unique=True)
    whatsapp_no = models.CharField(max_length=12, null=True, blank=True, unique=True)  
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)  
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    date_of_birth = models.DateField()
    mpin = models.CharField(max_length=255, editable=False)
    city_id = models.ForeignKey(City_master, on_delete=models.PROTECT, null=True, blank=True)
    state_id = models.ForeignKey(State_master, on_delete=models.PROTECT, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=13, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=13, decimal_places=6, null=True, blank=True)
    vendor_id = models.CharField(max_length=12, unique=True, blank=True)
    business_name = models.CharField(max_length=255)
    service_id = models.ForeignKey(Service_master, on_delete=models.PROTECT, null=True, blank=True)
    best_suited = models.ManyToManyField(Best_suited_for, blank=True)
    referral_code = models.CharField(max_length=12, unique=True, blank=True)
    working_since = models.DateField()
    year_of_experience = models.IntegerField(default=0)
    terms_conditions = models.BooleanField(default=True)
    privacy_policy = models.BooleanField(default=True)
    payment_cancellation = models.BooleanField(default=True)   
    # document_id = models.CharField(max_length=100, null=True, blank=True)
    document_id = ArrayField(models.IntegerField(), default=list, blank=True)
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
    ]
    PROFILE_STATUS_CHOICES = [
        ('Registered', 'Registered'),
        ('Approved', 'Approved'),
        ('Suspended', 'Suspended')
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')  
    profile_status = models.CharField(max_length=20, choices=PROFILE_STATUS_CHOICES, default='Registered')  
    is_active = models.BooleanField(default=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    reason = models.TextField(max_length=255)
    profile_image = models.URLField(null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VendorManager()

    class Meta:
        constraints = [
           models.UniqueConstraint(
                fields=['email', 'contact_no', 'service_id'],
                name='unique_vendor_service_contact'
           ),
        ]

    def set_mpin(self, raw_mpin):
        self.mpin = make_password(raw_mpin)

    def check_mpin(self, raw_mpin):
        return check_password(raw_mpin, self.mpin)
    
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def username(self):
        return self.email or self.contact_no or f"vendor_{self.pk}"

    def get_username(self):
        return self.email or self.contact_no

    def save(self, *args, **kwargs):
        
        if not self.vendor_id:
            with transaction.atomic():
                last_vendor = Vendor_registration.objects.select_for_update().order_by('-id').first()
                if last_vendor and last_vendor.vendor_id:
                    last_number = int(last_vendor.vendor_id.replace('OV', ''))
                else:
                    last_number = 0
                self.vendor_id = f"OV{last_number + 1:010d}"

        # --- Set referral_code same as vendor_id ---
        if not self.referral_code:
            self.referral_code = self.vendor_id

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.business_name} | {self.contact_no} | {self.whatsapp_no} | {self.email} | {self.vendor_id}"
    
class VendorDevice(models.Model):
    vendor_id = models.ForeignKey(Vendor_registration, on_delete=models.PROTECT)
    device_type = models.CharField(max_length=50)
    os_version = models.CharField(max_length=50)
    browser_name = models.CharField(max_length=50, null=True, blank=True)
    browser_version = models.CharField(max_length=50, null=True, blank=True)
    last_login = models.DateTimeField(auto_now=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    os_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ('vendor_id', 'device_type', 'os_version', 'browser_name', 'os_type')

    def __str__(self):
        return f"{self.vendor} - {self.device_type} {self.os_version}"
    

class VendorDocument(models.Model):
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
    vendor_business_no = models.CharField(max_length=20, default="")    
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
    OTP_TTL_SECONDS = 600       # 10 minutes
    BLOCK_SECONDS = 3600        # 1 hour

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
            # This will safely handle cases where OTP is None or invalid
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

class VenderBusinessDescription(models.Model):
    vendor = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name='business_descriptions'
    )
    vendor_reg_id = models.CharField(max_length=12, db_index=True)  
    description = models.CharField(max_length=5000)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Description for {self.vendor_reg_id}"

class ReadyToSellItem(models.Model):
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    image_urls = ArrayField(models.URLField(), default=list, blank=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.product_name
    
class ProductAddition(models.Model):
    addon_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image_urls = ArrayField(models.URLField(), default=list, blank=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.addon_name
    
class VendorProduct(models.Model):
    vendor_id = models.ForeignKey(
        Vendor_registration,
        on_delete=models.PROTECT,
        related_name='products',
        null=True,
        blank=True
    )
    data = models.JSONField()
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=120, null=True, blank=True)
    updated_by = models.CharField(max_length=120, null=True, blank=True)

    def __str__(self):
        return f"{self.vendor_id}"
    
class VendorSocialMedia(models.Model):
    vendor = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name='social_media'
    )
    vendor_reg_id = models.CharField(max_length=12, db_index=True)
    facebook_link = models.URLField(max_length=500, null=True, blank=True)
    instagram_link = models.URLField(max_length=500, null=True, blank=True)
    whatsapp_group_link = models.URLField(max_length=500, null=True, blank=True)
    youtube_link = models.URLField(max_length=500, null=True, blank=True)
    pinterest_link = models.URLField(max_length=500, null=True, blank=True)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Social Media for {self.vendor_reg_id}"
    
class VendorMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    ]

    vendor = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name='vendor_media'
    )
    vendor_code = models.CharField(max_length=12, db_index=True) 
    file_url = models.URLField(max_length=1000)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_hash = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=10, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.media_type} - {self.vendor_code}"


class RefreshTokenStore(models.Model):
    user = models.ForeignKey(AdminUser, on_delete=models.CASCADE, blank=True, related_name="refreshtokenstore")
    refresh_token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}"

class BlacklistedToken(models.Model):
    user = models.ForeignKey("Vendor_registration", on_delete=models.CASCADE)
    token = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.blacklisted_at}"
    
class VendorBankAccount(models.Model):
    vendor = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name="bank_accounts"
    )
    full_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=30)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=150)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_vendor_bankaccount"

    def __str__(self):
        return f"{self.vendor.id} - {self.bank_name}"

class VendorFeedback(models.Model):
    vendor = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    message = models.TextField()
    rating = models.IntegerField(default=5)
    is_visible = models.BooleanField(default=True)  
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Feedback for {self.vendor.vendor_id} - {self.rating}⭐"
    
class VendorFeedbackReply(models.Model):
    feedback = models.ForeignKey(
        VendorFeedback,
        on_delete=models.CASCADE,
        related_name="replies"
    )
    
    reply_text = models.TextField()
    reply_by = models.CharField(
        max_length=50,
        choices=[('ADMIN', 'Admin'), ('VENDOR', 'Vendor')],
        default='ADMIN'
    )
    
    replied_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Reply by {self.reply_by} on feedback {self.feedback.id}"

class CelebrityBanner(models.Model):
    title = models.CharField(max_length=255)
    image = models.URLField(max_length=500)   
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class BestDealBanner(models.Model):
    title = models.CharField(max_length=255)
    image = models.TextField()   # S3 URL
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title 

class CakeOptions(models.Model):
    flavors = models.JSONField(default=list)      
    shapes = models.JSONField(default=list)       
    types = models.JSONField(default=list)        
    combo_items = models.JSONField(default=list) 
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Cake Options"
    
class DeliveryOptions(models.Model):
    same_day_available = models.BooleanField(default=True)

    fixed_time_slots = models.JSONField(default=list)
    pre_midnight_slots = models.JSONField(default=list)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Delivery Options"