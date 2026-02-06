from rest_framework.authentication import BaseAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from manager.models import Manager_register, BlacklistedToken
from jwt_utils import verify_jwt


class ManagerJWTAuthentication(BaseAuthentication):

    def authenticate(self, request):

        token = request.headers.get("Authorization")

        if not token:
            raise AuthenticationFailed("Authorization header missing")

        token = token.strip()

        # Accept "Bearer <token>" AND plain token
        if token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1].strip()

        # Check if blacklisted
        if BlacklistedToken.objects.filter(token=token).exists():
            raise AuthenticationFailed("Access token is blacklisted")

        # Verify JWT
        payload = verify_jwt(token)
        if not payload:
            raise AuthenticationFailed("Session expired. Please login again.")

        # Get user id
        user_id = payload.get("user_id")

        # ---- THIS WAS YOUR ERROR ----
        if not isinstance(user_id, int):
            raise AuthenticationFailed("user_id in token must be integer")

        # Fetch manager
        try:
            manager = Manager_register.objects.get(auth_user_id=user_id)
        except Manager_register.DoesNotExist:
            raise AuthenticationFailed("Manager not found")

        # role check
        if manager.auth_user.role != "manager":
            raise AuthenticationFailed("Token not allowed for manager API")

        return (manager, None)
