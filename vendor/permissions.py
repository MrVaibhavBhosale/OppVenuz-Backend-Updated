from rest_framework import permissions
from vendor.models import Vendor_registration

class IsVendor(permissions.BasePermission):
    """
    Allows access only to authenticated vendor users.
    """

    def has_permission(self, request, view):
        # Ensure the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if the logged-in user is a Vendor_registration instance
        return isinstance(request.user, Vendor_registration)

    def has_object_permission(self, request, view, obj):
        """
        Optional: allows access only to the vendor’s own objects
        (like their own services).
        """
        if isinstance(request.user, Vendor_registration):
            return getattr(obj, 'vendor_id', None) == request.user.id
        return False