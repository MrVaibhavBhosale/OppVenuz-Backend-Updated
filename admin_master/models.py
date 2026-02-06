from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


# Model For Role 
class Role_master(models.Model):

    role_name = models.CharField(max_length=255)
    status = models.IntegerField(default=1)

    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.role_name
    
# Model For Best Suited For
class Best_suited_for(models.Model):

    name = models.CharField(max_length=255)
    status = models.IntegerField(default=1)

    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Model For State
class State_master(models.Model):

    state_name = models.CharField(max_length=255)
    state_code = models.IntegerField()
    status = models.IntegerField(default=1)

    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.state_name

# Model For City
class City_master(models.Model):
    state = models.ForeignKey(
        State_master, 
        on_delete=models.CASCADE,        
        related_name='cities'           
    )
    city_name = models.CharField(max_length=255)
    pincode = models.IntegerField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    status = models.IntegerField(default=1)

    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.city_name}, {self.state.state_name}"
    
# Model For Payment Type
class Payment_type(models.Model):

    payment_type = models.CharField(max_length=255)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.payment_type
    

class Service_master(models.Model):
    service_name = models.CharField(max_length=255)
    registration_charges = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    status = models.IntegerField(default=1)

    def __str__(self):
        return self.service_name

class document_type(models.Model):
    STATUS_CHOICES = (
        (1, 'Active'),
        (2, 'Inactive'),
        (3, 'Deleted'),
    )

    document_type = models.CharField(max_length=255)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=1)

    created_by = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.document_type

# Model For Article Type
class Article_type(models.Model):
    article_type = models.CharField(max_length=255)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.article_type

# Model For Delivery Options
class Delivery_option(models.Model):

    delivery_option = models.CharField(max_length=255)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.delivery_option
    
# Model For Best Deal
class Best_deal(models.Model):

    deal_name = models.CharField(max_length=255)
    image = models.URLField(max_length=255)
    occasion = models.CharField(max_length=255)
    duration_of_deal = models.DateTimeField(max_length=255)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.deal_name

# Model For App Version
class App_version(models.Model):

    app_version = models.CharField(max_length=255) 
    is_force_update = models.BooleanField(default=False) 
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.app_version, self.is_force_update
    
# ------------------ STATUS MASTER ------------------
class StatusMaster(models.Model):
    STATUS_TYPE_CHOICES = (
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Deleted', 'Deleted'),
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Archived', 'Archived'),
        ('Draft', 'Draft'),
        ('Completed', 'Completed'),
        ('Expired', 'Expired'),
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Suspended', 'Suspended'),
        ('on-Hold', 'on-Hold')
    )

    status_type = models.CharField(
        max_length=50,
        choices=STATUS_TYPE_CHOICES,
        default='Active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_status_master'

    def __str__(self):
        return self.status_type


# ------------------ CAKE MASTER ------------------
class CakeMaster(models.Model):
    shape_name = models.CharField(max_length=100, default="Round")
    cake_type = models.CharField(max_length=100, default="Egg")
    flavor = models.CharField(max_length=100, default="Vanilla")
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_cake_master'

    def __str__(self):
        return f"{self.flavor} - {self.shape_name} ({self.cake_type})"


# ------------------ COMPANY TYPE MASTER ------------------
class CompanyTypeMaster(models.Model):
    company_type = models.CharField(max_length=150, unique=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_company_type_master'

    def __str__(self):
        return self.company_type


# ------------------ VENUE TYPE MASTER ------------------
class VenueTypeMaster(models.Model):
    venue_type = models.CharField(max_length=150, unique=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_venue_type_master'

    def __str__(self):
        return self.venue_type


# ------------------ OPPVENUZ CHOICE MASTER ------------------
class OppvenuzChoiceMaster(models.Model):
    choice_name = models.CharField(max_length=255, unique=True)
    minimum_comments_count = models.PositiveIntegerField(default=0)
    archived_comments_count = models.PositiveIntegerField(default=0)
    average_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_oppvenuz_choice_master'

    def save(self, *args, **kwargs):
        if self.minimum_comments_count > 0:
            self.average_percentage = (self.archived_comments_count / self.minimum_comments_count) * 100
        else:
            self.average_percentage = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return self.choice_name


# ------------------ GST MASTER ------------------
class GstMaster(models.Model):
    gst_percentage = models.PositiveIntegerField()
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'admin_master_gst_master'

    def __str__(self):
        return f"{self.gst_percentage}%"


class OnboardingScreens(models.Model):
    TYPE_CHOICES = (
        (1, "GIF"),
        (2, "FLASH"),
    )

    STATUS_CHOICES = (
        (1, "Active"),
        (2, "Deleted"),
    )

    title = models.CharField(max_length=255)
    media = models.JSONField(null=True, blank=True) 
    type = models.IntegerField(choices=TYPE_CHOICES, default=2) 
    order = models.IntegerField(default=0)
    status = models.IntegerField(choices=STATUS_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["type", "order"]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"


class Social_media_master(models.Model):
    media_name = models.CharField(max_length=255, unique=True)
    media_image = models.URLField(max_length=300)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.media_name
    
class Terms_and_condition_master(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    slug = models.CharField(max_length=255, unique=True, blank=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Terms and Condition"
        verbose_name_plural = "Terms and Conditions"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = ''.join(e for e in self.title.upper() if e.isalnum())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title}"
    
# Model For Oppvenuz ques ans master
class Oppvenuz_ques_ans_master(models.Model):

    question = models.CharField(max_length=2500)
    answer = models.CharField(max_length=2500)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.question    

# Model For Oppvenuz ques ans master
class Common_setting(models.Model):

    min_photo_upload = models.IntegerField()
    max_photo_upload = models.IntegerField()
    min_video_upload = models.IntegerField()
    max_video_upload = models.IntegerField()
    min_photo_size = models.IntegerField()
    max_photo_size = models.IntegerField()
    min_video_size = models.IntegerField()
    max_video_size = models.IntegerField()
    image_format = models.CharField(max_length=500)
    video_format = models.CharField(max_length=500)
    min_document_upload = models.IntegerField()
    max_document_upload = models.IntegerField()
    document_format = models.CharField(max_length=500)
    status = models.IntegerField(default=1)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if Common_setting.objects.exists() and not self.pk:
            # Update the existing one instead of creating new
            existing = Common_setting.objects.first()
            self.pk = existing.pk
        super(Common_setting, self).save(*args, **kwargs)
     
    def __str__(self):
        return "Common Settings"
    
class CompanyDocumentMapping(models.Model):
    company_type = models.ForeignKey(CompanyTypeMaster, on_delete=models.CASCADE, related_name='mapped_documents')
    document_type = models.ForeignKey(document_type, on_delete=models.CASCADE, related_name='mapped_companies')
    status = models.PositiveSmallIntegerField(default=1)  
    created_by = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admin_master_company_document_mapping'
        unique_together = ('company_type', 'document_type')

    def __str__(self):
        return f"{self.company_type.company_type} → {self.document_type.document_type}"
class AdminUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, mobile_no=None, full_name=None, role="admin", **extra_fields):
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, mobile_no=mobile_no, full_name=full_name, role=role, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "admin")
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "super_admin")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)

    # Provide get_by_natural_key so Django's checks and some internals are happy
    def get_by_natural_key(self, username):
        # Accept email or mobile (if mobile passed)
        if "@" in username:
            return self.get(email=username)
        return self.get(mobile_no=username)

class AdminUser(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ("super_admin", "Super Admin"),
        ("admin", "Admin"),
    )

    admin_uid = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True
    )

    email = models.EmailField(unique=True)
    mobile_no = models.CharField(
        max_length=15,
        unique=True,
        null=True,
        blank=True
    )
    full_name = models.CharField(max_length=150, blank=True)

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="admin"
    )

    profile_image = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    status = models.ForeignKey(StatusMaster, models.PROTECT, null=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)

    objects = AdminUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["mobile_no", "full_name"]

    class Meta:
        db_table = "admin_user"

    def save(self, *args, **kwargs):
        """ Auto-generate admin_uid like: AD0000000001
        """
        if not self.admin_uid:
            with transaction.atomic():
                last_admin = (
                    AdminUser.objects
                    .select_for_update()
                    .order_by("-id")
                    .first()
                )

                if last_admin and last_admin.admin_uid:
                    last_number = int(
                        last_admin.admin_uid.replace("AD", "")
                    )
                else:
                    last_number = 0

                self.admin_uid = f"AD{last_number + 1:010d}"

        # Super admin permissions
        if self.role == "super_admin":
            self.is_staff = True
            self.is_superuser = True

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name or self.email} ({self.admin_uid})"

class AdminRefreshTokenStore(models.Model):
    user = models.ForeignKey('admin_master.AdminUser', on_delete=models.CASCADE, blank=True)
    refresh_token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.refresh_token[:20]}"

    class Meta:
        db_table = "admin_master_adminrefreshtokenstore"


class BlacklistedAdminAccessToken(models.Model):
    user = models.ForeignKey('admin_master.AdminUser', on_delete=models.CASCADE, null=True, blank=True)
    token = models.TextField(unique=True)
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.token[:20]}"

class EmploymentType(models.Model):
    employment_type = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    working_hours = models.PositiveIntegerField()
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.employment_type

class WorkMode(models.Model):
    work_mode_name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    location_type = models.CharField(
        max_length=50,
        choices=[
            ('Office', 'Office'),
            ('Remote', 'Remote'),
            ('Hybrid', 'Hybrid')
        ]
    )
    working_rule = models.CharField(
        max_length=50,
        choices=[
            ('Fixed', 'Fixed'),
            ('Flexible', 'Flexible')
        ]
    )
    status = models.ForeignKey(
        StatusMaster,
        on_delete=models.PROTECT,
        default=1
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.work_mode_name

class TentativeBudget(models.Model):
    label = models.CharField(
        max_length=50,
        help_text="Eg: ₹2L - ₹10L"
    )
    min_amount = models.PositiveIntegerField(
        help_text="Amount in INR (Eg: 200000)"
    )
    max_amount = models.PositiveIntegerField(
        help_text="Amount in INR (Eg: 1000000)"
    )
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Tentative Budget"
        verbose_name_plural = "Tentative Budgets"

    def __str__(self):
        return self.label

class CelebrityProfession(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_professions"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_professions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_master_celebrity_profession"
        ordering = ["name"]

    def __str__(self):
        return self.name

class Language(models.Model):
    language_name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    status = models.ForeignKey(
        StatusMaster,
        on_delete=models.PROTECT,
        default=1
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.language_name

class CommissionMaster(models.Model):
    COMMISSION_TYPE = (
        ("SERVICE", "Service Wise"),
        ("GENERAL", "General"),
    )

    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPE)
    service = models.ForeignKey(
        Service_master,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or self.service.service_name

class PreferredEventType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    status = models.IntegerField(default=1)
    # 1 = Active, 0 = Inactive / Deleted

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_preferred_event_types"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_preferred_event_types"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "admin_master_preferred_event_type"
        ordering = ["name"]

    def __str__(self):
        return self.name

class MessageTemplate(models.Model):
    title = models.CharField(max_length=150, unique=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_message_templates"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_message_templates"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "message_template"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
class TaskType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_task_types"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_task_types"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class VendorResponse(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vendor_responses"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_vendor_responses"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class TaskStatus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_task_statuses"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_task_statuses"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ReasonForTask(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reason_for_tasks"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_reason_for_tasks"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class LeadSource(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_lead_sources"
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_lead_sources"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name