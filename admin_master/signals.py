import logging
from django.conf import settings
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps
from django.db import connection   # <-- FIXED: get DB connection here

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def create_default_super_admin(sender, **kwargs):
    """
    Creates a default super admin after admin_master migrations.
    Ensures table exists and avoids crashes during other app migrations.
    """

    # Run ONLY when admin_master app finishes migrations
    if sender.label != "admin_master":
        return

    # Safely load model AFTER migrations
    try:
        AdminUser = apps.get_model("admin_master", "AdminUser")
    except LookupError:
        logger.warning("AdminUser model not found during post_migrate.")
        return

    # Ensure table exists to avoid 'relation does not exist'
    existing_tables = connection.introspection.table_names()
    if AdminUser._meta.db_table not in existing_tables:
        logger.warning("AdminUser table does not exist yet. Skipping super admin creation.")
        return

    # Default credentials from settings
    default_email = getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
    default_password = getattr(settings, "DEFAULT_ADMIN_PASSWORD", None)
    default_mobile = getattr(settings, "DEFAULT_ADMIN_MOBILE", "")
    default_full_name = getattr(settings, "DEFAULT_ADMIN_FULL_NAME", "Super Admin")

    if not default_email or not default_password:
        logger.warning("DEFAULT_ADMIN_EMAIL or DEFAULT_ADMIN_PASSWORD not set. Skipping.")
        return

    try:
        if AdminUser.objects.filter(email=default_email).exists():
            logger.info("Default super admin already exists: %s", default_email)
            return

        # Create super admin
        user = AdminUser.objects.create_superuser(
            email=default_email,
            password=default_password,
            mobile_no=default_mobile,
            full_name=default_full_name,
        )

        user.is_active = True
        user.is_staff = True
        user.save(update_fields=["is_active", "is_staff"])

        logger.info("Created default super admin: %s", default_email)

    except Exception as e:
        logger.exception("Error creating default super admin: %s", e)

@receiver(post_migrate)
def insert_default_task_masters(sender, **kwargs):

    if sender.label != "admin_master":
        return

    TaskType = apps.get_model("admin_master", "TaskType")
    VendorResponse = apps.get_model("admin_master", "VendorResponse")
    TaskStatus = apps.get_model("admin_master", "TaskStatus")
    ReasonForTask = apps.get_model("admin_master", "ReasonForTask")

    for name in ["Call", "Site Visit"]:
        TaskType.objects.get_or_create(name=name)

    for name in ["Interested", "Not-Interested", "Registered"]:
        VendorResponse.objects.get_or_create(name=name)

    for name in ["Task Closed", "Task Open", "Reschedule"]:
        TaskStatus.objects.get_or_create(name=name)

    for name in [
        "Vendor Not Responding",
        "Forget to update the task",
        "Network issue at field visit",
        "Site Visit Missed",
        "Leave or sick day",
    ]:
        ReasonForTask.objects.get_or_create(name=name)

@receiver(post_migrate)
def insert_default_lead_sources(sender, **kwargs):
    if sender.label != "admin_master":
        return

    LeadSource = apps.get_model("admin_master", "LeadSource")

    for name in ["Direct", "Social Media", "Referral"]:
        LeadSource.objects.get_or_create(name=name)
