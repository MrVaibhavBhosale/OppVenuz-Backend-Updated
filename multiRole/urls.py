from django.urls import path
from .views import (
    MultiRoleLoginView,
    MultiRoleLogoutView,
    getDailyLogsByUserView,
    DownloadDailyLogsView,
    ExecutiveTaskCreateAPIView,
    ExecutiveTaskRescheduleAPIView,
    ExecutiveTaskCompleteAPIView,
    MyTaskListAPIView,
    LeadCreateAPIView
)

urlpatterns = [
    path('login/', MultiRoleLoginView.as_view(), name="login"),
    path('logout/', MultiRoleLogoutView.as_view(), name="logout"),
    path("getDailyLogsByUser/<int:emp_id>/<str:role>/", getDailyLogsByUserView.as_view(), name="dailyLogs"),
    path("downloadDailyLogs/<str:role>/",DownloadDailyLogsView.as_view(),name="download-daily-logs"),
    path("executive/task/create/", ExecutiveTaskCreateAPIView.as_view()),
    path("executive/task/reschedule/", ExecutiveTaskRescheduleAPIView.as_view()),
    path("executive/task/complete/", ExecutiveTaskCompleteAPIView.as_view()),
    # path("getActivityLogsByUser/<int:emp_id>/<int:vendor_id>/", getActivityLogsByUserView.as_view(), name="ActivityLogs"),
    path("executive/my-tasks/", MyTaskListAPIView.as_view(), name="mytask"),
    path("createLead/", LeadCreateAPIView.as_view()),

]