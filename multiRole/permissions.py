from rest_framework.permissions import BasePermission
from manager.models import Manager_register
from team_head.models import TeamHead_register
from executive.models import Executive_register


class EmployeeDetailsPermission(BasePermission):

    def has_permission(self, request, view):
        # User must be authenticated via JWT
        return bool(request.auth)

    def has_object_permission(self, request, view, obj):
        role = request.auth.get("role")
        user = request.user

        # ---------- MANAGER ----------
        if role == "manager":
            # Can see executives
            if isinstance(obj, Executive_register):
                return True

            # Can see team heads
            if isinstance(obj, TeamHead_register):
                return True

            # Can see ONLY self (manager)
            if isinstance(obj, Manager_register):
                return obj.id == user.id

            return False

        # ---------- TEAM HEAD ----------
        if role == "team_head":
            # Can see executives
            if isinstance(obj, Executive_register):
                return True

            # Can see ONLY self
            if isinstance(obj, TeamHead_register):
                return obj.id == user.id

            return False

        # ---------- EXECUTIVE ----------
        if role == "executive":
            # Only self
            return isinstance(obj, Executive_register) and obj.id == user.id

        return False
