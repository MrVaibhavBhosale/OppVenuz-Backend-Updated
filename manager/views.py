from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from admin_master.authentication import AdminJWTAuthentication
from rest_framework.parsers import MultiPartParser, FormParser
from .pagination import StandardResultsSetPagination
from .serializers import (
    EmployeeRegisterSerializer,
    EmployeeReadSerializer,
    get_employee_update_serializer,
)
from .models import (
    Manager_register,
)
from team_head.models import TeamHead_register
from executive.models import Executive_register
from itertools import chain
import logging
from user_agents import parse
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
logger = logging.getLogger("django")
from .models import RefreshTokenStore, BlacklistedToken
from multiRole.authentication import MultiRoleJWTAuthentication
from jwt_utils import create_jwt
from rest_framework.permissions import AllowAny
from rest_framework import serializers, generics, status
from multiRole.permissions import EmployeeDetailsPermission
from admin_master.models import StatusMaster
from .utils import DynamicPDFGenerator
from django.db import transaction
from .utils import DynamicPDFGenerator, send_pdf_view_link

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Employee-Registration']))
class EmployeeRegisterAPIView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = EmployeeRegisterSerializer(
            data=request.data, 
            context={"request": request}
        )

        if not serializer.is_valid():
            logger.warning(f"Validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                employee = serializer.save()

            return Response({
                "message": "Employee registered successfully",
                "emp_id": getattr(employee, "emp_id", None),
                "role": getattr(employee, "auth_user").role,  # or employee.role if exists
                "name": employee.full_name,
                "profile_image": employee.profile_image_url
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.exception("Employee registration failed")
            return Response(
                {"status": False, "error": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Employee_list']))
class EmployeeListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        try:
            role = request.query_params.get("role")

            model_map = {
                "manager": Manager_register,
                "team_head": TeamHead_register,
                "executive": Executive_register,
            }

            try:
                deleted_status = StatusMaster.objects.get(status_type="Deleted")
                active_status = StatusMaster.objects.get(status_type="Active")
                inactive_status = StatusMaster.objects.get(status_type="Inactive")
            except StatusMaster.DoesNotExist:
                return Response(
                    {
                        "status": False,
                        "message": "Required status not configured"
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            paginator = self.pagination_class()

            # ---------------------------------------------------
            # CASE 1: Specific employee type
            # ---------------------------------------------------
            if role:
                model = model_map.get(role)

                if not model:
                    return Response(
                        {
                            "status": False,
                            "message": "Invalid employee type",
                            "allowed_types": list(model_map.keys()),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                queryset = (
                    model.objects
                    .select_related(
                        "auth_user",
                        "auth_user__aadhaar_details",
                        "status",
                        "city",
                        "state",
                        "reporting_to"
                    )
                    .prefetch_related(
                        "auth_user__bank_accounts"
                    )
                    .exclude(status=deleted_status)
                    .order_by("-created_at")
                )

                active_count = queryset.filter(status=active_status).count()
                inactive_count = queryset.filter(status=inactive_status).count()

                page = paginator.paginate_queryset(queryset, request)
                serializer = EmployeeReadSerializer(page, many=True)

                return paginator.get_paginated_response({
                    "status": True,
                    "active_count": active_count,
                    "inactive_count": inactive_count,
                    "data": serializer.data,
                })

            # ---------------------------------------------------
            # CASE 2: ALL employees
            # ---------------------------------------------------

            manager_qs = (
                    Manager_register.objects
                    .select_related(
                        "auth_user",
                        "auth_user__aadhaar_details",
                        "status",
                        "city",
                        "state",
                        "reporting_to"
                    )
                    .prefetch_related(
                        "auth_user__bank_accounts"
                    )
                    .exclude(status=deleted_status)
                )

            team_head_qs = (
                    TeamHead_register.objects
                    .select_related(
                        "auth_user",
                        "auth_user__aadhaar_details",
                        "status",
                        "city",
                        "state",
                        "reporting_to"
                    )
                    .prefetch_related(
                        "auth_user__bank_accounts"
                    )
                    .exclude(status=deleted_status)
                )

            executive_qs = (
                    Executive_register.objects
                    .select_related(
                        "auth_user",
                        "auth_user__aadhaar_details",
                        "status",
                        "city",
                        "state",
                        "reporting_to"
                    )
                    .prefetch_related(
                        "auth_user__bank_accounts"
                    )
                    .exclude(status=deleted_status)
                )

            # Active / Inactive counts
            active_count = (
                manager_qs.filter(status=active_status).count() +
                team_head_qs.filter(status=active_status).count() +
                executive_qs.filter(status=active_status).count()
            )

            inactive_count = (
                manager_qs.filter(status=inactive_status).count() +
                team_head_qs.filter(status=inactive_status).count() +
                executive_qs.filter(status=inactive_status).count()
            )

            combined_queryset = list(chain(manager_qs, team_head_qs, executive_qs))
            combined_queryset.sort(key=lambda x: x.created_at, reverse=True)

            page = paginator.paginate_queryset(combined_queryset, request)
            serializer = EmployeeReadSerializer(page, many=True)

            return paginator.get_paginated_response({
                "status": True,
                "active_count": active_count,
                "inactive_count": inactive_count,
                "data": serializer.data,
            })

        except Exception as e:
            logger.exception(
                "Error while fetching employee list | user_id=%s",
                request.user.id
            )
            return Response(
                {
                    "status": False,
                    "message": "Something went wrong while fetching employee data",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
@method_decorator(name='get', decorator=swagger_auto_schema(tags=['EmployeeDetails_by_id']))
class EmployeeDetailsById(APIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    permission_classes = [EmployeeDetailsPermission]

    def get(self, request, role, pk):
        model_map = {
            "manager": Manager_register,
            "team_head": TeamHead_register,
            "executive": Executive_register,
        }

        model = model_map.get(role)
        if not model:
            logger.warning(f"Invalid employee_type '{role}' requested by user {request.user.id}")
            return Response({
                "status":False,
                "error": "Invalid employee type"
            },
            status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            employee = (
                model.objects
                .select_related(
                    "auth_user",
                    "auth_user__aadhaar_details",
                    "status",
                    "city",
                    "state",
                    "reporting_to"
                )
                .prefetch_related(
                    "auth_user__bank_accounts"
                )
                .get(pk=pk)
            )
        except model.DoesNotExist:
            return Response(
                {
                    "status":False,
                    "error": "Employee Not Found"
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        self.check_object_permissions(request, employee)

        serializer = EmployeeReadSerializer(employee)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Employee profile']))   
class EmployeeProfileAPIView(APIView):
    authentication_classes = [MultiRoleJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = request.user

        # Validation: Ensure employee exists
        if not employee:
            logger.warning("Invalid token: employee not found")
            return Response({
                "status": False,
                "error": "Invalid token or employee not found"
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Validation: Check employee status (optional)
        if hasattr(employee, "status") and employee.status.status_type != "Active":
            logger.warning(f"Inactive employee {employee.id} tried to access profile")

            return Response({
                "status": False,
                "error": "Employee is not active"
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeReadSerializer(employee)
        return Response({
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Employee Status']))
class AdminEmployeeStatusAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    FRONTEND_ALLOWED_STATUSES = ["Active", "Inactive", "on-Hold"]

    def patch(self, request, role, pk):
        role = role.lower()

        model_map = {
            "manager": Manager_register,
            "team_head": TeamHead_register,
            "executive": Executive_register,
        }

        model = model_map.get(role)
        if not model:
            return Response(
                {"status": False, "error": "Invalid role"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            employee = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response(
                {"status": False, "error": f"{role} not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        status_type = request.data.get("status_type")

        if not status_type:
            return Response(
                {"status": False, "error": "status_type is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # validate from choices
        if status_type not in self.FRONTEND_ALLOWED_STATUSES:
            return Response(
                {
                    "status": False,
                    "error": f"Invalid status. Allowed values: {self.FRONTEND_ALLOWED_STATUSES}"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        status_obj, _ = StatusMaster.objects.get_or_create(
            status_type=status_type
        )

        employee.status = status_obj
        employee.save(update_fields=["status"])

        return Response(
            {
                "status": True,
                "message": f"{role.capitalize()} status updated",
                "new_status": status_type
            },
            status=status.HTTP_200_OK
        )
    
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Employee-update by id']))
class EmployeeupdateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AdminJWTAuthentication]


    def patch(self, request, role, pk):

        ROLE_MODEL_MAP = {
            "manager": Manager_register,
            "team_head": TeamHead_register,
            "executive": Executive_register,
        }
        
        model = ROLE_MODEL_MAP.get(role.lower())
        if not model:
            return Response({
                "message": "Invalid employee type"
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            employee =  model.objects.get(id=pk)
        except model.DoesNotExist:
            return Response({
                "message": "Employee not found"
            },
            status=status.HTTP_404_NOT_FOUND)
        
        if not employee.status or employee.status.status_type != 'Active':
            return Response({
                "message": "Employee can be updated only when status is Active"
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        # Get serializer dynamically
        SerializerClass = get_employee_update_serializer(model)

        serializers = SerializerClass(
            employee,
            data=request.data, 
            partial=True,
            context={"request":request}
        )

        serializers.is_valid(raise_exception=True)
        if request.user:
            employee.updated_by = str(request.user.email)
        serializers.save()

        return Response({
            "message": "Employee updated successfully",
            "data": EmployeeReadSerializer(employee).data
        })
    
@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Employee-delete']))
class EmployeeDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [AdminJWTAuthentication]

    MODEL_MAP = {
        "manager": Manager_register,
        "team_head": TeamHead_register,
        "executive": Executive_register
    }

    def delete(self, request, role, pk):
        model = self.MODEL_MAP.get(role.lower())
        if not model:
            return Response({
                "message": "Invalid employee type"
            },
            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            employee = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response({
                "message": "Employee not found"
            },
            status=status.HTTP_404_NOT_FOUND)
        
        try:
            deleted_status = StatusMaster.objects.get(status_type="Deleted")
        except StatusMaster.DoesNotExist:
            return Response({
                "message": "Deleted status not configured"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        employee.status = deleted_status
        employee.updated_by = request.user.email
        employee.save(update_fields=[
            'status',
            "updated_by",
            "updated_at"
            ])
        return Response({
            "message":"Employee deleted succsessfully",
            
        },
        status=status.HTTP_200_OK)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Download-PDF']))
class EmployeePDFAPIView(APIView):
    def get(self, request):
        deleted_status_id = StatusMaster.objects.get(status_type='Deleted').id

        manager_qs = Manager_register.objects.all().exclude(status=deleted_status_id).iterator()
        team_head_qs = TeamHead_register.objects.all().exclude(status=deleted_status_id).iterator()
        executive_qs = Executive_register.objects.all().exclude(status=deleted_status_id).iterator()

        def build_list(qs, role):
            return [{
                "Full Name": obj.full_name,
                "Email": obj.email_address,
                "Contact Number": obj.mobile_no,
                "Role": role,
                "Joining Date": obj.joining_date,
                "City": obj.city
            } for obj in qs]

        combined_list = (
            build_list(manager_qs, "Manager") +
            build_list(team_head_qs, "Team Head") +
            build_list(executive_qs, "Executive")
        )

        if not combined_list:
            return Response({"message": "No employees found"}, status=204)

        # Add Serial No dynamically
        combined_list_with_sn = [
        {"S.No.": idx, **emp} for idx, emp in enumerate(combined_list, start=1)
        ]

        pdf_generator = DynamicPDFGenerator(
            combined_list_with_sn,
            title="All Employees Report"
        )
        # IMPORTANT: open in browser, not download
        response = pdf_generator.generate_pdf()
        response["Content-Disposition"] = 'inline; filename="employees.pdf"'
        return response
    
@method_decorator(name='get', decorator=swagger_auto_schema(tags=['sendEmail PDF Link']))
class SendEmployeePDFEmailAPIView(APIView):
    authentication_classes = (AdminJWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        pdf_url = request.build_absolute_uri("/manager/employeePDF/")

        send_pdf_view_link(
            email=request.user.email,
            pdf_url=pdf_url,
            user_name=request.user.full_name
        )

        return Response({
            "message": "Employee PDF link sent to email successfully"
        },
        status=status.HTTP_200_OK)
    