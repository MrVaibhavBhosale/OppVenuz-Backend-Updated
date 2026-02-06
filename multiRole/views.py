from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from user_agents import parse
from django.utils import timezone
from datetime import datetime
from datetime import time
from .serializers import ExecutiveDataSerializer, MultiRoleLoginSerializer, ManagerDataSerializer, TeamHeadDataSerializer, DailyWorkLogSerializer, ExecutiveTaskCreateSerializer, TaskRescheduleSerializer, TaskCompleteSerializer, ExecutiveTaskActivity,TaskActivitySerializer,MyTaskListSerializer,LeadCreateSerializer
from .models import RefreshTokenStore, BlacklistedToken, DailyWorkLog, ExecutiveTask
from .authentication import MultiRoleJWTAuthentication
from jwt_utils import create_jwt
from rest_framework.permissions import AllowAny
from rest_framework import serializers
from multiRole.permissions import EmployeeDetailsPermission
from rest_framework_simplejwt.exceptions import AuthenticationFailed
import csv
from django.http import HttpResponse
from manager.models import (
    Manager_register
)
from executive.models import (
    Executive_register
)
from team_head.models import (
    TeamHead_register
)
from django.db.models import Q
from vendor.models import Vendor_registration
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from admin_master.models import TaskStatus, ReasonForTask
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Case, When, Value, IntegerField
class MultiRoleLoginView(generics.GenericAPIView):
    serializer_class = MultiRoleLoginSerializer
    permission_classes = [AllowAny]
    

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        role = serializer.validated_data["role"]

        # ----------- TOKENS -----------
        access = create_jwt({
            "user_id": user.id,
            "role": role,
            "token_type": "access"
        })

        refresh = create_jwt({
            "user_id": user.id,
            "role": role,
            "token_type": "refresh"
        })

        # ----------- SINGLE SESSION -----------
        RefreshTokenStore.objects.filter(
            user_id=user.id,
            role=role
        ).delete()

        RefreshTokenStore.objects.create(
            user_id=user.id,
            role=role,
            refresh_token=refresh,
            token=access
        )

        # ----------- DAILY WORK LOG -----------

        now_utc = timezone.now()

        # Convert to local timezone
        now_local = timezone.localtime(now_utc)

        # Extract date and time
        today = now_local.date()
        now_time = now_local.time()

        log = DailyWorkLog.objects.filter(
            user_id=user.id,
            emp_id=user.emp_id,
            role=role,
            date=today,
            logout_time__isnull=True
        ).first()

        if not log:
            log = DailyWorkLog.objects.create(
                user_id=user.id,
                emp_id=user.emp_id,
                role=role,
                date=today,
                login_time=now_time,
                working_status="working"
            )
            log.set_login_status()
            log.save(update_fields=["status"])

        # ---------- ROLE-BASED DATA ----------
        if role == "executive":
            data = ExecutiveDataSerializer(user).data
        elif role == "manager":
            data = ManagerDataSerializer(user).data
        elif role == "team_head":
            data = TeamHeadDataSerializer(user).data
        else:
            data = {"id": user.id}

        data.update({
            "access": access,
            "refresh": refresh,
            "role": role
        })

        return Response({
            "status": True,
            "message": "Login successful",
            "data": data
        }, status=status.HTTP_200_OK)
    

class MultiRoleLogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(help_text="Refresh token")


@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        operation_summary="Logout user",
        operation_description="Logout user and blacklist tokens",
        request_body=MultiRoleLogoutSerializer,
        responses={
            200: openapi.Response("Logout successful"),
            400: openapi.Response("Invalid refresh token"),
        }
    )
)
class MultiRoleLogoutView(generics.GenericAPIView):
    authentication_classes = [MultiRoleJWTAuthentication]

    def post(self, request):
        if not request.auth:
            return Response(
                {
                    "status": False,
                    "message": "Authentication token is missing or invalid"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer = MultiRoleLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        refresh = serializer.validated_data["refresh"]

        payload = request.auth
        user_id = payload.get("user_id")
        role = payload.get("role")

        # ---------- DELETE REFRESH TOKEN ----------
        deleted, _ = RefreshTokenStore.objects.filter(
            user_id=user_id,
            role=role,
            refresh_token=refresh
        ).delete()

        if deleted == 0:
            return Response(
                {"status": False, "message": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ---------- BLACKLIST ACCESS TOKEN ----------
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = auth_header.replace("Bearer", "").strip()
            BlacklistedToken.objects.create(
                user_id=user_id,
                role=role,
                token=token
            )

        # ---------- DAILY WORK LOG ----------
        now_local = timezone.localtime(timezone.now())
        today = now_local.date()
        now_time = now_local.time()


        log = DailyWorkLog.objects.filter(
            user_id=user_id,
            role=role,
            date=today
        ).filter(
            Q(logout_time__isnull=True) |
            Q(logout_time=time(0, 0))
        ).order_by("-login_time").first()

        if not log:
            return Response(
                {"status": False, "message": "No active work log found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        log.logout_time = now_time
        log.calculate_work_minutes()
        log.working_status = "completed"
        log.save()   # ✅ no update_fields

        return Response(
            {"status": True, "message": "Logout successful"},
            status=status.HTTP_200_OK
        )
class getDailyLogsByUserView(generics.ListAPIView):
    serializer_class = DailyWorkLogSerializer
    authentication_classes = [MultiRoleJWTAuthentication]

    filter_backends = []
    
    def get_queryset(self):
        payload = self.request.auth
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message":"Authorization header missing"})

        user_id = payload.get("user_id")
        role = payload.get("role")

        input_role = self.kwargs.get("role")
        input_user_id = self.kwargs.get("emp_id")

        if input_role != role or input_user_id != user_id:
            raise AuthenticationFailed(detail={"status": False, "message":"You are not allowed to access this role data"})

        return DailyWorkLog.objects.filter(
            user_id=user_id,
            role=role
        ).order_by("-date")
 
class DownloadDailyLogsView(APIView):
    serializer_class = DailyWorkLogSerializer
    authentication_classes = [MultiRoleJWTAuthentication]

    def get_emp_id_by_role(self, role, request):
        token_user_id = str(request.auth.get("user_id"))

        if role.lower() == "executive":
            try:
                executive = Executive_register.objects.get(id=token_user_id)  
                return executive.emp_id
            except Executive_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Executive not found"})
        elif role.lower() == "manager":
            try:
                manager = Manager_register.objects.get(id=token_user_id) 
                return manager.emp_id
            except Manager_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Manager not found"})
        elif role.lower() == "team_head":
            try:
                manager = TeamHead_register.objects.get(id=token_user_id) 
                return manager.emp_id
            except TeamHead_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Team Head not found"})
            
        else:
            raise AuthenticationFailed(detail={"status": False, "message":"Invalid role"})

    def get(self, request, role):
        if not request.auth:
            return Response(
                {
                    "status": False,
                    "message": "Authentication token is missing or invalid"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        payload = request.auth

        token_user_id = str(payload.get("user_id"))
        token_role = payload.get("role")

        # ROLE CHECK
        if role != token_role:
            raise AuthenticationFailed(detail={"status": False, "message":"You are not allowed to download this data"})

        logs = DailyWorkLog.objects.filter(
            user_id=token_user_id,
            role=token_role
        ).order_by("-date")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="daily_logs_{token_user_id}_{token_role}.csv"'
        )

        writer = csv.writer(response)

        writer.writerow([
            "User ID",
            "Employee ID",
            "Role",
            "Date",
            "Login Time",
            "Logout Time",
            "Work Minutes",
            "Work Duration",
            "Working Status"
        ])

        for log in logs:
            writer.writerow([
                log.user_id,
                log.emp_id,
                log.role,
                log.date,
                log.login_time,
                log.logout_time,
                log.work_minutes,
                log.work_duration,
                log.working_status
            ])

        return response


class ExecutiveTaskCreateAPIView(generics.GenericAPIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    serializer_class = ExecutiveTaskCreateSerializer

    def post(self, request):
        serializer = ExecutiveTaskCreateSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        task = serializer.save()

        return Response({
            "status": True,
            "message": "Task created successfully",
            "data": {
                "task_id": task.task_id,
                "vendor_id": task.vendor_id.id,
                "emp_id": task.emp_id.emp_id,
                "task_type": task.task_type.id,
                "task_priority": task.task_priority,
                "task_status": task.task_status.id,
                "date": task.date,
                "time": task.time,
            }
        }, status=status.HTTP_201_CREATED)

class ExecutiveTaskRescheduleAPIView(generics.GenericAPIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    serializer_class = TaskRescheduleSerializer

    def post(self, request):
        if not request.auth:
            return Response(
                {
                    "status": False,
                    "message": "Authentication token is missing or invalid"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        payload = request.auth
        user_id = payload.get("user_id")
        role = payload.get("role")

        task = get_object_or_404(
            ExecutiveTask,
            task_id=data["task_id"]
        )

        task_status = get_object_or_404(
            TaskStatus,
            id=data["task_status_id"],
            is_active=True
        )

        reason = None

        # RESCHEDULE (ID = 3)
        if data["task_status_id"] == 3:
            reason = get_object_or_404(
                ReasonForTask,
                id=data["reschedule_reason_id"],
                is_active=True
            )
            task.date = data["date"]
            task.time = data["time"]

        # UPDATE TASK
        task.task_status = task_status
        task.reschedule_reason=reason
        task.note = data.get("note", task.note)
        task.updated_by = user_id
        task.save()

        # ACTIVITY LOG
        ExecutiveTaskActivity.objects.create(
            task=task,
            vendor_id=task.vendor_id,
            emp_id=task.emp_id,
            task_type=task.task_type,
            task_priority=task.task_priority,
            task_status=task_status,
            reschedule_reason=reason,
            role=task.role,
            date=task.date,
            time=task.time,
            note=task.note,
            action="rescheduled" if data["task_status_id"] == 3 else "closed" ,
            performed_by=user_id,
            performed_role=role
        )


        return Response(
                {
                    "status": True,
                    "message": (
                        "Task rescheduled successfully"
                        if data["task_status_id"] == 3
                        else "Task Closed successfully"
                    )
                },
                status=status.HTTP_200_OK
            )

class ExecutiveTaskCompleteAPIView(APIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Executive Task"],
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter("task_id", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("task_status_id", openapi.IN_FORM, type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter("selfie_photo", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
            openapi.Parameter("note", openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
        ],
    )
    def post(self, request):
        serializer = TaskCompleteSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        task, selfie_url = serializer.save()

        return Response(
            {
                "status": True,
                "message": "Task marked as completed",
                "task_id": task.task_id,
                "selfie_photo": selfie_url,
            },
            status=status.HTTP_200_OK,
        )

class getActivityLogsByUserView(generics.ListAPIView):
    authentication_classes = [MultiRoleJWTAuthentication]

    filter_backends = []
    
    def get_queryset(self):
        payload = self.request.auth
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message":"Authorization header missing"})

        user_id = payload.get("user_id")
        role = payload.get("role")

        input_role = self.kwargs.get("role")
        input_user_id = self.kwargs.get("emp_id")

        if input_role != role or input_user_id != user_id:
            raise AuthenticationFailed(detail={"status": False, "message":"You are not allowed to access this role data"})

        return DailyWorkLog.objects.filter(
            user_id=user_id,
            role=role
        ).order_by("-date")

# class MyTaskListAPIView(generics.ListAPIView):
#     authentication_classes = [MultiRoleJWTAuthentication]
#     serializer_class = TaskActivitySerializer
#     def get_queryset(self):
#         return ExecutiveTask.objects.all().order_by('-id')

#     def list(self, request, *args, **kwargs):
#         serializer = self.get_serializer(self.get_queryset(), many=True)
#         return Response({
#             "status":True,
#             "message": "Tasl list fetched successfully",
#             "data": serializer.data
#         }, status=status.HTTP_200_OK)

class MyTaskListAPIView(APIView):
    authentication_classes = [MultiRoleJWTAuthentication]

    def get(self, request):
        if not request.auth:
            return Response(
                {
                    "status": False,
                    "message": "Authentication token is missing or invalid"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        payload = request.auth
        user_id = payload.get("user_id")
        role = payload.get("role")

        queryset = ExecutiveTask.objects.select_related(
            "vendor_id",
            "task_type",
            "task_status",
        )

        # Executive sees only own tasks
        if role == "executive":
            queryset = queryset.filter(emp_id_id=user_id)

        # 📊 SUMMARY COUNTS
        total_tasks = queryset.count()
        closed_tasks = queryset.filter(task_status__name__iexact="completed").count()
        site_visits = queryset.filter(task_type__name__iexact="site visit").count()
        call_tasks = queryset.filter(task_type__name__iexact="call").count()

        today = timezone.now().date()

        # 🔀 ORDERING AS PER UI
        queryset = queryset.annotate(
            order_priority=Case(
                When(task_status__name__iexact="completed", then=Value(4)),
                When(date=today, then=Value(1)),
                When(date__gt=today, then=Value(2)),
                When(date__lt=today, then=Value(3)),
                default=Value(5),
                output_field=IntegerField(),
            )
        ).order_by("order_priority", "date", "time")

        serializer = MyTaskListSerializer(queryset, many=True)

        return Response(
            {
                "status": True,
                "summary": {
                    "total_tasks": total_tasks,
                    "closed_tasks": closed_tasks,
                    "site_visits": site_visits,
                    "call_tasks": call_tasks,
                },
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

class LeadCreateAPIView(generics.GenericAPIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    serializer_class = LeadCreateSerializer

    def post(self, request):
        if not request.auth:
            return Response(
                {
                    "status": False,
                    "message": "Authentication token is missing or invalid"
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        serializer = self.get_serializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        lead = serializer.save()

        return Response(
            {
                "status": True,
                "message": "Lead created successfully",
                "data": {
                    "lead_id": lead.lead_id,
                    "lead_name": lead.lead_name,
                    "assigned_to": lead.assigned_to,
                    "selected_date_time": lead.selected_date_time,
                }
            },
            status=status.HTTP_201_CREATED
        )
    

