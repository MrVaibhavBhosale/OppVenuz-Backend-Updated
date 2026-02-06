from rest_framework import serializers
from .models import (
    RefreshTokenStore,
    DailyWorkLog,
    BankAccount,
    AadhaarDetails,
    ExecutiveTask,
    ExecutiveTaskActivity,
    Leads_registration
)
from manager.models import (
    Manager_register
)
from executive.models import (
    Executive_register
)
from team_head.models import (
    TeamHead_register
)
from django.contrib.auth import authenticate
import re
from django.db import models
import os
from django.db.models import Q
from admin_master.models import AdminUser, State_master, City_master, TaskStatus,TaskType, ReasonForTask
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import check_password
from vendor.models import Vendor_registration
from rest_framework.exceptions import ValidationError
import boto3
import os
import uuid
from django.db import transaction
from django.utils import timezone


def get_reporting_to(instance, role):
    """
    Match reporting_to_id with correct table based on role
    """

    if not instance.reporting_to_id:
        return None

    # Manager → Admin
    if role == "manager":
        admin = AdminUser.objects.filter(
            id=instance.reporting_to_id
        ).first()
        return {
            "id": admin.id if admin else None,
            "emp_id": admin.admin_uid if admin else None,
            "name": admin.full_name if admin else None
        }
    # Team Head → Manager
    if role == "team_head":
        manager = Manager_register.objects.filter(
            id=instance.reporting_to_id
        ).first()
        return {
                "id": manager.id if manager else None,
                "emp_id": manager.emp_id if manager else None,
                "name": manager.full_name if manager else None
            }

    # Executive → Team Head
    if role == "executive":
        team_head = TeamHead_register.objects.filter(
            id=instance.reporting_to_id
        ).first()
        return {
                    "id": team_head.id if team_head else None,
                    "emp_id": team_head.emp_id if team_head else None,
                    "name": team_head.full_name if team_head else None
                }

    return None


class ExecutiveDataSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)
    # documents = VendorDocumentSerializer(many=True, read_only=True)

    def get_city(self, obj):
        if obj.city_id:
            city = City_master.objects.filter(id=obj.city_id).first()
            return city.city_name if city else None
        return None

    def get_state(self, obj):
        if obj.state_id:
            state = State_master.objects.filter(id=obj.state_id).first()
            return state.state_name if state else None
        return None

    class Meta:
        model = Executive_register
        fields = '__all__'

    def to_representation(self, instance):
        return {
            "emp_id": instance.emp_id,
            "first_name": instance.full_name,
            "email": instance.email_id,
            "email_address": instance.email_address,
            "mobile_no": instance.mobile_no,
            "joining_date": instance.joining_date,
            "city": self.get_city(instance),
            "state": self.get_state(instance),
            "employment_type": instance.employment_type,
            "work_mode": instance.work_mode,
            "branch": instance.branch,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "profile_image": instance.profile_image_url,
            "reporting_to": get_reporting_to(instance,role="executive"),


        }

class ManagerDataSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)

    def get_city(self, obj):
        if obj.city_id:
            city = City_master.objects.filter(id=obj.city_id).first()
            return city.city_name if city else None
        return None

    def get_state(self, obj):
        if obj.state_id:
            state = State_master.objects.filter(id=obj.state_id).first()
            return state.state_name if state else None
        return None

    class Meta:
        model = Manager_register
        fields = '__all__'

    def to_representation(self, instance):
        return {
            "emp_id": instance.emp_id,
            "first_name": instance.full_name,
            "email": instance.email_id,
            "email_address": instance.email_address,
            "mobile_no": instance.mobile_no,
            "joining_date": instance.joining_date,
            "city": self.get_city(instance),
            "state": self.get_state(instance),
            "employment_type": instance.employment_type,
            "work_mode": instance.work_mode,
            "branch": instance.branch,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "profile_image": instance.profile_image_url,
            "reporting_to": get_reporting_to(instance,role="manager"),

        }

class TeamHeadDataSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)

    def get_city(self, obj):
        if obj.city_id:
            city = City_master.objects.filter(id=obj.city_id).first()
            return city.city_name if city else None
        return None

    def get_state(self, obj):
        if obj.state_id:
            state = State_master.objects.filter(id=obj.state_id).first()
            return state.state_name if state else None
        return None

    class Meta:
        model = TeamHead_register
        fields = '__all__'

    def to_representation(self, instance):
        return {
            "emp_id": instance.emp_id,
            "first_name": instance.full_name,
            "email": instance.email_id,
            "email_address": instance.email_address,
            "mobile_no": instance.mobile_no,
            "joining_date": instance.joining_date,
            "city": self.get_city(instance),
            "state": self.get_state(instance),
            "employment_type": instance.employment_type,
            "work_mode": instance.work_mode,
            "branch": instance.branch,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "profile_image": instance.profile_image_url,
            "reporting_to": get_reporting_to(instance,role="team_head"),


        }

class ExecutiveLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)

    def validate_refresh(self, value):
        if not RefreshTokenStore.objects.filter(refresh_token=value).exists():
            raise serializers.ValidationError("Refresh token not found or already logged out.")
        return value  
    
class MultiRoleLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = None
        role = None

        # ---------- EXECUTIVE ----------
        try:
            user = Executive_register.objects.get(
                Q(mobile_no=username) | Q(email_id=username) | Q(emp_id=username)
            )
            if user.check_Executive(password):
                role = "executive"
        except Executive_register.DoesNotExist:
            user = None

        # ---------- MANAGER ----------
        if user is None:
            try:
                user = Manager_register.objects.get(
                    Q(mobile_no=username) | Q(email_id=username) | Q(emp_id=username)
                )
                if user.check_Manager(password):
                    role = "manager"
            except Manager_register.DoesNotExist:
                user = None
        
        # ---------- TeamHead ----------
        if user is None:
            try:
                user = TeamHead_register.objects.get(
                    Q(mobile_no=username) | Q(email_id=username) | Q(emp_id=username)
                )
                if user.check_TeamHead(password):
                    role = "team_head"
            except TeamHead_register.DoesNotExist:
                user = None


        # ---------- FAILED ----------
        if user is None or role is None:
            raise AuthenticationFailed("Invalid username or password")

        attrs["user"] = user
        attrs["role"] = role
        return attrs


class DailyWorkLogSerializer(serializers.ModelSerializer):
    date = serializers.DateField(format="%d-%b-%Y")
    login_time = serializers.TimeField(format="%I:%M %p", allow_null=True)
    logout_time = serializers.TimeField(format="%I:%M %p", allow_null=True)

    hours_work = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = DailyWorkLog
        fields = [
            "date",
            "role",     
            "login_time",
            "logout_time",
            "hours_work",
            "status_label"
        ]

    def get_hours_work(self, obj):
        return obj.work_duration or "Nil"

    def get_status_label(self, obj):
        if obj.status == "late":
            return "Late login"
        if obj.status == "absent":
            return "Absent"
        return "Present"
    
class BankDetailsReadSerializer(serializers.ModelSerializer):
    masked_account_number = serializers.SerializerMethodField()

    class Meta:
        model = BankAccount
        fields = [
            "account_holder_name",
            "bank_name",
            "masked_account_number",
            "ifsc_code",
        ]

    def get_masked_account_number(self, obj):
        if not obj.account_number:
            return None
        return f"{'*' * (len(obj.account_number) - 4)}{obj.account_number[-4:]}"
    
class AadhaarDetailsReadSerializer(serializers.ModelSerializer):
    masked_aadhaar = serializers.SerializerMethodField()

    class Meta:
        model = AadhaarDetails
        fields = [
            "masked_aadhaar",
            "aadhaar_card_url",
            "is_verified",
        ]

    def get_masked_aadhaar(self, obj):
        return f"{'*' * 8}{obj.aadhaar_number[-4:]}"
    
class BankDetailsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ["account_holder_name", "bank_name", "account_number", "ifsc_code"]

class AadhaarDetailsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AadhaarDetails
        fields = ["aadhaar_number", "aadhaar_card_url", "is_verified"]


class ExecutiveTaskCreateSerializer(serializers.ModelSerializer):
    vendor_id = serializers.IntegerField()

    class Meta:
        model = ExecutiveTask
        fields = [
            "vendor_id",
            "task_type",
            "task_priority",
            "date",
            "time",
            "task_status",
            "note",
        ]

    def validate_vendor_id(self, value):
        if not Vendor_registration.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid vendor")
        return value

    def create(self, validated_data):
        request = self.context["request"]
        payload = request.auth

        # Auth data
        user_id = payload.get("user_id")
        role = payload.get("role")

        if role != "executive":
            raise serializers.ValidationError("Only executives can create tasks")

        vendor_id = validated_data.pop("vendor_id")

        task = ExecutiveTask.objects.create(
            vendor_id_id=vendor_id,
            emp_id_id=user_id,          
            role=role,
            created_by=user_id,
            **validated_data
        )

        ExecutiveTaskActivity.objects.create(
            task=task,
            vendor_id=task.vendor_id,
            emp_id=task.emp_id,
            task_type=task.task_type,
            task_priority=task.task_priority,
            role=task.role,
            date=task.date,
            time=task.time,
            task_status=task.task_status,
            note=task.note,
            action="created", 
            performed_by=user_id,
            performed_role=role
        )
        return task
    
class TaskRescheduleSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    task_status_id = serializers.IntegerField()

    date = serializers.DateField(required=False)
    time = serializers.TimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    reschedule_reason_id = serializers.IntegerField(allow_null=True)

    def validate_task_status_id(self, value):
        if not TaskStatus.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid task status")
        return value

    def validate(self, data):
        task_id = data["task_id"]
        new_status_id = data["task_status_id"]

        try:
            task = ExecutiveTask.objects.get(task_id=task_id)
        except ExecutiveTask.DoesNotExist:
            raise serializers.ValidationError("Task not found")

        # BLOCK IF ALREADY COMPLETED
        if task.task_status_id == 4:
            raise serializers.ValidationError(
                "Completed task cannot be rescheduled or closed"
            )

        # RESCHEDULE
        if new_status_id == 3:
            if not data.get("date") or not data.get("time"):
                raise serializers.ValidationError(
                    "Date and time are required for reschedule"
                )
            if not data.get("reschedule_reason_id"):
                raise serializers.ValidationError(
                    "Reschedule reason is required"
                )

        return data


class TaskCompleteSerializer(serializers.Serializer):
    task_id = serializers.CharField()
    task_status_id = serializers.IntegerField()
    selfie_photo = serializers.ImageField(required=True)
    note = serializers.CharField(required=False, allow_blank=True)

    def validate_task_status_id(self, value):
        if not TaskStatus.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid task status")
        return value

    def validate(self, data):
        task_id = data["task_id"]

        try:
            task = ExecutiveTask.objects.get(task_id=task_id)
        except ExecutiveTask.DoesNotExist:
            raise serializers.ValidationError("Task not found")

        # ALREADY COMPLETED
        if task.task_status_id == 4:
            raise serializers.ValidationError(
                "Task is already completed"
            )

        # ONLY COMPLETED STATUS ALLOWED
        if data["task_status_id"].id != 4:
            raise serializers.ValidationError(
                "Only completed status is allowed in this API"
            )

        return data
    def upload_to_s3(self, file_obj, task_id):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("s3AccessKey"),
            aws_secret_access_key=os.getenv("s3Secret"),
            region_name=os.getenv("AWS_REGION"),
        )

        bucket = os.getenv("S3_BUCKET_NAME")

        ext = os.path.splitext(file_obj.name)[1]
        file_name = f"{task_id}_{uuid.uuid4()}{ext}"
        file_key = f"task_selfies/{file_name}"

        s3.upload_fileobj(
            file_obj,
            bucket,
            file_key,
            ExtraArgs={
                "ACL": "public-read",
                "ContentType": file_obj.content_type,
            },
        )

        return f"https://{bucket}.s3.amazonaws.com/{file_key}"

    def save(self, **kwargs):
        request = self.context["request"]
        user_id = request.auth.get("user_id")
        role = request.auth.get("role")

        with transaction.atomic(): 
            task = ExecutiveTask.objects.select_for_update().get(
                task_id=self.validated_data["task_id"]
            )

            task_status = TaskStatus.objects.get(
                id=self.validated_data["task_status_id"],
                is_active=True
            )

            # Upload selfie
            selfie_file = self.validated_data["selfie_photo"]
            selfie_url = self.upload_to_s3(selfie_file, task.task_id)

            # Update task
            task.task_status = task_status
            task.note = self.validated_data.get("note", task.note)
            task.updated_by = user_id
            task.save()

            # Activity log
            ExecutiveTaskActivity.objects.create(
                task=task,
                vendor_id=task.vendor_id,
                emp_id=task.emp_id,
                task_type=task.task_type,
                task_priority=task.task_priority,
                task_status=task_status,
                role=task.role,
                date=task.date,
                time=task.time,
                note=task.note,
                action="completed",
                performed_by=user_id,
                performed_role=role,
                selfie_photo = selfie_url,
            )

        return task, selfie_url
    
class TaskActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutiveTask
        fields = [
            'task_id',
            'task_type_id',
            'task_priority',
            'role',
            'date',
            'time',
            'note',
            'vendor_id_id',
            'created_at'
        ]
        read_only_fields = ('created_at',) 

class MyTaskListSerializer(serializers.ModelSerializer):
    task_type = serializers.CharField(source="task_type.name")
    task_status = serializers.CharField(source="task_status.name")
    vendor_name = serializers.CharField(source="vendor_id.first_name")
    vendor_email = serializers.CharField(source="vendor_id.email")
    vendor_phone = serializers.CharField(source="vendor_id.whatsapp_no")
    vendor_city = serializers.CharField(source="vendor_id.city_id")
    vendor_state = serializers.CharField(source="vendor_id.state_id")

    vendor_address = serializers.SerializerMethodField()
    status_badge = serializers.SerializerMethodField()
    schedule_label = serializers.SerializerMethodField()
    schedule_time = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveTask
        fields = [
            "task_id",
            "task_type",
            "status_badge",
            "vendor_name",
            "vendor_email",
            "vendor_phone",
            "vendor_city",
            "vendor_state",
            "vendor_address",
            "schedule_label",
            "schedule_time",
            "task_status",
        ]

    def get_vendor_address(self, obj):
        return f"{obj.vendor_id.city_id}, {obj.vendor_id.state_id},{obj.vendor_id.address}"
    

    def get_status_badge(self, obj):
        today = timezone.now().date()

        if obj.task_status.name.lower() == "completed":
            return "Completed"

        if obj.date == today:
            return "Today"
        elif obj.date > today:
            return "Upcoming"
        else:
            return "Overdue"

    def get_schedule_label(self, obj):
        return "Task Completed" if obj.task_status.name.lower() == "completed" else "Task Schedule"

    def get_schedule_time(self, obj):
        return f"{obj.date.strftime('%d %B %Y')}, {obj.time.strftime('%I:%M %p')}"

class LeadCreateSerializer(serializers.ModelSerializer):

    task_type = serializers.PrimaryKeyRelatedField(
        queryset=TaskType.objects.all(),
        required=True
    )

    class Meta:
        model = Leads_registration
        fields = [
            "email",
            "contact_no",
            "alternative_no",
            "lead_name",
            "pincode",
            "address",
            "latitude",
            "longitude",
            "service_id",
            "lead_source",
            "referral_code",
            "city_id",
            "state_id",
            "task_priority",
            "reason",
            "selected_date_time",
            "task_type",
        ]

    def validate_selected_date_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError(
                "Selected date & time cannot be in the past"
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get("request")
        payload = request.auth if request else None

        if not payload:
            raise serializers.ValidationError("Invalid authentication token")

        user_id = payload.get("user_id")
        role = payload.get("role")

        if not user_id or not role:
            raise serializers.ValidationError("Invalid token payload")

        task_type = validated_data.pop("task_type")

        # 🔐 ROLE VALIDATION
        if role == "executive":
            if not Executive_register.objects.filter(id=user_id).exists():
                raise serializers.ValidationError(
                    "Logged-in executive not found"
                )

        elif role == "manager":
            if not Manager_register.objects.filter(id=user_id).exists():
                raise serializers.ValidationError(
                    "Logged-in manager not found"
                )

        else:
            raise serializers.ValidationError("Invalid role")

        # CREATE LEAD
        lead = Leads_registration.objects.create(
            **validated_data,
            task_type=task_type,
            assigned_to=user_id,
            role=role,
            created_by=user_id,
            updated_by=str(user_id),
        )

         # CREATE TASK ONLY FOR EXECUTIVE
        if role == "executive":

            task = ExecutiveTask.objects.create(
                emp_id_id=user_id,
                role=role,
                lead=lead,    
                task_type=task_type,
                task_priority=lead.task_priority,
                date=lead.selected_date_time.date(),
                time=lead.selected_date_time.time(),
                note=lead.reason,
                created_by=user_id,
                task_status_id=2,
            )

            # TASK ACTIVITY LOG
            ExecutiveTaskActivity.objects.create(
                task=task,
                lead=lead,    
                emp_id=task.emp_id,
                task_type=task.task_type,
                task_priority=task.task_priority,
                role=task.role,
                date=task.date,
                time=task.time,
                task_status=task.task_status,
                note=task.note,
                action="created",
                performed_by=user_id,
                performed_role=role
            )

        return lead