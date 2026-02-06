from django.db import models
from admin_master.models import AdminUser, StatusMaster, State_master, City_master
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from manager.models import Manager_register

class TeamHead_register(models.Model):
    auth_user = models.OneToOneField(
        AdminUser,
        on_delete=models.CASCADE,
        related_name="team_head_reg",
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
    city = models.ForeignKey(City_master, on_delete=models.PROTECT, null=True, blank=True)
    state = models.ForeignKey(State_master, on_delete=models.PROTECT, null=True, blank=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    reporting_to = models.ForeignKey(
        Manager_register,
        on_delete=models.PROTECT,
        related_name="reported_team_heads",
        null=True,
        blank=True
    )    
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=120, null=True, blank=True)
    updated_by = models.CharField(max_length=120, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.emp_id:
            last = TeamHead_register.objects.order_by("-id").first()
            next_id = 1
            if last and last.emp_id:
                try:
                    last_number = int(last.emp_id.split("-")[1])
                    next_id = last_number + 1
                except:
                    next_id = last.id + 1
            self.emp_id = f"OV-TH-{next_id:06d}"

            # hash password
            if self.password and not self.password.startswith("pbkdf2_"):
                self.password = make_password(self.password)
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.emp_id} - {self.full_name}"
    
    def set_mpin(self, raw_mpin):
        self.mpin = make_password(raw_mpin)

    def check_TeamHead(self, raw_mpin):
        return check_password(raw_mpin, self.password)

    @property
    def is_authenticated(self):
        return True