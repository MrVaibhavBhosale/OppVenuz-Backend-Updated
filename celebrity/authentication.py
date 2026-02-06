from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from celebrity.models import CelebrityRegistration
from vendor.models import BlacklistedToken   
from jwt_utils import verify_jwt


class CelebrityJWTAuthentication(BaseAuthentication):

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
            # Case 2: direct token
            token = token

        token_str = str(token)

        # ---------- BLACKLIST CHECK ----------
        if BlacklistedToken.objects.filter(token=token_str).exists():
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})

        # ---------- VERIFY JWT ----------
        payload = verify_jwt(token_str)
        if not payload:
            raise AuthenticationFailed(detail={"status": False, "message": "Invalid or expired token."})

        # ---------- USER ID ----------
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationFailed(detail={"status": False,"message":"Invalid token. No user_id found."})

        # ---------- FETCH CELEBRITY ----------
        try:
            celebrity = CelebrityRegistration.objects.get(id=user_id)
        except CelebrityRegistration.DoesNotExist:
            raise AuthenticationFailed(detail={"status": False, "message":"Celebrity not found."})

        return (celebrity, None)