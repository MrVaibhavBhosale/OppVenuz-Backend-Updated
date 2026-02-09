from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import ValidationError, NotFound
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
import logging
from django.contrib.auth.hashers import make_password
from rest_framework.views import APIView
from drf_yasg import openapi
from .utils import get_status, generate_reset_token, verify_reset_token, get_reporting_list_by_role
from vendor.utils import(
    send_email, get_status_count
 )
from utilities.constants import (
        FORGOT_PASSWORD_URL
)
from manager.pagination import StandardResultsSetPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
import boto3
from decouple import config
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from admin_master.authentication import AdminJWTAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from jwt_utils import create_jwt
from vendor.models import Vendor_registration
from django.db.models.functions import TruncDate, ExtractYear, ExtractMonth, ExtractWeek
from django.db.models import Count
from rest_framework import status as http_status
from django.http import Http404


from .models import (
    Role_master, 
    Service_master, 
    Best_suited_for, 
    State_master, 
    Payment_type,
    document_type,
    City_master,
    Article_type,
    Delivery_option,
    Best_deal,
    App_version,
    StatusMaster,
    CakeMaster,
    CompanyTypeMaster,
    VenueTypeMaster,
    OppvenuzChoiceMaster,
    GstMaster,
    OnboardingScreens,
    Social_media_master,
    Terms_and_condition_master,
    Oppvenuz_ques_ans_master,
    CompanyDocumentMapping,
    AdminUser,
    AdminRefreshTokenStore,
    BlacklistedAdminAccessToken,
    EmploymentType,
    WorkMode,
    TentativeBudget,
    CelebrityProfession,
    Language,
    CommissionMaster,
    PreferredEventType,
    MessageTemplate,
    TaskType,
    VendorResponse,
    TaskStatus,
    ReasonForTask,
    LeadSource,
)
 
from .serializers import (
    RoleMasterSerializer, 
    ServiceSerializer, 
    BestSuitedForSerializer, 
    StateSerializer, 
    PaymentTypeSerializer,
    document_typeSerializer,
    CitySerializer,
    ArticleTypeSerializer,
    DeliveryOptionSerializer,
    BestDealSerializer,
    AppVersionSerializer,
    CakeMasterSerializer,
    CompanyTypeMasterSerializer,
    VenueTypeMasterSerializer,
    OppvenuzChoiceMasterSerializer,
    GstMasterSerializer,
    OnboardingScreenSerializer,
    SocialMediaSerializer,
    TermsConditionSerializer,
    QuestionAnswerSerializer,
    CompanyDocumentMappingSerializer,
    AdminLoginSerializer,
    AddAdminSerializer,
    UpdateAdminSerializer,
    AdminLogoutSerializer,
    EmploymentTypeSerializer,
    WorkModeSerializer,
    TentativeBudgetSerializer,
    CelebrityProfessionSerializer,
    LanguageSerializer,
    CommissionMasterSerializer,
    ForgotPasswordRequestSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    MessageTemplateSerializer,
    TaskTypeSerializer,
    VendorResponseSerializer,
    TaskStatusSerializer,
    ReasonForTaskSerializer,
    LeadSourceSerializer,
    VendorListSerializer,
    VendorStatusUpdateSerializer

)
from rest_framework.pagination import PageNumberPagination

logger = logging.getLogger("django")

logger = logging.getLogger(__name__)
AdminUser = get_user_model()

# ------------------ ADMIN ROLES -----------------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Roles']))
class RoleCreateView(generics.CreateAPIView):    
    queryset = Role_master.objects.all()
    serializer_class = RoleMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        role_name = serializer.validated_data.get('role_name')
        if Role_master.objects.filter(role_name__iexact=role_name, status__in=[1,2]).exists():
         raise ValidationError({"role_name": f"'{role_name}' already exists and is active."})

        if role_name and not role_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid role name: {role_name}")
            raise ValidationError({"role_name": "Role name must contain only letters and spaces."})

        serializer.save(created_by=user_fullname, updated_by=user_fullname)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            "status": True,
            "message": "Role created successfully",
            "data": response.data
        }, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Roles']))
class RoleListView(generics.ListAPIView):
    serializer_class = RoleMasterSerializer
    # permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Role_master.objects.filter(status=1).order_by('-id')
        role = self.request.query_params.get('role_name', None)
        if role:
            queryset = queryset.filter(role_name__icontains=role)
            if not queryset.exists():
                logger.warning(f"{role} no such role exists")
                raise ValidationError({"role_name": f"{role} no such role exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Roles fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Roles']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Roles']))
class RoleUpdateView(generics.UpdateAPIView):
    queryset = Role_master.objects.filter(status=1)
    serializer_class = RoleMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        role_name = data.get('role_name', None)

        if role_name and not role_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid role name: {role_name}")
            raise ValidationError({"role_name": "Role name must contain only letters and spaces."})

        updated_by = getattr(user, "fullname", user.user_fullname)
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Role updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Roles']))
class RoleDeleteView(generics.DestroyAPIView):
    queryset = Role_master.objects.filter(status=1)
    serializer_class = RoleMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Role deleted successfully."},status=status.HTTP_200_OK)
        except Role_master.DoesNotExist:
            logger.warning(f"Role ID {kwargs.get('id')} not found")
            return Response({"error": "Role not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error deleting role: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ----------------------- ADMIN BEST SUITED FOR -----------------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Best Suited For']))
class BestSuitedForCreateView(generics.CreateAPIView):
    queryset = Best_suited_for.objects.all()
    serializer_class = BestSuitedForSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        name = data.get('name', None) 
        if name and not name.replace(' ', '').isalpha():
            raise ValidationError({"name": "Name must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        best_suited = serializer.validated_data.get('name')
        if Best_suited_for.objects.filter(name__iexact=best_suited, status__in=[1,2]).exists():
         raise ValidationError({"name": f"'{name}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Best Suited created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Best Suited For']))
class BestSuitedForListView(generics.ListAPIView):
    serializer_class = BestSuitedForSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Best_suited_for.objects.filter(status=1).order_by('-id')
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
            if not queryset.exists():
                logger.warning(f"{name} no such name exists")
                raise ValidationError({"name": f"{name} no such name exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Best Suited fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Best Suited For']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Best Suited For']))
class BestSuitedForUpdateView(generics.UpdateAPIView):
    queryset = Best_suited_for.objects.filter(status=1)
    serializer_class = BestSuitedForSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        name = data.get('name', None)
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        if name and not name.replace(' ', '').isalpha():
            logger.warning(f"Invalid name: {name}")
            raise ValidationError({"name": "Name must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Best Suited updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Best Suited For']))
class BestSuitedForDeleteView(generics.DestroyAPIView):
    queryset = Best_suited_for.objects.filter(status=1)
    serializer_class = BestSuitedForSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Name deleted successfully."},status=status.HTTP_200_OK)
        except Best_suited_for.DoesNotExist:
            logger.warning(f"Name ID {kwargs.get('id')} not found")
            return Response({"error": "Name not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting Name: {str(e)}")
            return Response({"error": str(e)}, status=500)

#  ---------------------- ADMIN STATE ---------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin State']))
class StateCreateView(generics.CreateAPIView):
    queryset = State_master.objects.all()
    serializer_class = StateSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        state_name = data.get('state_name', None) 
        if state_name and not state_name.replace(' ', '').isalpha():
            raise ValidationError({"state_name": "State Name must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        state = serializer.validated_data.get('state_name')
        if State_master.objects.filter(state_name__iexact=state, status__in=[1,2]).exists():
         raise ValidationError({"state": f"'{state}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "State created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin State']))
class StateListView(generics.ListAPIView):
    serializer_class = StateSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = State_master.objects.filter(status=1).order_by('-id')
        state_name = self.request.query_params.get('state_name', None)
        if state_name:
            queryset = queryset.filter(state_name__icontains=state_name)
            if not queryset.exists():
                logger.warning(f"{state_name} no such State exists")
                raise ValidationError({"state_name": f"{state_name} no such name exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "State fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin State']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin State']))
class StateUpdateView(generics.UpdateAPIView):
    queryset = State_master.objects.filter(status=1)
    serializer_class = StateSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        state_name = data.get('state_name', None)
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        if state_name and not state_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid state name: {state_name}")
            raise ValidationError({"state_name": "State Name must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "State updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin State']))
class StateDeleteView(generics.DestroyAPIView):
    queryset = State_master.objects.filter(status=1)
    serializer_class = StateSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            #  Check if any city is linked to this state
            if City_master.objects.filter(state=instance, status=1).exists():
                return Response(
                    {"error": "Cannot delete this state because it is linked with one or more cities."},
                    status=400
                )
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "State deleted successfully."},status=status.HTTP_200_OK)
        except State_master.DoesNotExist:
            logger.warning(f"State ID {kwargs.get('id')} not found")
            return Response({"error": "State not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting State: {str(e)}")
            return Response({"error": str(e)}, status=500)

#  ----------------------- ADMIN CITY ----------------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin City']))
class CityCreateView(generics.CreateAPIView):
    queryset = City_master.objects.all()
    serializer_class = CitySerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        city_name = data.get('city_name', None) 
        if city_name and not city_name.replace(' ', '').isalpha():
            raise ValidationError({"city_name": "City Name must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        city = serializer.validated_data.get('city_name')
        if City_master.objects.filter(city_name__iexact=city, status__in=[1,2]).exists():
         raise ValidationError({"city_name": f"'{city_name}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "City created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


city_list_parameters = [
    openapi.Parameter(
        'state_id', 
        in_=openapi.IN_QUERY, # Specifies that the parameter is passed in the URL query string
        type=openapi.TYPE_INTEGER, 
        required=False,       # Marks it as required in the Swagger UI
        description='State ID used to filter the cities.'
    ),
    openapi.Parameter(
        'city_name', 
        in_=openapi.IN_QUERY, 
        type=openapi.TYPE_STRING, 
        required=False, 
        description='Optional. Search query to filter cities by name (case-insensitive).'
    ),
]

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin City'], manual_parameters=city_list_parameters 
))

class CityListView(generics.ListAPIView):
    serializer_class = CitySerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = City_master.objects.filter(status=1).order_by('-id')

        state_id = self.request.query_params.get('state_id')
        if state_id:
            queryset = queryset.filter(state_id=state_id)
            if not queryset.exists():
                logger.warning(f"No cities found for state_id={state_id}")
                raise ValidationError({
                    "state_id": f"No cities found for this state_id ({state_id})"
                })

        city_name = self.request.query_params.get('city_name')
        if city_name:
            queryset = queryset.filter(city_name__icontains=city_name)
            if not queryset.exists():
                logger.warning(
                    f"{city_name} no such city exists"
                    + (f" in state_id={state_id}" if state_id else "")
                )
                raise ValidationError({
                    "city_name": f"{city_name} no such city exists"
                })

        return queryset

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Cities fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin City']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin City']))
class CityUpdateView(generics.UpdateAPIView):
    queryset = City_master.objects.filter(status=1)
    serializer_class = CitySerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        city_name = data.get('city_name', None)
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        if city_name and not city_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid city name: {city_name}")
            raise ValidationError({"city_name": "City Name must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "City updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin City']))
class CityDeleteView(generics.DestroyAPIView):
    queryset = City_master.objects.filter(status=1)
    serializer_class = CitySerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "City deleted successfully."},status=status.HTTP_200_OK)
        except City_master.DoesNotExist:
            logger.warning(f"City ID {kwargs.get('id')} not found")
            return Response({"error": "City not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting City: {str(e)}")
            return Response({"error": str(e)}, status=500)


# ------------------- ADMIN PAYMENT TYPE ---------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Payment Types']))
class PaymentTypeCreateView(generics.CreateAPIView):
    queryset = Payment_type.objects.all()
    serializer_class = PaymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        payment_type = data.get('payment_type', None) 
        if payment_type and not payment_type.replace(' ', '').isalpha():
            raise ValidationError({"payment_type": "Payment Type must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        payment_type = serializer.validated_data.get('payment_type')
        if Payment_type.objects.filter(payment_type__iexact=payment_type, status__in=[1,2]).exists():
         raise ValidationError({"payment_type": f"'{payment_type}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Payment Type created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Payment Types']))
class PaymentTypeListView(generics.ListAPIView):
    serializer_class = PaymentTypeSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Payment_type.objects.filter(status=1).order_by('-id')
        payment_type = self.request.query_params.get('payment_type', None)
        if payment_type:
            queryset = queryset.filter(payment_type__icontains=payment_type)
            if not queryset.exists():
                logger.warning(f"{payment_type} no such payment type exists")
                raise ValidationError({"payment_type": f"{payment_type} no such payment type exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Payment Types fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Payment Types']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Payment Types']))
class PaymentTypeUpdateView(generics.UpdateAPIView):
    queryset = Payment_type.objects.filter(status=1)
    serializer_class = PaymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        payment_type = data.get('payment_type', None)
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        if payment_type and not payment_type.replace(' ', '').isalpha():
            logger.warning(f"Invalid payment type: {payment_type}")
            raise ValidationError({"payment_type": "payment type must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Payment Type updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Payment Types']))
class PaymentTypeDeleteView(generics.DestroyAPIView):
    queryset = Payment_type.objects.filter(status=1)
    serializer_class = PaymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Payment Type deleted successfully."},status=status.HTTP_200_OK)
        except Payment_type.DoesNotExist:
            logger.warning(f"Payment type ID {kwargs.get('id')} not found")
            return Response({"error": "payment type not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting Payment type: {str(e)}")
            return Response({"error": str(e)}, status=500)

# -------------- ADMIN SERVICES ----------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Services']))
class ServiceCreateView(generics.CreateAPIView):
    queryset = Service_master.objects.all()
    serializer_class = ServiceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
 
    def perform_create(self, serializer):
        user = self.request.user
        created_by = getattr(user, "email", user.username)
        serializer.save(created_by=created_by, updated_by=created_by)
 
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
 
        return Response(
            {
                "status": True,
                "message": "Service created successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
@method_decorator(name="get", decorator=swagger_auto_schema(tags=["Admin Services"]))
class ServiceListView(generics.ListAPIView):
    serializer_class = ServiceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
 
    def get_queryset(self):
        return Service_master.objects.filter(status__in=[1, 2]).order_by("-id")
 
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
 
        return Response(
            {
                "status": True,
                "count": queryset.count(),
                "data": serializer.data,
                "message": "Service list fetched successfully.",
            },
            status=status.HTTP_200_OK,
        )
@method_decorator(name="put", decorator=swagger_auto_schema(tags=["Admin Services"]))
class ServiceUpdateView(generics.UpdateAPIView):
    queryset = Service_master.objects.filter(status__in=[1, 2])
    serializer_class = ServiceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
 
    def perform_update(self, serializer):
        user = self.request.user
        updated_by = getattr(user, "email", user.username)
        serializer.save(updated_by=updated_by)
 
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
 
        return Response(
            {
                "status": True,
                "message": "Service updated successfully.",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
@method_decorator(name="delete", decorator=swagger_auto_schema(tags=["Admin Services"]))
class ServiceDeleteView(generics.DestroyAPIView):
    queryset = Service_master.objects.filter(status__in=[1, 2])
    serializer_class = ServiceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
 
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status = 3
        instance.updated_by = getattr(request.user, "email", request.user.username)
        instance.save(update_fields=["status", "updated_by", "updated_at"])
 
        return Response(
            {
                "status": True,
                "message": "Service deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )
        
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Document Services']))
class DocumentTypeCreateView(generics.CreateAPIView):
    queryset = document_type.objects.all()
    serializer_class = document_typeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
        document_type = serializer.validated_data.get('document_type')
        if document_type.objects.filter(document_type__iexact=document_type, status__in=[1,2]).exists():
         raise ValidationError({"document_type": f"'{document_type}' already exists and is active."})
        logger.info(f"Document created by user {user_fullname} with data: {self.request.data}")
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Document Type created successfully", "data": response.data}, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Document Services']))
class DocumentTypeListView(generics.ListAPIView):
    serializer_class = document_typeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = document_type.objects.filter(status=1)
        doc_type = self.request.query_params.get('document_type', None)
        if doc_type:
            queryset = queryset.filter(document_type__icontains=doc_type)
            if not queryset.exists():
                logger.warning(f"{doc_type} no such document type exists")
                raise ValidationError({"document_type": f"{doc_type} no such document type exists"})
        logger.info(f"Document list fetched by user {self.request.user}")
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Document Types fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Document Services']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Document Services']))
class DocumentTypeUpdateView(generics.UpdateAPIView):
    queryset = document_type.objects.filter(status=1)
    serializer_class = document_typeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        doc_type_name = data.get('document_type', None)
        if doc_type_name and not doc_type_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid document_type name: {doc_type_name}")
            raise ValidationError({"document_type": "Document type must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
        logger.info(f"Document ID {self.get_object().id} updated by user {updated_by}")
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Document Types updated successfully", "data": response.data}, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Document Services']))
class DocumentTypeDeleteView(generics.DestroyAPIView):
    queryset = document_type.objects.filter(status=1)
    serializer_class = document_typeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.status = 3  
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            logger.info(f"Document ID {instance.id} soft deleted by user {user}")
            return Response({"status": True,"message": "Document deleted successfully."},status=status.HTTP_200_OK)
        except document_type.DoesNotExist:
            logger.warning(f"Document ID {kwargs.get('pk')} not found for delete")
            return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#  ----------------------- ADMIN ARTICLE TYPE ----------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Article Types']))
class ArticleTypeCreateView(generics.CreateAPIView):
    queryset = Article_type.objects.filter(status=1)
    serializer_class = ArticleTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        article_type = data.get('article_type', None) 
        if article_type and not article_type.replace(' ', '').isalpha():
            raise ValidationError({"article_type": "Article Type must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        article_type = serializer.validated_data.get('article_type')
        if Article_type.objects.filter(article_type__iexact=article_type, status__in=[1,2]).exists():
         raise ValidationError({"article_type": f"'{article_type}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Article type created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Article Types']))
class ArticleTypeListView(generics.ListAPIView):
    serializer_class = ArticleTypeSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Article_type.objects.filter(status=1).order_by('-id')
        article_type = self.request.query_params.get('article_type', None)
        if article_type:
            queryset = queryset.filter(article_type__icontains=article_type)
            if not queryset.exists():
                logger.warning(f"{article_type} no such article type exists")
                raise ValidationError({"article_type": f"{article_type} no such article type exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Article Types fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Article Types']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Article Types']))
class ArticleTypeUpdateView(generics.UpdateAPIView):
    queryset = Article_type.objects.filter(status=1)
    serializer_class = ArticleTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
        article_type = data.get('article_type', None)

        if article_type and not article_type.replace(' ', '').isalpha():
            logger.warning(f"Invalid article type: {article_type}")
            raise ValidationError({"article_type": "article type must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Article Types updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Article Types']))
class ArticleTypeDeleteView(generics.DestroyAPIView):
    queryset = Article_type.objects.filter(status=1)
    serializer_class = ArticleTypeSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Article Type deleted successfully."},status=status.HTTP_200_OK)
        except Article_type.DoesNotExist:
            logger.warning(f"Article type ID {kwargs.get('id')} not found")
            return Response({"error": "article type not found"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error deleting article type: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


#  -------------------- ADMIN DELIVERY OPTION ----------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Delivery Option']))
class DeliveryOptionCreateView(generics.CreateAPIView):
    queryset = Delivery_option.objects.all()
    serializer_class = DeliveryOptionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        delivery_option = data.get('delivery_option', None) 
        if delivery_option and not delivery_option.replace(' ', '').isalpha():
            raise ValidationError({"delivery_option": "Delivery Option must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        delivery_option = serializer.validated_data.get('delivery_option')
        if Delivery_option.objects.filter(delivery_option__iexact=delivery_option, status__in=[1,2]).exists():
         raise ValidationError({"delivery_option": f"'{delivery_option}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Delivery Option created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Delivery Option']))
class DeliveryOptionListView(generics.ListAPIView):
    serializer_class = DeliveryOptionSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Delivery_option.objects.filter(status=1).order_by('-id')
        delivery_option = self.request.query_params.get('delivery_option', None)
        if delivery_option:
            queryset = queryset.filter(delivery_option__icontains=delivery_option)
            if not queryset.exists():
                logger.warning(f"{delivery_option} no such delivery option exists")
                raise ValidationError({"delivery_option": f"{delivery_option} no such delivery option exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Delivery Options fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Delivery Option']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Delivery Option']))
class DeliveryOptionUpdateView(generics.UpdateAPIView):
    queryset = Delivery_option.objects.filter(status=1)
    serializer_class = DeliveryOptionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
        delivery_option = data.get('delivery_option', None)

        if delivery_option and not delivery_option.replace(' ', '').isalpha():
            logger.warning(f"Invalid delivery option: {delivery_option}")
            raise ValidationError({"delivery_option": "delivery option must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Delivery Options updated successfully", "data": response.data}, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Delivery Option']))
class DeliveryOptionDeleteView(generics.DestroyAPIView):
    queryset = Delivery_option.objects.filter(status=1)
    serializer_class = DeliveryOptionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Delivery Option deleted successfully."},status=status.HTTP_200_OK)
        except Delivery_option.DoesNotExist:
            logger.warning(f"Delivery Option ID {kwargs.get('id')} not found")
            return Response({"error": "delivery option not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting delivery option: {str(e)}")
            return Response({"error": str(e)}, status=500)



# ----------------------- ADMIN BEST DEAL ------------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Best Deal']))
class BestDealCreateView(generics.CreateAPIView):
    queryset = Best_deal.objects.filter(status=1)
    serializer_class = BestDealSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        deal_name = data.get('deal_name', None) 
        if deal_name and not deal_name.replace(' ', '').isalpha():
            raise ValidationError({"deal_name": "Deal Name must contain only letters and spaces."})
            
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        deal_name = serializer.validated_data.get('deal_name')
        if Best_deal.objects.filter(deal_name__iexact=deal_name, status__in=[1,2]).exists():
         raise ValidationError({"deal_name": f"'{deal_name}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "Best Deal created successfully", "data": response.data}, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Best Deal']))
class BestDealListView(generics.ListAPIView):
    serializer_class = BestDealSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Best_deal.objects.filter(status=1).order_by('-id')
        deal_name = self.request.query_params.get('deal_name', None)
        if deal_name:
            queryset = queryset.filter(deal_name__icontains=deal_name)
            if not queryset.exists():
                logger.warning(f"{deal_name} no such deal name exists")
                raise ValidationError({"deal_name": f"{deal_name} no such deal name exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Best Deal fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Best Deal']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Best Deal']))
class BestDealUpdateView(generics.UpdateAPIView):
    queryset = Best_deal.objects.filter(status=1)
    serializer_class = BestDealSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        deal_name = data.get('deal_name', None)
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 

        if deal_name and not deal_name.replace(' ', '').isalpha():
            logger.warning(f"Invalid Deal name: {deal_name}")
            raise ValidationError({"deal_name": "deal name must contain only letters and spaces."})

        updated_by = user_fullname
        serializer.save(updated_by=updated_by)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Best Deal updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Best Deal']))
class BestDealDeleteView(generics.DestroyAPIView):
    queryset = Best_deal.objects.filter(status=1)
    serializer_class = BestDealSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.status = 3
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Deal Name deleted successfully."},status=status.HTTP_200_OK)
        except Best_deal.DoesNotExist:
            logger.warning(f"Deal ID {kwargs.get('id')} not found")
            return Response({"error": "deal name not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting deal name: {str(e)}")
            return Response({"error": str(e)}, status=500)


# --------------------------- ADMIN APP VERSION ---------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin App Version']))
class AppVersionCreateView(generics.CreateAPIView):
    queryset = App_version.objects.filter(status=1)
    serializer_class = AppVersionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        app_version = data.get('app_version', None) 
        user_fullname = (
            getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "email", None)
            or getattr(self.request.user, "username", None)  
        ) 
        app_version = serializer.validated_data.get('app_version')
        if App_version.objects.filter(app_version__iexact=app_version, status__in=[1,2]).exists():
         raise ValidationError({"app_version": f"'{app_version}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": "App version created successfully", "data": response.data}, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin App Version']))
class AppVersionListView(generics.ListAPIView):
    serializer_class = AppVersionSerializer
    permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = App_version.objects.filter(status=1).order_by('-id')
        app_version = self.request.query_params.get('app_version', None)
        if app_version:
            queryset = queryset.filter(app_version__icontains=app_version)
            if not queryset.exists():
                logger.warning(f"{app_version} no such app version exists")
                raise ValidationError({"app_version": f"{app_version} no such app version exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "App Version fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin App Version']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin App Version']))
class AppVersionUpdateView(generics.UpdateAPIView):
    queryset = App_version.objects.filter(status=1)
    serializer_class = AppVersionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        user_fullname = (
            getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "email", None)
            or getattr(self.request.user, "username", None)  
        ) 
        app_version = data.get('app_version', None)
        serializer.save(updated_by=user_fullname)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "App Version updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin App Version']))
class AppVersionDeleteView(generics.DestroyAPIView):
    queryset = App_version.objects.filter(status=1)
    serializer_class = AppVersionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "App Version deleted successfully."},status=status.HTTP_200_OK)
        except App_version.DoesNotExist:
            logger.warning(f"Version ID {kwargs.get('id')} not found")
            return Response({"error": "app version not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting app version: {str(e)}")
            return Response({"error": str(e)}, status=500)


# -------------------------- ADMIN Base API ----------------------------------

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Base API']))
class BaseAPIView(APIView):
    permission_classes = [AllowAny]
    # authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            # ------------------- Base Data -------------------
            appVersion = AppVersionSerializer(App_version.objects.filter(status=1), many=True).data
            states = StateSerializer(State_master.objects.filter(status=1), many=True).data
            categories = ServiceSerializer(Service_master.objects.filter(status=1), many=True).data
            documents = document_typeSerializer(document_type.objects.filter(status=1), many=True).data
            company_types = CompanyTypeMaster.objects.filter(status__status_type='Active')

            # ------------------- Onboarding -------------------
            gif = OnboardingScreens.objects.filter(status=1, type=1).order_by("-created_at").first()
            flash_screens = OnboardingScreens.objects.filter(status=1, type=2).order_by("order")[:3]

            onboarding_data = {
                "gif": OnboardingScreenSerializer(gif).data if gif else None,
                "flash_screens": OnboardingScreenSerializer(flash_screens, many=True).data,
            }

            # ------------------- Add Cities under States -------------------
            for state in states:
                state_id = state.get('id')
                cities = City_master.objects.filter(state_id=state_id, status=1).values('id', 'city_name', 'status', 'latitude', 'longitude')
                state['cities'] = list(cities)

            # ------------------- Company Types with Documents -------------------
            company_data = []
            for company in company_types:
                mappings = CompanyDocumentMapping.objects.filter(company_type=company, status=1).select_related('document_type')
                mapped_docs = [
                    {
                        'id': m.document_type.id,
                        'document_type': m.document_type.document_type
                    } for m in mappings
                ]
                company_data.append({
                    'id': company.id,
                    'company_type': company.company_type,
                    'documents': mapped_docs
                })

            # ------------------- NEW: GST & Best Suited For -------------------
            gst_list = GstMasterSerializer(
                GstMaster.objects.filter(status__status_type='Active').order_by('gst_percentage'),
                many=True
            ).data

            best_suited_for_list = BestSuitedForSerializer(
                Best_suited_for.objects.filter(status=1).order_by('name'),
                many=True
            ).data

            # ------------------- ✅ Terms & Conditions -------------------
            terms_conditions = TermsConditionSerializer(
                Terms_and_condition_master.objects.filter(status=1).order_by('-created_at'),
                many=True
            ).data


            # ------------------- Final Response -------------------
            data = {
                "status": True,
                "message": "Base API Data fetched successfully",
                "data": {
                    "appVersion": appVersion,
                    "states": states,
                    "categories": categories,
                    "company_type_documents": company_data,
                    "gst": gst_list,
                    "best_suited_for": best_suited_for_list,
                    "terms_and_conditions": terms_conditions,  
                    "onboarding": onboarding_data,
                }
            }
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in BaseAPIView: {str(e)}")
            return Response({
                "status": False,
                "message": "Failed to fetch Base API Data",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# ---------------- Helper function ----------------
def get_status(status_type):
    try:
        return StatusMaster.objects.get(status_type=status_type)
    except StatusMaster.DoesNotExist:
        logger.error(f"Status '{status_type}' does not exist.")
        raise ValidationError({"status": f"Status '{status_type}' not found."})

# ------------------ CAKES ------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['cakes']))
class CakeCreateView(generics.CreateAPIView):
    queryset = CakeMaster.objects.all()
    serializer_class = CakeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        active_status = get_status('Active')
        serializer.save(status=active_status)
        logger.info("New cake created successfully")


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['cakes']))
class CakeListView(generics.ListAPIView):
    serializer_class = CakeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        active_status = get_status('Active')
        queryset = CakeMaster.objects.filter(status=active_status).order_by('-id')

        flavor = self.request.query_params.get('flavor')
        shape = self.request.query_params.get('shape_name')
        cake_type = self.request.query_params.get('cake_type')

        if flavor:
            queryset = queryset.filter(flavor__iexact=flavor)
        if shape:
            queryset = queryset.filter(shape_name__iexact=shape)
        if cake_type:
            queryset = queryset.filter(cake_type__iexact=cake_type)

        if not queryset.exists():
            logger.warning("No cakes found for the applied filters")
            raise ValidationError({"detail": "No cakes found for the given filters"})
        return queryset


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['cakes']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['cakes']))
class CakeUpdateView(generics.UpdateAPIView):
    queryset = CakeMaster.objects.all()
    serializer_class = CakeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())
        logger.info(f"Cake ID {self.get_object().id} updated successfully")


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['cakes']))
class CakeDeleteView(generics.DestroyAPIView):
    queryset = CakeMaster.objects.all()
    serializer_class = CakeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_status = get_status('Deleted')
        instance.status = deleted_status
        instance.save(update_fields=['status', 'updated_at'])
        logger.info(f"Cake ID {instance.id} deleted successfully")
        return Response({"status": True,"message": "Cake deleted successfully"}, status=status.HTTP_200_OK)

# ------------------ COMPANY TYPE ------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['company-type']))
class CompanyTypeCreateView(generics.CreateAPIView):
    queryset = CompanyTypeMaster.objects.all()
    serializer_class = CompanyTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        name = self.request.data.get('company_type')
        active_status = get_status('Active')
        if CompanyTypeMaster.objects.filter(company_type=name, status=active_status).exists():
            raise ValidationError({"company_type": "This company type already exists"})
        serializer.save(status=active_status)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['company-type']))
class CompanyTypeListView(generics.ListAPIView):
    serializer_class = CompanyTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        active_status = get_status('Active')
        return CompanyTypeMaster.objects.filter(status=active_status).order_by('-id')


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['company-type']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['company-type']))
class CompanyTypeUpdateView(generics.UpdateAPIView):
    queryset = CompanyTypeMaster.objects.all()
    serializer_class = CompanyTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['company-type']))
class CompanyTypeDeleteView(generics.DestroyAPIView):
    queryset = CompanyTypeMaster.objects.all()
    serializer_class = CompanyTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_status = get_status('Deleted')
        instance.status = deleted_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response({"status": True,"message": "Company type deleted successfully"}, status=status.HTTP_200_OK)

# ------------------ VENUE TYPE ------------------
@method_decorator(name='get', decorator=swagger_auto_schema(tags=['venue-type']))
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['venue-type']))
class VenueTypeListCreateView(generics.ListCreateAPIView):
    serializer_class = VenueTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        active_status = get_status('Active')
        return VenueTypeMaster.objects.filter(status=active_status).order_by('-id')

    def perform_create(self, serializer):
        name = self.request.data.get('venue_type')
        active_status = get_status('Active')
        if VenueTypeMaster.objects.filter(venue_type=name, status=active_status).exists():
            raise ValidationError({"venue_type": "This venue type already exists"})
        serializer.save(status=active_status)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['venue-type']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['venue-type']))
class VenueTypeUpdateView(generics.UpdateAPIView):
    queryset = VenueTypeMaster.objects.all()
    serializer_class = VenueTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def perform_update(self, serializer):
        serializer.save(updated_at=timezone.now())


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['venue-type']))
class VenueTypeDeleteView(generics.DestroyAPIView):
    queryset = VenueTypeMaster.objects.all()
    serializer_class = VenueTypeMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_status = get_status('Deleted')
        instance.status = deleted_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response({"status": True,"message": "Venue type deleted successfully"}, status=status.HTTP_200_OK)

# ------------------ OPPVENUZ CHOICE ------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['OPPVENUZ CHOICE']))
class OppvenuzChoiceCreateView(APIView):
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OppvenuzChoiceMasterSerializer(data=request.data)
        if serializer.is_valid():
            active_status = get_status('Active')
            serializer.save(status=active_status)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['OPPVENUZ CHOICE']))
class OppvenuzChoiceListView(APIView):
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        if pk:
            obj = get_object_or_404(OppvenuzChoiceMaster, pk=pk)
            serializer = OppvenuzChoiceMasterSerializer(obj)
            return Response(serializer.data)
        active_status = get_status('Active')
        objs = OppvenuzChoiceMaster.objects.filter(status=active_status).order_by('-id')
        serializer = OppvenuzChoiceMasterSerializer(objs, many=True)
        return Response(serializer.data)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['OPPVENUZ CHOICE']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['OPPVENUZ CHOICE']))
class OppvenuzChoiceUpdateView(APIView):
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        obj = get_object_or_404(OppvenuzChoiceMaster, pk=pk)
        serializer = OppvenuzChoiceMasterSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_at=timezone.now())
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        obj = get_object_or_404(OppvenuzChoiceMaster, pk=pk)
        serializer = OppvenuzChoiceMasterSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_at=timezone.now())
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['OPPVENUZ CHOICE']))
class OppvenuzChoiceDeleteView(APIView):
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        obj = get_object_or_404(OppvenuzChoiceMaster, pk=pk)
        deleted_status = get_status('Deleted')
        obj.status = deleted_status
        obj.save(update_fields=['status', 'updated_at'])
        return Response({"status": True,"message": "Choice deleted successfully"}, status=status.HTTP_200_OK)

# ------------------ GST ------------------

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['GST']))
class GstMasterCreateView(generics.CreateAPIView):
    queryset = GstMaster.objects.all()
    serializer_class = GstMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['GST']))
class GstMasterListView(generics.ListAPIView):
    serializer_class = GstMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GstMaster.objects.filter(status__status_type__in=['Active', 'Inactive']).order_by('-id')

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['GST']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['GST']))
class GstMasterUpdateView(generics.UpdateAPIView):
    queryset = GstMaster.objects.all()
    serializer_class = GstMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'pk'

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['GST']))
class GstMasterDeleteView(generics.DestroyAPIView):
    queryset = GstMaster.objects.all()
    serializer_class = GstMasterSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_status = get_status('Deleted')
        instance.status = deleted_status
        instance.save(update_fields=['status', 'updated_at'])
        return Response({"status": True,"message": "GST deleted successfully"}, status=status.HTTP_200_OK)
    
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Social Media'])) 
class SocialMediaUploadView(generics.CreateAPIView):
    queryset = Social_media_master.objects.all()
    serializer_class = SocialMediaSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        media_name = request.data.get("media_name")
        if media_name:
            media_name = media_name.strip().strip('"')

        image = request.FILES.get("media_image")

        if not media_name or not image:
            logger.warning("Missing media_name or media_image in upload request.")
            return Response(
                {
                    "message": "Both media_name and media_image are required.",
                    "status": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if Social_media_master.objects.filter(media_name__iexact=media_name, status__in=[1,2]).exists():
            return Response(
                {"message": f"Social media '{media_name}' already exists.", "status": False},
                status=status.HTTP_400_BAD_REQUEST
            )

        max_size_mb = 5
        if image.size > max_size_mb * 1024 * 1024:
            logger.warning(f"File too large: {image.size / (1024 * 1024):.2f} MB")
            return Response(
                {
                    "message": f"Maximum file size is {max_size_mb} MB.",
                    "status": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_extensions = (".png", ".jpg", ".jpeg", ".svg", ".webp")
        ext = image.name.lower().rsplit(".", 1)[-1]
        if f".{ext}" not in valid_extensions:
            logger.warning(f"Unsupported file extension: .{ext}")
            return Response(
                {
                    "message": f"Unsupported file extension. Allowed: {', '.join(valid_extensions)}",
                    "status": False
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        s3 = boto3.client(
            "s3",
            aws_access_key_id=config("s3AccessKey"),
            aws_secret_access_key=config("s3Secret"),
        )

        filename = f"{image.name}"
        key = f"social_media/{filename}"
        bucket = config("S3_BUCKET_NAME")

        try:
            s3.upload_fileobj(
                Fileobj=image,
                Bucket=bucket,
                Key=key,
                ExtraArgs={"ACL": "public-read", "ContentType": image.content_type},
            )
        except Exception as e:
            logger.error(f"Failed to upload image to S3: {str(e)}")
            return Response(
                {
                    "message": "Failed to upload image.",
                    "error": str(e),
                    "status": False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        media_url = f"https://{bucket}.s3.amazonaws.com/{key}"

        serializer = self.get_serializer(data={
            "media_name": media_name,
            "media_image": media_url
        })
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                "message": "Social media uploaded successfully.",
                "data": serializer.data,
                "status": True
            },
            status=status.HTTP_201_CREATED
        )

    def perform_create(self, serializer):
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        serializer.save(
            created_by=user_fullname,
            updated_by=user_fullname
        )

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Social Media']))
class SocialMediaList(generics.ListAPIView):
    queryset = Social_media_master.objects.all()
    serializer_class = SocialMediaSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Social_media_master.objects.filter(status__in=[1,2]).order_by("media_name")

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)

            if not queryset.exists():
                return Response(
                    {
                        "message": "No social media records found.",
                        "data": [],
                        "status": True
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {
                    "message": "Social media list fetched successfully.",
                    "data": serializer.data,
                    "status": True
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching social media list: {str(e)}")
            return Response(
                {
                    "message": "Failed to fetch social media list.",
                    "error": str(e),
                    "status": False
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Social Media']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Social Media']))
class SocialMediaUpdateView(generics.UpdateAPIView):
    serializer_class = SocialMediaSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [AdminJWTAuthentication]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = "id"

    def get_queryset(self):
        return Social_media_master.objects.filter(status__in=[1, 2])

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        data = request.data.copy()
        data.pop("media_image", None)

        serializer = self.get_serializer(
            instance,
            data=data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        # Safe updated_by
        user = request.user
        updated_by = (
            getattr(user, "fullname", None)
        )

        media_file = request.FILES.get("media_image")

        if media_file:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret"),
            )
            bucket = config("S3_BUCKET_NAME")

            key = f"social_media/{media_file.name}"

            s3.upload_fileobj(
                media_file,
                bucket,
                key,
                ExtraArgs={
                    "ACL": "public-read",
                    "ContentType": getattr(media_file, "content_type", "image/jpeg"),
                },
            )

            serializer.save(
                media_image=f"https://{bucket}.s3.amazonaws.com/{key}",
                updated_by=updated_by,
            )
        else:
            serializer.save(updated_by=updated_by)

        return Response(
            {
                "status": True,
                "message": "Social media updated successfully",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )  

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Social Media']))
class SocialMediaDeleteView(generics.DestroyAPIView):
    queryset = Social_media_master.objects.all()
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            old_url = instance.media_image
            if old_url and config("S3_BUCKET_NAME") in old_url:
                s3 = boto3.client(
                    "s3",
                    aws_access_key_id=config("s3AccessKey"),
                    aws_secret_access_key=config("s3Secret"),
                )
                bucket = config("S3_BUCKET_NAME")
                old_key = old_url.split(f"https://{bucket}.s3.amazonaws.com/")[-1]
                s3.delete_object(Bucket=bucket, Key=old_key)

            instance.delete()

            return Response({"status": True,"message": "Deleted successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"status": False,"message": f"Deletion failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Terms & Conditions']))
class TermsAndConditionsView(generics.CreateAPIView):
    queryset = Terms_and_condition_master.objects.all()
    serializer_class = TermsConditionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]    

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        title = serializer.validated_data.get('title')
        content = serializer.validated_data.get('content')

        if Terms_and_condition_master.objects.filter(
            title__iexact=title,
            content__iexact=content,
            status__in=[1, 2]  
        ).exists():
            raise ValidationError("This Terms & Conditions already exists.")

        self.perform_create(serializer)

        return Response(
            {
                "message": "Terms & Conditions created successfully",
                "data": serializer.data,
                "status": True
            },
            status=status.HTTP_201_CREATED
        )

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Terms & Conditions']))
class TermsAndConditionsListView(generics.ListAPIView):
    serializer_class = TermsConditionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        try:
            queryset = Terms_and_condition_master.objects.filter(status__in=[1, 2])
            return queryset
        except Exception as e:
            logger.error(f"Error fetching Terms and Conditions list: {str(e)}", exc_info=True)
            return Terms_and_condition_master.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(
                {
                    "status": True,
                    "message": "Terms & Conditions fetched successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error('error', "Unexpected error in Terms & Conditions list API", exc=e)
            return Response(
                {"status": True,"message": "Failed to fetch Terms & Conditions."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Terms & Conditions']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Terms & Conditions']))
class TermsAndConditionsUpdateView(generics.UpdateAPIView):
    queryset = Terms_and_condition_master.objects.filter(status__in=[1,2])
    serializer_class = TermsConditionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)

            user = request.user
            user_fullname = (
                getattr(self.request.user, "email", None)
                or getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "username", None)  
            ) 
            title = serializer.validated_data.get('title')
            content = serializer.validated_data.get('content')

            duplicate = Terms_and_condition_master.objects.filter(
                title__iexact=title,
                content__iexact=content,
                status__in=[1, 2]
            ).exclude(id=instance.id)

            if duplicate.exists():
                logger.warning(f"Duplicate Terms & Conditions found for title '{title}' by '{user_fullname}'")
                raise ValidationError("A Terms & Conditions with the same title and content already exists.")

            instance = serializer.save(updated_by=user_fullname)

            return Response({
                "status": True,
                "message": "Terms & Conditions updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error during Terms update: {str(e)}", exc_info=True)
            return Response(
                {"status": False,"message": "An unexpected error occurred."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Terms & Conditions']))
class TermsAndConditionsDeleteView(generics.DestroyAPIView):
    queryset = Terms_and_condition_master.objects.filter(status__in=[1, 2])  
    serializer_class = TermsConditionSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def delete(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user_fullname = (
                getattr(self.request.user, "email", None)
                or getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "username", None)  
            ) 

            instance.status = 3
            instance.updated_by = user_fullname
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])

            return Response(
                {"message": "Terms & Conditions soft-deleted successfully", "status": True},
                status=status.HTTP_200_OK
            )

        except Terms_and_condition_master.DoesNotExist:
            return Response(
                {"message": "Terms & Conditions not found or already deleted", "status": False},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Unexpected error while soft deleting Terms & Conditions: {str(e)}", exc_info=True)
            return Response(
                {"message": "An unexpected error occurred", "status": False},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['service Registration charges']))
class GetRegistrationChargeView(APIView):
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    def get(self, request, id, *args, **kwargs):
        try:
            service = Service_master.objects.get(id=id, status__in=[1, 2])
            return Response({
                "service_name": service.service_name,
                "registration_charges": service.registration_charges
            }, status=status.HTTP_200_OK)
        except Service_master.DoesNotExist:
            return Response(
                {"error": "Service not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

# ------------------- OPPVENUZ QUESTION ANSWER ---------------------------
@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Admin Oppvenuz Question Answer']))
class QuestionAnswerCreateView(generics.CreateAPIView):
    queryset = Oppvenuz_ques_ans_master.objects.all()
    serializer_class = QuestionAnswerSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        question = data.get('question', None)  
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        question = serializer.validated_data.get('question')
        if Oppvenuz_ques_ans_master.objects.filter(question__iexact=question, status__in=[1,2]).exists():
         raise ValidationError({"question": f"'{question}' already exists and is active."})
        serializer.save(created_by=user_fullname, updated_by=user_fullname)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({"status": True, "message": " created successfully", "data": response.data}, status=status.HTTP_201_CREATED)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin Oppvenuz Question Answer']))
class QuestionAnswerListView(generics.ListAPIView):
    serializer_class = QuestionAnswerSerializer
    # permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Oppvenuz_ques_ans_master.objects.filter(status=1).order_by('-id')
        question = self.request.query_params.get('question', None)
        if question:
            queryset = queryset.filter(question__icontains=question)
            if not queryset.exists():
                logger.warning(f"{question} no such Details")
                raise ValidationError({"question": f"{question} no such Details exists"})
        return queryset
    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({"status": True, "message": "Details fetched successfully", "data": serializer.data}, status=status.HTTP_200_OK)


@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin Oppvenuz Question Answer']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Admin Oppvenuz Question Answer']))
class QuestionAnswerUpdateView(generics.UpdateAPIView):
    queryset = Oppvenuz_ques_ans_master.objects.filter(status=1)
    serializer_class = QuestionAnswerSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def perform_update(self, serializer):
        user = self.request.user
        data = serializer.validated_data
        user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
        question = data.get('question', None)
        serializer.save(updated_by=user_fullname)
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response({"status": True, "message": "Details updated successfully", "data": response.data}, status=status.HTTP_200_OK)


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin Oppvenuz Question Answer']))
class QuestionAnswerDeleteView(generics.DestroyAPIView):
    queryset = Oppvenuz_ques_ans_master.objects.filter(status=1)
    serializer_class = QuestionAnswerSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            user = request.user
            instance.status = 3
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True,"message": "Details deleted successfully."},status=status.HTTP_200_OK)
        except Payment_type.DoesNotExist:
            logger.warning(f" ID {kwargs.get('id')} not found")
            return Response({"error": "not found"}, status=404)
        except Exception as e:
            logger.error(f"Error deleting: {str(e)}")
            return Response({"error": str(e)}, status=500)


class UploadOnboardingView(APIView):
    # permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def upload_to_s3(self, file_obj):
        s3 = boto3.client(
            "s3",
            aws_access_key_id=config("s3AccessKey"),
            aws_secret_access_key=config("s3Secret"),
        )
        bucket = config("S3_BUCKET_NAME")
        key = f"onboarding/{file_obj.name}"
        s3.upload_fileobj(file_obj, bucket, key, ExtraArgs={"ACL": "public-read"})
        return f"https://{bucket}.s3.amazonaws.com/{key}"

    def post(self, request):
        file = request.FILES.get("file")
        title = request.data.get("title")
        type_ = int(request.data.get("type", 2))  # 1 = GIF, 2 = Flash
        order = int(request.data.get("order", 0))

        if not file:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)

        allowed_ext = (".png", ".jpg", ".jpeg", ".gif")
        if not file.name.lower().endswith(allowed_ext):
            return Response({"error": "Invalid file type"}, status=status.HTTP_400_BAD_REQUEST)

        # Upload to S3
        file_url = self.upload_to_s3(file)
        media = {"image": file_url}

        screen = OnboardingScreens.objects.create(
            title=title,
            media=media,
            type=type_,
            order=order,
        )

        return Response(OnboardingScreenSerializer(screen).data, status=status.HTTP_201_CREATED)

class GetOnboardingFlowView(APIView):
    # permission_classes = [AllowAny]
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get(self, request):
        gif = OnboardingScreens.objects.filter(status=1, type=1).order_by("-created_at").first()
        flash_screens = OnboardingScreens.objects.filter(status=1, type=2).order_by("order")[:3]

        response = {
            "gif": OnboardingScreenSerializer(gif).data if gif else None,
            "flash_screens": OnboardingScreenSerializer(flash_screens, many=True).data,
        }
        return Response(response, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Company Document Mapping']))
class CompanyDocumentMappingCreateView(generics.CreateAPIView):
    queryset = CompanyDocumentMapping.objects.all()
    serializer_class = CompanyDocumentMappingSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user_fullname = (
            getattr(self.request.user, "email", None)
            or getattr(self.request.user, "full_name", None)
            or getattr(self.request.user, "username", None)  
        ) 
        company_type = serializer.validated_data.get('company_type')
        document_type_obj = serializer.validated_data.get('document_type')

        
        if CompanyDocumentMapping.objects.filter(
            company_type=company_type, document_type=document_type_obj, status__in=[1, 2]
        ).exists():
            raise ValidationError({"detail": "This document is already mapped with the selected company type."})

        serializer.save(created_by=user_fullname, updated_by=user_fullname)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Company Document Mapping']))
class CompanyDocumentMappingListView(generics.ListAPIView):
    serializer_class = CompanyDocumentMappingSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CompanyDocumentMapping.objects.filter(status=1).select_related('company_type', 'document_type')


@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Company Document Mapping']))
class CompanyDocumentMappingDeleteView(generics.DestroyAPIView):
    queryset = CompanyDocumentMapping.objects.filter(status=1)
    serializer_class = CompanyDocumentMappingSerializer
    authentication_classes = [AdminJWTAuthentication]  
    permission_classes = [IsAuthenticated]
    
    lookup_field = 'pk'

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            instance.status = 3  
            user_fullname = (
                getattr(self.request.user, "full_name", None)
                or getattr(self.request.user, "email", None)
                or getattr(self.request.user, "username", None)  
            ) 
            instance.updated_by = user_fullname
            instance.updated_at = timezone.now()
            instance.save(update_fields=['status', 'updated_by', 'updated_at'])
            return Response({"status": True, "message": "Mapping deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"status": False, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(name='post', decorator=swagger_auto_schema(
    tags=['Admin'],
    security=[],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["username", "password"],
        properties={
            "username": openapi.Schema(type=openapi.TYPE_STRING, example="admin@gmail.com"),
            "password": openapi.Schema(type=openapi.TYPE_STRING, example="Admin@123"),
        },
    ),
))
class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = AdminLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        try:
            user = AdminUser.objects.get(email=email)
        except AdminUser.DoesNotExist:
            return Response({"error": "Invalid credentials"}, status=400)

        if not user.check_password(password):
            return Response({"error": "Invalid credentials"}, status=400)

        # Create access + refresh tokens
        access_token  = create_jwt({"user_id": user.id, "role": user.role})
        refresh_token = create_jwt({"user_id": user.id, "role": user.role})

        # access_token  = create_jwt({"user_id": user.id, "role": user.role}, expiry_minutes=60)
        # refresh_token = create_jwt({"user_id": user.id, "role": user.role}, expiry_days=7)

        AdminRefreshTokenStore.objects.create(user=user, refresh_token=refresh_token)
        refresh = RefreshToken.for_user(user)
        token_data = {"access": access_token, "refresh": refresh_token}

        return Response(
            {
                "status": True,
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "mobile_no": user.mobile_no,
                    "role": user.role,
                    "full_name": user.full_name,
                    "profile_image": user.profile_image,
                },
                "token": token_data,
            },
            status=status.HTTP_200_OK,
        )

class AddAdminView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Admin"],
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                "email", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Admin email",
                required=False
            ),
            openapi.Parameter(
                "mobile_no", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Mobile number",
                required=False
            ),
            openapi.Parameter(
                "full_name", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Full name",
                required=False
            ),
            openapi.Parameter(
                "role", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Role",
            ),
            openapi.Parameter(
                "is_active", openapi.IN_FORM,
                type=openapi.TYPE_BOOLEAN,
                description="Activate / Deactivate admin",
                required=False
            ),
            openapi.Parameter(
                "password", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Password",
                required=True
            ),
            openapi.Parameter(
                "profile_image", openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Profile image",
                required=False
            ),
        ],
    )

    def post(self, request):
        #  Only super admin can create admins
        if request.user.role not in ["super_admin", "admin"]:
            return Response(
                {"detail": "Only super_admin can create admin users."},
                status=status.HTTP_403_FORBIDDEN
            )

        email = request.data.get("email")
        mobile_no = request.data.get("mobile_no")

        #  Duplicate email check
        if AdminUser.objects.filter(email=email, status=1).exists():
            return Response(
                {"status": False,"message": "Email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Duplicate mobile check
        if AdminUser.objects.filter(mobile_no=mobile_no, status=1).exists():
            return Response(
                {"status": False,"message": "Mobile number already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = AddAdminSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "status": True,
                "message": "Admin created successfully",
                "id": user.id,
                "admin_uid": user.admin_uid,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "profile_image": user.profile_image if user.profile_image else None,
            },
            status=status.HTTP_201_CREATED
        )

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin']))
# class GetAllAdminUsersView(APIView):
#     authentication_classes = [AdminJWTAuthentication]
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         if request.user.role not in ["super_admin", "admin"]:
#             return Response({"detail": "Only super_admin can access this API."},
#                             status=status.HTTP_403_FORBIDDEN)

#         users = AdminUser.objects.filter(
#             role__in=["super_admin", "admin"],status=1
#         ).values("id", "full_name", "email", "mobile_no", "role", "profile_image", "admin_uid")
#         return Response({"status": True,"message": "Admin users fetched successfully","data": list(users)}, status=status.HTTP_200_OK)


@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin']))
class GetAllAdminUsersView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):

        # only allowed roles
        if request.user.role not in ["super_admin", "admin"]:
            return Response(
                {"detail": "Only super_admin can access this API."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = AdminUser.objects.filter(
            role__in=["super_admin", "admin"],
            status=1
        ).values(
            "id",
            "full_name",
            "email",
            "mobile_no",
            "role",
            "profile_image",
            "admin_uid"
        ).order_by("-id")

        # ----------- pagination ----------
        paginator = PageNumberPagination()
        paginator.page_size_query_param = "page_size"   # allow ?page_size=
        paginator.page_size = 20               # default page size

        result_page = paginator.paginate_queryset(queryset, request)

        return paginator.get_paginated_response({
            "status": True,
            "message": "Admin users fetched successfully",
            "data": list(result_page)
        })

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Admin']))
class UpdateAdminUserView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        tags=["Admin"],
        consumes=["multipart/form-data"],
        manual_parameters=[
            openapi.Parameter(
                "email", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Admin email",
                required=False
            ),
            openapi.Parameter(
                "mobile_no", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Mobile number",
                required=False
            ),
            openapi.Parameter(
                "full_name", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Full name",
                required=False
            ),
            openapi.Parameter(
                "role", openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description="Role",
            ),
            openapi.Parameter(
                "is_active", openapi.IN_FORM,
                type=openapi.TYPE_BOOLEAN,
                description="Activate / Deactivate admin",
                required=False
            ),
            openapi.Parameter(
                "profile_image", openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Profile image",
                required=False
            ),
        ],
    )
    def put(self, request, id):
        if request.user.role not in ["super_admin", "admin"]:
            return Response(
                {"detail": "Only super_admin can update admin users."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = AdminUser.objects.get(id=id)
        except AdminUser.DoesNotExist:
            return Response(
                {"detail": "Admin not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UpdateAdminSerializer(
            user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "status": True,
                "message": "Admin updated successfully",
                "id": user.id,
                "admin_uid": user.admin_uid,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "profile_image": user.profile_image if user.profile_image else None,
            },
            status=status.HTTP_200_OK
        )
@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Admin']))
class DeleteAdminUserView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        if request.user.role not in ["super_admin", "admin"]:
            return Response({"detail": "Only super_admin can delete admin users."},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            user = AdminUser.objects.get(id=id)
        except AdminUser.DoesNotExist:
            return Response({"detail": "Admin not found."},
                            status=status.HTTP_404_NOT_FOUND)

        user.status = 3   
        user.save()

        return Response({"status": True,"message": "Admin deleted successfully"}, status=status.HTTP_200_OK)
@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        tags=["Admin"],
        security=[{"Bearer": []}],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["access","refresh"],
            properties={
                "access": openapi.Schema(type=openapi.TYPE_STRING, description="Access token"),
                "refresh": openapi.Schema(type=openapi.TYPE_STRING, description="Refresh token"),
            },
        ),
    ),
)

class AdminLogoutView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"error": "Refresh token missing"}, status=400)

        # Delete refresh token owned by this user
        deleted = AdminRefreshTokenStore.objects.filter(
            user=request.user,
            refresh_token=refresh
        ).delete()

        if deleted[0] == 0:
            return Response({"error": "Invalid refresh token"}, status=400)

        #  Blacklist the access token from header
        auth_header = request.headers.get("Authorization")
        if auth_header:
            try:
                token_str = auth_header.split()[1]  # Bearer <access_token>
                
                # Save token in BlacklistedAdminAccessToken
                BlacklistedAdminAccessToken.objects.create(
                    user=request.user,
                    token=token_str
                )
            except Exception:
                pass  # ignore invalid token

        return Response({"status": True,"message": "Logout successful"}, status=200)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Admin']))
class DashboardStatisticsAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    # def get(self, request):
        # Basic totals
        # total_users = AdminUser.objects.all().count()
        # total_vendors = Vendor_registration.objects.all().count()
        # total_active_vendors = Vendor_registration.objects.filter(status=1).count()
        # total_inactive_vendors = Vendor_registration.objects.filter(status=2).count()

        # Vendor service list (service_name + vendor_count if you want)
        # vendor_service_qs = Service_master.objects.all().values("service_name")
        # vendor_service_count = [
        #     {"service_name": v["service_name"]} for v in vendor_service_qs
        # ]

        # ---------- GRAPH: New users by date ----------
        # graph_data = (
        #     AdminUser.objects
        #     .annotate(date=TruncDate('created_at'))
        #     .values('date')
        #     .annotate(total=Count('id'))
        #     .order_by('date')
        # )

        # ---------- ORDERS GRAPH (if you have an orders model) ----------
        # orders_graph = []
        # if ServiceOrder is not None:
        #     orders_graph_qs = (
        #         ServiceOrder.objects
        #         .annotate(date=TruncDate('created_at'))
        #         .values('date')
        #         .annotate(total_orders=Count('id'), total_revenue=Sum('total_amount'))
        #         .order_by('date')
        #     )
        #     orders_graph = list(orders_graph_qs)
        # else:
        #     # If no orders model, return empty list (frontend will show message)
        #     orders_graph = []

        # orders_graph = [
        #     {"date": "2025-01-01", "total_orders": 12, "total_revenue": 2400},
        #     {"date": "2025-01-02", "total_orders": 18, "total_revenue": 3900},
        #     {"date": "2025-01-03", "total_orders": 9,  "total_revenue": 1500},
        #     {"date": "2025-01-04", "total_orders": 15, "total_revenue": 3100},
        #     {"date": "2025-01-05", "total_orders": 22, "total_revenue": 4500},
        # ]


        # ---------- Yearly summary (users + vendors) ----------
        # users_per_year = (
        #     AdminUser.objects
        #     .annotate(year=ExtractYear('created_at'))
        #     .values('year')
        #     .annotate(total_users=Count('id'))
        #     .order_by('year')
        # )

        # vendors_per_year = (
        #     Vendor_registration.objects
        #     .annotate(year=ExtractYear('created_at'))
        #     .values('year')
        #     .annotate(total_vendors=Count('id'))
        #     .order_by('year')
        # )

        # years = sorted(set([u['year'] for u in users_per_year] + [v['year'] for v in vendors_per_year]))
        # yearly_summary = []
        # for y in years:
        #     yearly_summary.append({
        #         "date": str(y),
        #         "total_users": next((u['total_users'] for u in users_per_year if u['year'] == y), 0),
        #         "total_vendors": next((v['total_vendors'] for v in vendors_per_year if v['year'] == y), 0),
        #     })

        # ---------- Monthly summary ----------
        # users_per_month = (
        #     AdminUser.objects
        #     .annotate(month=ExtractMonth('created_at'))
        #     .values('month')
        #     .annotate(total_users=Count('id'))
        #     .order_by('month')
        # )
        # vendors_per_month = (
        #     Vendor_registration.objects
        #     .annotate(month=ExtractMonth('created_at'))
        #     .values('month')
        #     .annotate(total_vendors=Count('id'))
        #     .order_by('month')
        # )
        # months = sorted(set([u['month'] for u in users_per_month] + [v['month'] for v in vendors_per_month]))
        # monthly_summary = [
        #     {
        #         "date": str(m),
        #         "total_users": next((u['total_users'] for u in users_per_month if u['month'] == m), 0),
        #         "total_vendors": next((v['total_vendors'] for v in vendors_per_month if v['month'] == m), 0),
        #     }
        #     for m in months
        # ]

        # # ---------- Weekly summary ----------
        # users_per_week = (
        #     AdminUser.objects
        #     .annotate(week=ExtractWeek('created_at'))
        #     .values('week')
        #     .annotate(total_users=Count('id'))
        #     .order_by('week')
        # )
        # vendors_per_week = (
        #     Vendor_registration.objects
        #     .annotate(week=ExtractWeek('created_at'))
        #     .values('week')
        #     .annotate(total_vendors=Count('id'))
        #     .order_by('week')
        # )
        # weeks = sorted(set([u['week'] for u in users_per_week] + [v['week'] for v in vendors_per_week]))
        # weekly_summary = [
        #     {
            #     "date": str(w),
            #     "total_users": next((u['total_users'] for u in users_per_week if u['week'] == w), 0),
            #     "total_vendors": next((v['total_vendors'] for v in vendors_per_week if v['week'] == w), 0),
            # }
            # for w in weeks
        # ]

        # ---------- Revenue per year (from orders) ----------
        # revenue_per_year = []
        # if ServiceOrder is not None:
        #     revenue_qs = (
        #         ServiceOrder.objects
        #         .annotate(year=ExtractYear('created_at'))
        #         .values('year')
        #         .annotate(total_revenue=Sum('total_amount'))
        #         .order_by('year')
        #     )
        #     revenue_per_year = [
        #         {"date": str(r['year']), "total_revenue": r['total_revenue'] or 0}
        #         for r in revenue_qs
        #     ]
        # else:
        #     revenue_per_year = []

        # revenue_per_year = [
        #     {"date": "2021", "total_revenue": 12000},
        #     {"date": "2022", "total_revenue": 18500},
        #     {"date": "2023", "total_revenue": 22600},
        #     {"date": "2024", "total_revenue": 31500},
        #     {"date": "2025", "total_revenue": 40200},
        # ]


        # ---------- Extra fields requested (defaults / hardcoded) ----------
        # registered_vendor_default = 10  # hardcoded default as requested

        # vendor registration by platform (use your actual field name, here I assume 'signup_source')
        # If your model does not have signup_source, these queries will be no-ops and defaults will be returned
        # try:
        #     vendor_from_android = Vendor_registration.objects.filter(signup_source__iexact='android').count()
        #     vendor_from_ios = Vendor_registration.objects.filter(signup_source__iexact='ios').count()
        #     # if both zero, fallback to default 20 each (as requested)
        #     if vendor_from_android == 0 and vendor_from_ios == 0:
        #         vendor_from_android = 20
        #         vendor_from_ios = 20
        # except Exception:
        #     vendor_from_android = 20
        #     vendor_from_ios = 20

        # Total signups for vendors (can be same as total_vendors or filtered)
        # total_signup_vendors = total_vendors

        # Recent registered vendors (limit 10)
        # recent_registered_vendors_qs = Vendor_registration.objects.order_by('-created_at')[:10]
        # recent_registered_vendors = [
        #     {
        #         "id": v.id,
        #         "vendor_name": getattr(v, "vendor_name", "") or getattr(v, "name", ""),
        #         "created_at": v.created_at
        #     } for v in recent_registered_vendors_qs
        # ]

        # response = [
        #     {
        #         "total_users": total_users,
        #         "total_vendors": total_vendors,
        #         "total_active_vendors": total_active_vendors,
        #         "total_inactive_vendors": total_inactive_vendors,
        #         "graph_data": list(graph_data),
        #         "orders_graph": orders_graph,
        #         "vendor_service_count": vendor_service_count,
        #         "year": yearly_summary,
        #         "month": monthly_summary,
        #         "week": weekly_summary,
        #         "revenue_year": revenue_per_year,
        #         "registered_vendor_default": registered_vendor_default,
        #         "vendor_from_android": vendor_from_android,
        #         "vendor_from_ios": vendor_from_ios,
        #         "total_signup_vendors": total_signup_vendors,
        #         "recent_registered_vendors": recent_registered_vendors,
        #     }
        # ]

        # return Response({"message": "Data fetched Sucessfully", "data": response}, status=status.HTTP_200_OK)

    def get(self, request):
        # Basic totals
        total_users = AdminUser.objects.all().count()
        total_vendors = Vendor_registration.objects.all().count()
        total_active_vendors = Vendor_registration.objects.filter(status=1).count()
        total_inactive_vendors = Vendor_registration.objects.filter(status=2).count()

        # Vendor service list
        vendor_service_qs = Service_master.objects.all().values("service_name")
        vendor_service_count = [
            {"service_name": v["service_name"]} for v in vendor_service_qs
        ]

        # New users by date
        graph_data_qs = (
            AdminUser.objects
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(total=Count('id'))
            .order_by('date')
        )
        graph_data = list(graph_data_qs)

        # Orders graph (if you have orders)
        # try:
        #     orders_graph_qs = (
        #         ServiceOrder.objects
        #         .annotate(date=TruncDate('created_at'))
        #         .values('date')
        #         .annotate(total_orders=Count('id'), total_revenue=Sum('total_amount'))
        #         .order_by('date')
        #     )
        #     orders_graph = list(orders_graph_qs)
        # except Exception:
        #     orders_graph = []

        # Yearly summary
        users_per_year_qs = (
            AdminUser.objects
            .annotate(year=ExtractYear('created_at'))
            .values('year')
            .annotate(total_users=Count('id'))
            .order_by('year')
        )
        vendors_per_year_qs = (
            Vendor_registration.objects
            .annotate(year=ExtractYear('created_at'))
            .values('year')
            .annotate(total_vendors=Count('id'))
            .order_by('year')
        )
        users_per_year = list(users_per_year_qs)
        vendors_per_year = list(vendors_per_year_qs)

        years = sorted(set([u['year'] for u in users_per_year] + [v['year'] for v in vendors_per_year]))
        yearly_summary = []
        for y in years:
            yearly_summary.append({
                "date": str(y),
                "total_users": next((u['total_users'] for u in users_per_year if u['year'] == y), 0),
                "total_vendors": next((v['total_vendors'] for v in vendors_per_year if v['year'] == y), 0),
            })

        # Monthly summary
        users_per_month = list(
            AdminUser.objects
            .annotate(month=ExtractMonth('created_at'))
            .values('month')
            .annotate(total_users=Count('id'))
            .order_by('month')
        )
        vendors_per_month = list(
            Vendor_registration.objects
            .annotate(month=ExtractMonth('created_at'))
            .values('month')
            .annotate(total_vendors=Count('id'))
            .order_by('month')
        )
        months = sorted(set([u['month'] for u in users_per_month] + [v['month'] for v in vendors_per_month]))
        monthly_summary = [
            {
                "date": str(m),
                "total_users": next((u['total_users'] for u in users_per_month if u['month'] == m), 0),
                "total_vendors": next((v['total_vendors'] for v in vendors_per_month if v['month'] == m), 0),
            }
            for m in months
        ]

        # Weekly summary
        users_per_week = list(
            AdminUser.objects
            .annotate(week=ExtractWeek('created_at'))
            .values('week')
            .annotate(total_users=Count('id'))
            .order_by('week')
        )
        vendors_per_week = list(
            Vendor_registration.objects
            .annotate(week=ExtractWeek('created_at'))
            .values('week')
            .annotate(total_vendors=Count('id'))
            .order_by('week')
        )
        weeks = sorted(set([u['week'] for u in users_per_week] + [v['week'] for v in vendors_per_week]))
        weekly_summary = [
            {
                "date": str(w),
                "total_users": next((u['total_users'] for u in users_per_week if u['week'] == w), 0),
                "total_vendors": next((v['total_vendors'] for v in vendors_per_week if v['week'] == w), 0),
            }
            for w in weeks
        ]

        # Revenue per year (from orders)
        try:
            # revenue_qs = (
            #     ServiceOrder.objects
            #     .annotate(year=ExtractYear('created_at'))
            #     .values('year')
            #     .annotate(total_revenue=Sum('total_amount'))
            #     .order_by('year')
            # )
            revenue_per_year = [
                {"date": str(r['year']), "total_revenue": r['total_revenue'] or 0}
                # for r in revenue_qs
            ]
        except Exception:
            # fallback sample
            revenue_per_year = [
                {"date": "2021", "total_revenue": 12000},
                {"date": "2022", "total_revenue": 18500},
                {"date": "2023", "total_revenue": 22600},
                {"date": "2024", "total_revenue": 31500},
                {"date": "2025", "total_revenue": 40200},
            ]

        # Registered vendor defaults
        registered_vendor_default = 10

        # signup platform counts
        try:
            vendor_from_android = Vendor_registration.objects.filter(signup_source__iexact='android').count()
            vendor_from_ios = Vendor_registration.objects.filter(signup_source__iexact='ios').count()
            if vendor_from_android == 0 and vendor_from_ios == 0:
                vendor_from_android = 20
                vendor_from_ios = 20
        except Exception:
            vendor_from_android = 20
            vendor_from_ios = 20

        total_signup_vendors = total_vendors

        recent_registered_vendors_qs = Vendor_registration.objects.order_by('-created_at')[:10]
        recent_registered_vendors = [
            {
                "id": v.id,
                "vendor_name": getattr(v, "vendor_name", "") or getattr(v, "name", ""),
                "created_at": v.created_at
            } for v in recent_registered_vendors_qs
        ]

        response = {
            "total_users": total_users,
            "total_vendors": total_vendors,
            "total_active_vendors": total_active_vendors,
            "total_inactive_vendors": total_inactive_vendors,
            "graph_data": graph_data,
            # "orders_graph": orders_graph,
            "vendor_service_count": vendor_service_count,
            "year": yearly_summary,
            "month": monthly_summary,
            "week": weekly_summary,
            "revenue_year": revenue_per_year,
            "registered_vendor_default": registered_vendor_default,
            "vendor_from_android": vendor_from_android,
            "vendor_from_ios": vendor_from_ios,
            "total_signup_vendors": total_signup_vendors,
            "recent_registered_vendors": recent_registered_vendors,
        }

        return Response({"status": True,"message": "Data fetched Successfully", "data": response}, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Employment Type']))
class EmploymentTypeCreateAPIView(generics.CreateAPIView):
    queryset = EmploymentType.objects.all()
    serializer_class = EmploymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        employment_type = serializer.validated_data.get('employment_type')
        code = serializer.validated_data.get('code')

        if EmploymentType.objects.filter(
            employment_type__iexact=employment_type,
            code__iexact=code,
            status__in=[1, 2]
        ).exists():
            raise ValidationError("Employment Type already exists.")

        self.perform_create(serializer)

        return Response({
            "message": "Employment Type created successfully",
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Employment Type']))
class EmploymentTypeListAPIView(generics.ListAPIView):
    serializer_class = EmploymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmploymentType.objects.filter(status__in=[1, 2]).order_by('-id')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({
            "message": "Employment Type list fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Employment Type']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Employment Type']))
class EmploymentTypeUpdateAPIView(generics.UpdateAPIView):
    queryset = EmploymentType.objects.filter(status__in=[1, 2])
    serializer_class = EmploymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        duplicate = EmploymentType.objects.filter(
            employment_type__iexact=serializer.validated_data.get('employment_type'),
            code__iexact=serializer.validated_data.get('code'),
            status__in=[1, 2]
        ).exclude(id=instance.id)

        if duplicate.exists():
            raise ValidationError("Employment Type already exists.")

        serializer.save()

        return Response({
            "message": "Employment Type updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Employment Type']))
class EmploymentTypeDeleteAPIView(generics.DestroyAPIView):
    queryset = EmploymentType.objects.filter(status__in=[1, 2])
    serializer_class = EmploymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 3
        instance.save(update_fields=['status'])

        return Response({
            "message": "Employment Type deleted successfully",
            "status": True
        }, status=status.HTTP_200_OK)

@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Employment Type']))
class EmploymentTypeStatusAPIView(generics.UpdateAPIView):
    queryset = EmploymentType.objects.all()
    serializer_class = EmploymentTypeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 2 if instance.status_id == 1 else 1
        instance.save(update_fields=['status'])

        return Response({
            "message": "Status updated successfully",
            "status": True,
            "data": {
                "id": instance.id,
                "status": instance.status_id
            }
        }, status=status.HTTP_200_OK)

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Work Mode']))
class WorkModeCreateAPIView(generics.CreateAPIView):
    queryset = WorkMode.objects.all()
    serializer_class = WorkModeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if WorkMode.objects.filter(
            work_mode_name__iexact=serializer.validated_data['work_mode_name'],
            code__iexact=serializer.validated_data['code'],
            status__in=[1, 2]
        ).exists():
            raise ValidationError("Work Mode already exists.")

        serializer.save()

        return Response({
            "message": "Work Mode created successfully",
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Work Mode']))
class WorkModeListAPIView(generics.ListAPIView):
    serializer_class = WorkModeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WorkMode.objects.filter(
            status__in=[1, 2]
        ).order_by('-id')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({
            "message": "Work Mode list fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Work Mode']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Work Mode']))
class WorkModeUpdateAPIView(generics.UpdateAPIView):
    queryset = WorkMode.objects.filter(status__in=[1, 2])
    serializer_class = WorkModeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        duplicate = WorkMode.objects.filter(
            work_mode_name__iexact=serializer.validated_data.get('work_mode_name'),
            code__iexact=serializer.validated_data.get('code'),
            status__in=[1, 2]
        ).exclude(id=instance.id)

        if duplicate.exists():
            raise ValidationError("Work Mode already exists.")

        serializer.save()

        return Response({
            "message": "Work Mode updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Work Mode']))
class WorkModeDeleteAPIView(generics.DestroyAPIView):
    queryset = WorkMode.objects.filter(status__in=[1, 2])
    serializer_class = WorkModeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 3
        instance.save(update_fields=['status_id'])

        return Response({
            "message": "Work Mode deleted successfully",
            "status": True
        }, status=status.HTTP_200_OK)

@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Work Mode']))
class WorkModeStatusAPIView(generics.UpdateAPIView):
    queryset = WorkMode.objects.all()
    serializer_class = WorkModeSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 2 if instance.status_id == 1 else 1
        instance.save(update_fields=['status_id'])

        return Response({
            "message": "Status updated successfully",
            "status": True,
            "data": {
                "id": instance.id,
                "status": instance.status_id
            }
        }, status=status.HTTP_200_OK)

class TentativeBudgetListAPIView(APIView):

    def get(self, request):
        budgets = TentativeBudget.objects.filter(is_active=True).order_by("sort_order")
        serializer = TentativeBudgetSerializer(budgets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CelebrityProfessionCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CelebrityProfessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    
class CelebrityProfessionListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        professions = CelebrityProfession.objects.filter(
            is_active=True
        ).order_by("name")

        serializer = CelebrityProfessionSerializer(
            professions, many=True
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

class CelebrityProfessionUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            profession = CelebrityProfession.objects.get(pk=pk)
        except CelebrityProfession.DoesNotExist:
            return Response(
                {"detail": "Profession not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = CelebrityProfessionSerializer(
            profession, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )

class CelebrityProfessionDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            profession = CelebrityProfession.objects.get(pk=pk)
        except CelebrityProfession.DoesNotExist:
            return Response(
                {"detail": "Profession not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        profession.is_active = False
        profession.updated_by = request.user
        profession.save()

        return Response(
            {"detail": "Profession deleted successfully"},
            status=status.HTTP_200_OK
        )

@method_decorator(name='post', decorator=swagger_auto_schema(tags=['Language']))
class LanguageCreateAPIView(generics.CreateAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if Language.objects.filter(
            language_name__iexact=serializer.validated_data['language_name'],
            code__iexact=serializer.validated_data['code'],
            status__in=[1, 2]
        ).exists():
            raise ValidationError("Language already exists.")

        serializer.save()

        return Response({
            "message": "Language created successfully",
            "status": True,
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

@method_decorator(name='get', decorator=swagger_auto_schema(tags=['Language']))
class LanguageListAPIView(generics.ListAPIView):
    serializer_class = LanguageSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Language.objects.filter(
            status__in=[1, 2]
        ).order_by('-id')

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response({
            "message": "Language list fetched successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='put', decorator=swagger_auto_schema(tags=['Language']))
@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Language']))
class LanguageUpdateAPIView(generics.UpdateAPIView):
    queryset = Language.objects.filter(status__in=[1, 2])
    serializer_class = LanguageSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        duplicate = Language.objects.filter(
            language_name__iexact=serializer.validated_data.get('language_name'),
            code__iexact=serializer.validated_data.get('code'),
            status__in=[1, 2]
        ).exclude(id=instance.id)

        if duplicate.exists():
            raise ValidationError("Language already exists.")

        serializer.save()

        return Response({
            "message": "Language updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

@method_decorator(name='delete', decorator=swagger_auto_schema(tags=['Language']))
class LanguageDeleteAPIView(generics.DestroyAPIView):
    queryset = Language.objects.filter(status__in=[1, 2])
    serializer_class = LanguageSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 3
        instance.save(update_fields=['status_id'])

        return Response({
            "message": "Language deleted successfully",
            "status": True
        }, status=status.HTTP_200_OK)

@method_decorator(name='patch', decorator=swagger_auto_schema(tags=['Language']))
class LanguageStatusAPIView(generics.UpdateAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def patch(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.status_id = 2 if instance.status_id == 1 else 1
        instance.save(update_fields=['status_id'])

        return Response({
            "message": "Status updated successfully",
            "status": True,
            "data": {
                "id": instance.id,
                "status": instance.status_id
            }
        }, status=status.HTTP_200_OK)

# admin_master/views.py

class CommissionCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = CommissionMasterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Commission created", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommissionListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        qs = CommissionMaster.objects.all().order_by("-id")
        serializer = CommissionMasterSerializer(qs, many=True)
        return Response({"data": serializer.data})


class CommissionUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    def put(self, request, pk):
        try:
            obj = CommissionMaster.objects.get(pk=pk)
        except CommissionMaster.DoesNotExist:
            return Response({"message": "Not found"}, status=404)

        serializer = CommissionMasterSerializer(obj, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Updated", "data": serializer.data})
        return Response(serializer.errors, status=400)


class ForgotPasswordRequestView(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = ForgotPasswordRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = AdminUser.objects.get(email=email, is_active=True)
        except AdminUser.DoesNotExist:
            logger.warning(
                "Forgot password requested for non-existing user | email=%s",
                email
            )
            return Response({
                "message": "Admin user not found"
            },
            status=status.HTTP_200_OK
            )
        
        token = generate_reset_token(email)
        print("EMAIL FROM TOKEN:", token)
        #reset_url = f"{FORGOT_PASSWORD_URL}/{token}/{email}"
        reset_url = "http://localhost:3000/set-password" + f"/{token}/{email}"


        send_email(
            recipient=email,
            data_dict={
                    "user_name": user.full_name,
                    "reset_link": reset_url,
            }
        )

        return Response(
            {
                "message": "reset password link has been sent successfully to your email."
            },
            status=status.HTTP_200_OK
        )
    

class ResetPasswordView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    serializer_class = ResetPasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        email = verify_reset_token(token)

        if not email:
            logger.warning(
                "Password reset failed: invalid or expired token"
            )
            return Response({
                "error": "Invalid or expired reset link"
            },
            status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = AdminUser.objects.get(email=email, is_active=True)
        except AdminUser.DoesNotExist:
            logger.warning(
                "Password reset failed: user not found | email=%s",
                email
            )
            return Response({
                "error": "user Not Found"
            },
            status=status.HTTP_200_OK
        )

        user.set_password(new_password)
        user.updated_by = email
        user.save(update_fields=[
            "password",
            "updated_by",
            "updated_at"
            ])

        return Response(
            {
                "message": "Password reset successfully"
            },
            status=status.HTTP_200_OK
        )

class ChangePasswordView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (AdminJWTAuthentication,)
    serializer_class = ChangePasswordSerializer

    def put(self, request):
        user = request.user
        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Change password validation failed | user=%s | errors=%s",
                user.email,
                serializer.errors
            )
            return Response(
                {"status": False, "error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            logger.warning(
                "Change password failed: incorrect old password | user=%s",
                user.email
            )
            return Response(
                {"status": False, "error": "Old password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.updated_by = user.email
        user.save(update_fields=[
            "password",
            "updated_by",
            "updated_at"
        ])

        return Response(
            {"status": True, "message": "Password changed successfully"},
            status=status.HTTP_200_OK
        )


class AdminBaseAPIView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            employment = EmploymentTypeSerializer(EmploymentType.objects.filter(status=1), many=True).data
            workmode = WorkModeSerializer(WorkMode.objects.filter(status=1), many=True).data
            states = StateSerializer(State_master.objects.filter(status=1),many=True).data
            cities = City_master.objects.filter(status=1).values(
                "id", "city_name", "state_id"
            )

             # Map cities to their states
            city_map = {}
            for city in cities:
                city_map.setdefault(city["state_id"], []).append({
                    "id": city["id"],
                    "city_name": city["city_name"]
                })

            # Attach cities under each state
            for state in states:
                state["cities"] = city_map.get(state["id"], [])

            return Response({
                "message": "base APi fetched successfully.",
                "data": {
                    "employment": employment,
                    "work_mode": workmode,
                    "state": state,
                }
            },
            status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error in baseApi: {str(e)}")
            return Response({
                "status": False,
                "message": "Failed to fetch Base API Data",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExecutiveBaseAPIView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            commission = CommissionMasterSerializer(CommissionMaster.objects.filter(status=1), many=True).data
            states = StateSerializer(State_master.objects.filter(status=1),many=True).data
            cities = City_master.objects.filter(status=1).values(
                "id", "city_name", "state_id"
            )

             # Map cities to their states
            city_map = {}
            for city in cities:
                city_map.setdefault(city["state_id"], []).append({
                    "id": city["id"],
                    "city_name": city["city_name"]
                })

            # Attach cities under each state
            for state in states:
                state["cities"] = city_map.get(state["id"], [])

            return Response({
                "status": True,
                "message": "",
                "data": {
                    "states": states,
                    "commition_type": commission
                }
            })
        
        except Exception as e:
            return Response({
                "status": False,
                "message": "Failed to fetch Base API Data",
                "error": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class MessageTemplateCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MessageTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MessageTemplateListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        templates = MessageTemplate.objects.filter(is_active=True)
        serializer = MessageTemplateSerializer(templates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MessageTemplateUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        try:
            template = MessageTemplate.objects.get(pk=pk)
        except MessageTemplate.DoesNotExist:
            return Response(
                {"detail": "Template not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = MessageTemplateSerializer(
            template, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MessageTemplateDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            template = MessageTemplate.objects.get(pk=pk)
        except MessageTemplate.DoesNotExist:
            return Response(
                {"detail": "Template not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        template.is_active = False
        template.updated_by = request.user
        template.save()

        return Response(
            {"detail": "Template deleted successfully"},
            status=status.HTTP_200_OK
        )

class ReportingListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    """
    Returns id & name list based on selected role
    """

    def get(self, request):
        role = request.query_params.get("role")

        if not role:
            return Response(
                {"message": "role query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = get_reporting_list_by_role(role)

        return Response(
            {
                "success": True,
                "data": data
            },
            status=status.HTTP_200_OK
        )

class TaskTypeCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TaskTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskTypeListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TaskType.objects.filter(is_active=True)
        serializer = TaskTypeSerializer(qs, many=True)
        return Response(serializer.data)

class TaskTypeUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            obj = TaskType.objects.get(pk=pk)
        except TaskType.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        serializer = TaskTypeSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class TaskTypeDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = TaskType.objects.get(pk=pk)
        except TaskType.DoesNotExist:
            return Response({"detail": "Not found"}, status=404)

        obj.is_active = False
        obj.updated_by = request.user
        obj.save()
        return Response({"detail": "Deleted successfully"})

class VendorResponseCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VendorResponseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VendorResponseListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VendorResponse.objects.filter(is_active=True)
        serializer = VendorResponseSerializer(qs, many=True)
        return Response(serializer.data)

class VendorResponseUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            obj = VendorResponse.objects.get(pk=pk)
        except VendorResponse.DoesNotExist:
            return Response({"detail": "Vendor response not found"}, status=404)

        serializer = VendorResponseSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class VendorResponseDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = VendorResponse.objects.get(pk=pk)
        except VendorResponse.DoesNotExist:
            return Response({"detail": "Vendor response not found"}, status=404)

        obj.is_active = False
        obj.updated_by = request.user
        obj.save()
        return Response({"detail": "Vendor response deleted successfully"})

class TaskStatusCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TaskStatusSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskStatusListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = TaskStatus.objects.filter(is_active=True)
        serializer = TaskStatusSerializer(qs, many=True)
        return Response(serializer.data)

class TaskStatusUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            obj = TaskStatus.objects.get(pk=pk)
        except TaskStatus.DoesNotExist:
            return Response({"detail": "Task status not found"}, status=404)

        serializer = TaskStatusSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class TaskStatusDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = TaskStatus.objects.get(pk=pk)
        except TaskStatus.DoesNotExist:
            return Response({"detail": "Task status not found"}, status=404)

        obj.is_active = False
        obj.updated_by = request.user
        obj.save()
        return Response({"detail": "Task status deleted successfully"})

class ReasonForTaskCreateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReasonForTaskSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ReasonForTaskListAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = ReasonForTask.objects.filter(is_active=True)
        serializer = ReasonForTaskSerializer(qs, many=True)
        return Response(serializer.data)

class ReasonForTaskUpdateAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            obj = ReasonForTask.objects.get(pk=pk)
        except ReasonForTask.DoesNotExist:
            return Response({"detail": "Reason not found"}, status=404)

        serializer = ReasonForTaskSerializer(obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class ReasonForTaskDeleteAPIView(APIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            obj = ReasonForTask.objects.get(pk=pk)
        except ReasonForTask.DoesNotExist:
            return Response({"detail": "Reason not found"}, status=404)

        obj.is_active = False
        obj.updated_by = request.user
        obj.save()
        return Response({"detail": "Reason deleted successfully"})

class LeadSourceCreateAPIView(generics.CreateAPIView):
    queryset = LeadSource.objects.all()
    serializer_class = LeadSourceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {
                "status": True,
                "message": "Lead source created successfully",
                "data": response.data
            },
            status=status.HTTP_201_CREATED
        )

class LeadSourceListAPIView(generics.ListAPIView):
    serializer_class = LeadSourceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LeadSource.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                "status": True,
                "message": "Lead source list fetched successfully",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )
    
class LeadSourceUpdateAPIView(generics.UpdateAPIView):
    queryset = LeadSource.objects.filter(is_active=True)
    serializer_class = LeadSourceSerializer
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(
            {
                "status": True,
                "message": "Lead source updated successfully",
                "data": response.data
            },
            status=status.HTTP_200_OK
        )
    
class LeadSourceDeleteAPIView(generics.DestroyAPIView):
    queryset = LeadSource.objects.filter(is_active=True)
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()

        return Response(
            {
                "status": True,
                "message": "Lead source deleted successfully"
            },
            status=status.HTTP_200_OK
        )

class VendorListAPIView(generics.ListAPIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = VendorListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Vendor_registration.objects.select_related(
            "city_id", "service_id", "status").exclude(
                status__status_type="Deleted"
        )

        city = self.request.query_params.get("city")
        service = self.request.query_params.get("service")
        search = self.request.query_params.get("search")

        if city:
            if city.isdigit():
                queryset = queryset.filter(city_id=int(city))
            else:
                queryset = queryset.filter(city_id__city_name__icontains=city.strip())

        if service:
            if service.isdigit():
                queryset = queryset.filter(service_id=int(service))
            else:
                queryset = queryset.filter(service_id__service_name__icontains=service.strip())

        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search.strip()) |
                Q(business_name__icontains=search.strip())
            )

        return queryset.order_by("created_at")
    
    def list(self, request, *args, **kwargs):
        logger.warning(f"Vendor list API | Params: {request.query_params}")
        queryset = self.get_queryset()

        #optional filtering
        profile_status = request.GET.get("profile_status")
        status = request.GET.get("status")

        if profile_status:
            queryset = queryset.filter(profile_status=profile_status)
      
        if status:
            queryset = queryset.filter(status__status_type=status)

        status_count = get_status_count(self.get_queryset())

        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)

        paginated_responce = self.get_paginated_response(serializer.data)
        paginated_responce.data["status_count"] = status_count

        return paginated_responce
    
class VendorStatusUpdateView(generics.UpdateAPIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = VendorStatusUpdateSerializer
    queryset = Vendor_registration.objects.all()
    lookup_field = 'id'

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            vendor_id = self.kwargs.get("id")
            logger.warning(f"Vendor not found | vendor_id={vendor_id}")
            raise NotFound("Vendor not found")

    def perform_update(self, serializer):
        serializer.save(
            updated_by=self.request.user.email
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        return Response(
            {
                "message": "Vendor status updated successfully",
                "data": response.data
            },
            status=status.HTTP_200_OK
        )


class VendorDeleteAPIView(generics.DestroyAPIView):
    authentication_classes = [AdminJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Vendor_registration.objects.all()
    lookup_field = "id"

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            vendor_id = self.kwargs.get("id")
            logger.warning(f"Vendor Not Found | vendor_id={vendor_id}")
            raise NotFound("Vendor Not Found")
        
    def destroy(self, request, *args, **kwargs):
        vendor = self.get_object()

        try:
            deleted_status = StatusMaster.objects.get(status_type="Deleted")
        except StatusMaster.DoesNotExist:
            return Response({
                "message": "Deleted status not configured"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if vendor.status == deleted_status:
            raise ValidationError("Vendor already deleted")
        
        vendor.status = deleted_status
        vendor.updated_by = request.user.email
        vendor.updated_at = timezone.now()
        vendor.save(update_fields=["status", "updated_by", "updated_at"])

        return Response({
            "message": "Vendor deleted successfully"
        },
        status=status.HTTP_200_OK)

