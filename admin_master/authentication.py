from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jwt_utils import verify_jwt
from .models import AdminUser, BlacklistedAdminAccessToken
from rest_framework.authentication import BaseAuthentication
class AdminJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get("Authorization") 

        # if not token or not token.startswith("Bearer "):
        #     return None
        
        # token = token.split(" ")[1]

        if not token:
            return None
        

        # Normalize spacing
        token = token.strip()

        # Case 1: "Bearer <token>"
        if token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1].strip()
        else:
            # Case 2: direct token without Bearer
            token = token

        token_str = str(token)
        if BlacklistedAdminAccessToken.objects.filter(token=token_str).exists():
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})


        payload = verify_jwt(token)
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})

        # Must contain role = "admin" or "super_admin"
        role = payload.get("role")
        if role not in ["admin", "super_admin"]:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid role for this token."})

        # Fetch admin based on user_id
        try:
            user = AdminUser.objects.get(id=payload["user_id"])
        except AdminUser.DoesNotExist:
            raise AuthenticationFailed(detail={"status": False, "message": "Admin not found."})

        return (user, None)
