from django.db import models
from admin_master.models import AdminUser, StatusMaster, City_master, State_master,TaskStatus,TaskType, ReasonForTask,Service_master,LeadSource
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from datetime import datetime,timedelta, time
from vendor.models import Vendor_registration
from executive.models import Executive_register
from django.utils.crypto import get_random_string
from django.conf import settings


class BlacklistedToken(models.Model):
    user_id = models.IntegerField()                  
    role = models.CharField(max_length=20, default="null")           
    token = models.TextField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.user_id}  - {self.blacklisted_at}"


class RefreshTokenStore(models.Model):
    user_id = models.IntegerField()                 
    role = models.CharField(max_length=20, default="null")          
    refresh_token = models.TextField(unique=True)
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role} - {self.user_id}"



class DailyWorkLog(models.Model):
    user_id = models.IntegerField()
    emp_id = models.CharField(max_length=20, editable=False)
    role = models.CharField(max_length=20)
    date = models.DateField()

    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("present", "Present"),
            ("late", "Late"),
            ("absent", "Absent"),
            ("half-day", "Half Day"),
        ],
        default="present"
    )

    working_status = models.CharField(max_length=20, null=True)

    work_minutes = models.IntegerField(default=0)
    work_duration = models.CharField(max_length=10, null=True, blank=True)

    def set_login_status(self):
        """Set attendance status based on login time"""
        if not self.login_time:
            self.status = "absent"
            return

        if time(9, 0) <= self.login_time <= time(9, 30):
            self.status = "present"
        elif time(9, 31) <= self.login_time < time(13, 0):
            self.status = "late"
        else:
            self.status = "half-day"

    def calculate_work_minutes(self):
        """Calculate work duration like 8h 52m (no datetime.combine)"""

        if not self.login_time or not self.logout_time:
            self.work_minutes = 0
            self.work_duration = "Nil"
            return

        # Convert login time to minutes since midnight
        login_minutes = (
            self.login_time.hour * 60 +
            self.login_time.minute
        )

        # Convert logout time to minutes since midnight
        logout_minutes = (
            self.logout_time.hour * 60 +
            self.logout_time.minute
        )

        # Handle overnight shift (logout after midnight)
        if logout_minutes < login_minutes:
            logout_minutes += 24 * 60

        total_minutes = logout_minutes - login_minutes
        self.work_minutes = total_minutes

        hours = total_minutes // 60
        minutes = total_minutes % 60
        self.work_duration = f"{hours}h {minutes}m"

class BankAccount(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete= models.CASCADE,
        related_name="bank_accounts"
    )
    account_holder_name = models.CharField(max_length=150)
    bank_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=11)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=150)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.bank_name} - {self.account_number[:4]}"
    
class AadhaarDetails(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="aadhaar_details"
    )
    aadhaar_number = models.CharField(max_length=12, unique=True)
    aadhaar_card_url = models.URLField(max_length=500)
    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100)
    updated_by = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.aadhaar_number[:4]}"

class Leads_registration(models.Model):

    TASK_PRIORITY_TYPE = (
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    )

    PROFILE_STATUS_CHOICES = [
        ('REGISTERED', 'Registered'),
        ('SIGNUP', 'Signup'),
    ]

    email = models.EmailField(null=True, blank=True, unique=True)
    contact_no = models.CharField(max_length=12, null=True, blank=True, unique=True)
    alternative_no = models.CharField(max_length=12, null=True, blank=True, unique=True)

    lead_name = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)

    latitude = models.DecimalField(max_digits=13, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=13, decimal_places=6, null=True, blank=True)

    lead_id = models.CharField(max_length=20, unique=True, editable=False)

    service_id = models.ForeignKey(Service_master, on_delete=models.PROTECT, null=True, blank=True)
    lead_source = models.ForeignKey(LeadSource, on_delete=models.PROTECT, null=True, blank=True)

    referral_code = models.CharField(max_length=12, unique=True, null=True, blank=True)

    city_id = models.ForeignKey(City_master, on_delete=models.PROTECT, null=True, blank=True)
    state_id = models.ForeignKey(State_master, on_delete=models.PROTECT, null=True, blank=True)


    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)

    task_priority = models.CharField(max_length=20, choices=TASK_PRIORITY_TYPE)
    reason = models.TextField(max_length=255)

    selected_date_time = models.DateTimeField()

    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.CASCADE,
        related_name="leads",
        db_index=True,
        default=1
    )

    lead_account_staus = models.CharField(
        max_length=20,
        choices=PROFILE_STATUS_CHOICES,
        default="REGISTERED"
    )

    assigned_to = models.IntegerField()
    role = models.CharField(max_length=20)

    updated_by = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.IntegerField(null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new and not self.lead_id:
            self.lead_id = f"LEAD-{self.pk:06d}"
            super().save(update_fields=["lead_id"])


class ExecutiveTask(models.Model):

    TASK_PRIORITY_TYPE = (
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    )

    TASK_STATUS_CHOICES = (
        ("created", "Created"),
        ("completed", "Completed"),
        ("reschedule", "Reschedule"),
    )
    task_id = models.CharField(max_length=20, unique=True, editable=False)
    vendor_id = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name="ExecutiveTask",
        db_index=True,
        null=True,
        blank=True
    )
    emp_id = models.ForeignKey(
        Executive_register,
        on_delete=models.CASCADE,
        related_name="ExecutiveTask",
        db_index=True
    )

    lead = models.ForeignKey(
        Leads_registration,
        on_delete=models.CASCADE,
        related_name="ExecutiveTask",
        db_index=True,
        null=True,
        blank=True
    )
    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.CASCADE,
        related_name="ExecutiveTask",
        db_index=True
    )

    task_status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        related_name="ExecutiveTask",
        db_index=True,
        default=2,
    )


    task_priority = models.CharField(max_length=20, choices=TASK_PRIORITY_TYPE)

    reschedule_reason = models.ForeignKey(
        ReasonForTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    role = models.CharField(max_length=20)  # logged-in role

    date = models.DateField()
    time = models.TimeField()
    note = models.CharField(max_length=2000)

    created_by = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=255, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # first save to get primary key

        if not self.task_id:
            self.task_id = f"TASK-{self.pk:06d}"  # 5 digits with leading zeros
            ExecutiveTask.objects.filter(pk=self.pk).update(task_id=self.task_id)

class ExecutiveTaskActivity(models.Model):

    ACTION_CHOICES = (
        ("created", "Created"),
        ("rescheduled", "Rescheduled"),
        ("completed", "Completed"),
    )

    TASK_PRIORITY_TYPE = (
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    )

    # Reference to main task
    task = models.ForeignKey(
        ExecutiveTask,
        on_delete=models.CASCADE,
        related_name="activities"
    )

    vendor_id = models.ForeignKey(
        Vendor_registration,
        on_delete=models.CASCADE,
        related_name="task_activities",
        null=True,
        blank=True
    )

    emp_id = models.ForeignKey(
        Executive_register,
        on_delete=models.CASCADE,
        related_name="task_activities"
    )

    lead = models.ForeignKey(
        Leads_registration,
        on_delete=models.CASCADE,
        related_name="task_activities",
        db_index=True,
        null=True,
        blank=True
    )
    task_type = models.ForeignKey(
        TaskType,
        on_delete=models.CASCADE,
        related_name="task_activities",
        db_index=True
    )

    task_status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        related_name="task_activities",
        db_index=True,
        default=2
    )

    reschedule_reason = models.ForeignKey(
        ReasonForTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    task_priority = models.CharField(max_length=20, choices=TASK_PRIORITY_TYPE)

    role = models.CharField(max_length=20)

    date = models.DateField()
    time = models.TimeField()

    note = models.CharField(max_length=2000, blank=True, null=True)

    #ACTIVITY-SPECIFIC FIELDS
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    performed_by = models.CharField(max_length=50)
    performed_role = models.CharField(max_length=20)
    selfie_photo = models.URLField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


