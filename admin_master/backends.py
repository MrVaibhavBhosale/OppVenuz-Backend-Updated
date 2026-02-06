# admin_master/backend.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from .models import AdminUser


class AdminAuthBackend(BaseBackend):
    """
    Authenticate using email OR mobile_no for AdminUser.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = username or (request.data.get("email") if request and hasattr(request, "data") else None)
        if not identifier or not password:
            return None

        try:
            if "@" in identifier:
                user = AdminUser.objects.get(email=identifier)
            else:
                user = AdminUser.objects.get(mobile_no=identifier)
        except AdminUser.DoesNotExist:
            return None

        if user.check_password(password):
            return user
        return None

    def get_user(self, user_id):
        try:
            return AdminUser.objects.get(pk=user_id)
        except AdminUser.DoesNotExist:
            return None
