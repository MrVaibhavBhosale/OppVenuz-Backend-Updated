from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from django.shortcuts import redirect

def health_check(request):
    return JsonResponse({"status": "ok"}, status=200)

def index_redirect(request):
    return redirect("/")

schema_view = get_schema_view(
    openapi.Info(
        title="OppVenuz API",
        default_version="v1",
        description="API documentation for OppVenuz project",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@oppvenuz.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("health/", health_check),

    path("swagger.json",
         schema_view.without_ui(cache_timeout=0),
         name="schema-json"),

    path('', schema_view.with_ui('swagger', cache_timeout=0)),

    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),

    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("admin/", admin.site.urls),
    path("admin-master/", include("admin_master.urls")),
    path("vendor/", include("vendor.urls")),
    path("user/", include("user.urls")),
    path("manager/", include("manager.urls")),
    path("executive/", include("executive.urls")),
    path("multiRole/", include("multiRole.urls")),
    path("celebrity/", include("celebrity.urls")),
]
