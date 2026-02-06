from django.db import models
from admin_master.models import AdminUser, StatusMaster, City_master, State_master
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from team_head.models import TeamHead_register


class Executive_register(models.Model):
    auth_user = models.OneToOneField(
        AdminUser,
        on_delete=models.CASCADE,
        related_name="executive_reg",
        null=True,
        blank=True
    )
    emp_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
    )
    profile_image_url = models.URLField(
        max_length=500,
        null=True,
        blank=True
    )
    full_name = models.CharField(max_length=150)
    email_address = models.EmailField(unique=True, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, unique=True)
    email_id = models.EmailField(unique=True)
    password = models.CharField(max_length=255,)
    joining_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(max_length=20, null=True, blank=True)
    work_mode = models.CharField(max_length=20, null=True, blank=True)
    branch = models.CharField(max_length=20, null=True, blank=True)
    city = models.ForeignKey(
        'admin_master.City_master',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executives'
    )

    state = models.ForeignKey(
        'admin_master.State_master',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executives'
    )
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    reporting_to = models.ForeignKey(
        TeamHead_register,
        on_delete=models.PROTECT,
        related_name="reported_executives",
        null=True,
        blank=True
    )    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=120, null=True, blank=True)
    updated_by = models.CharField(max_length=120, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.emp_id:
            last = Executive_register.objects.order_by("-id").first()
            next_id = 1
            if last and last.emp_id:
                try:
                    last_number = int(last.emp_id.split("-")[1])
                    next_id = last_number + 1
                except:
                    next_id = last.id + 1
            self.emp_id = f"OV-EX-{next_id:06d}"

            # hash password
            if self.password and not self.password.startswith("pbkdf2_"):
                self.password = make_password(self.password)
                
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
    
    def set_mpin(self, raw_mpin):
        self.mpin = make_password(raw_mpin)

    def check_Executive(self, raw_mpin):
        return check_password(raw_mpin, self.password)

    @property
    def is_authenticated(self):
        return True
    
class ExecutiveSiteVisit(models.Model):
    STATUS_CHOICES = (
        ("COMPLETED", "COMPLETED"),
        ("SKIPPED", "SKIPPED"),
    )

    executive = models.ForeignKey(
        Executive_register,
        on_delete=models.CASCADE,
        related_name="site_visits"
    )
    visit_number = models.IntegerField()
    site_name = models.CharField(max_length=200)
    site_address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    visit_duration = models.IntegerField()  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField()

class ExecutiveLocationLog(models.Model):
    executive = models.ForeignKey(
        Executive_register,
        on_delete=models.CASCADE,
        related_name="location_logs"
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()

    class Meta:
        ordering = ["timestamp"]
