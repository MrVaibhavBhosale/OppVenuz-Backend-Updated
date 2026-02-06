from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from vendor.models import Vendor_registration, BlacklistedToken
from jwt_utils import verify_jwt
from rest_framework.authentication import BaseAuthentication
from .models import Vendor_registration

class VendorJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        # check access token blacklist
        if BlacklistedToken.objects.filter(token=token).exists():
            raise AuthenticationFailed(detail={"status": False, "message": "Access Token is blacklisted."})
        
        # Verify JWT
        payload = verify_jwt(token)
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})

        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid token. No user_id found."})

        # Vendor is linked to AdminUser through auth_user FK
        try:
            vendor = Vendor_registration.objects.get(auth_user_id=user_id)
        except Vendor_registration.DoesNotExist:
            raise AuthenticationFailed(detail={"status": False, "message": "Vendor not found."})

        # Check vendor role from linked admin_user
        if vendor.auth_user.role != "vendor":
            raise AuthenticationFailed(detail={"status": False, "message": "Token is not allowed for vendor API."})

        return (vendor, None)
