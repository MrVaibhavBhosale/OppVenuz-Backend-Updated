from django.urls import path
from .views import (
    EmployeeRegisterAPIView,
    EmployeeListAPIView, 
    EmployeeDetailsById,
    EmployeeProfileAPIView,
    AdminEmployeeStatusAPIView,
    EmployeeupdateAPIView,
    EmployeeDeleteAPIView,
    EmployeePDFAPIView,
    SendEmployeePDFEmailAPIView,
)

urlpatterns = [
    path("employee/register/", EmployeeRegisterAPIView.as_view(), name="employee-register"),
    path("employeeDetails/", EmployeeListAPIView.as_view(), name="get-employee-details"),
    path("employeeDetailsById/<str:role>/<int:pk>/", EmployeeDetailsById.as_view(), name="get-emp-details-by-id"),
    path("employeeProfile/", EmployeeProfileAPIView.as_view(), name="employee-profile"),
    path("employee_status/<str:role>/<int:pk>/", AdminEmployeeStatusAPIView.as_view(), name="employee-status"),
    path("employee_update/<str:role>/<int:pk>/", EmployeeupdateAPIView.as_view(), name="update-employee"),
    path("employee_delete/<str:role>/<int:pk>/", EmployeeDeleteAPIView.as_view(), name="delete-employee"),
    path("employeePDF/", EmployeePDFAPIView.as_view(), name="employee-pdf"),
    path("sendEmailPDF/", SendEmployeePDFEmailAPIView.as_view(), name="send-email"),
]