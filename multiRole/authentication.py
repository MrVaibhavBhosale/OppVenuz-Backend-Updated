from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from jwt_utils import verify_jwt
from .models import AdminUser, BlacklistedToken
from rest_framework.authentication import BaseAuthentication
from manager.models import Manager_register
from executive.models import Executive_register
from team_head.models import TeamHead_register
class MultiRoleJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.headers.get("Authorization") 

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
        if BlacklistedToken.objects.filter(token=token_str).exists():
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})


        payload = verify_jwt(token)
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})

        # Must contain role 
        role = payload.get("role")
        if role not in ["manager", "executive","team_head"]:
            raise AuthenticationFailed(detail={"status": False, "message":"Invalid role for this token."})

        # Fetch admin based on user_id
        # try:
        #     user = Executive_register.objects.get(id=payload["user_id"])
        # except Executive_register.DoesNotExist:
        #     raise AuthenticationFailed("Admin not found.")

        # return (user, None)
    

        if role.lower() == "executive":
            try:
                user = Executive_register.objects.get(id=payload["user_id"])
            except Executive_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Executive not found."})

        elif role.lower() == "manager":
            try:
                user = Manager_register.objects.get(id=payload["user_id"])
            except Manager_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Manager not found."})
            
        elif role.lower() == "team_head":
            try:
                user = TeamHead_register.objects.get(id=payload["user_id"])
            except TeamHead_register.DoesNotExist:
                raise AuthenticationFailed(detail={"status": False, "message":"Team Lead not found."})

        else:
            raise AuthenticationFailed(detail={"status": False, "message":"Invalid role in token."})

        return (user, payload)