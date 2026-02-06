from django.contrib.auth.backends import BaseBackend
from vendor.models import Vendor_registration
from admin_master.models import AdminUser

class VendorAuthBackend(BaseBackend):

    def authenticate(self, request, username=None, mpin=None, **kwargs):

        if not username or not mpin:
            return None

        try:
            # vendor login allowed via email or contact number
            if '@' in username:
                vendor = Vendor_registration.objects.get(email=username)
            else:
                vendor = Vendor_registration.objects.get(contact_no=username)
        except Vendor_registration.DoesNotExist:
            return None

        # check mpin
        if not vendor.check_mpin(mpin):
            return None

        # ✔ ALWAYS return AdminUser
        return vendor.auth_user

    def get_user(self, user_id):
        try:
            return AdminUser.objects.get(pk=user_id)
        except AdminUser.DoesNotExist:
            return None
