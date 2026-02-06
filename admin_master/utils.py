from .models import StatusMaster
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
import logging
logger = logging.getLogger("django")
from admin_master.models import AdminUser
from manager.models import Manager_register
from team_head.models import TeamHead_register

def get_status(status_name):
    try:
        return StatusMaster.objects.get(status_type=status_name)
    except StatusMaster.DoesNotExist:
        # Create if not exists
        return StatusMaster.objects.create(status_type=status_name)


signer = TimestampSigner()

def generate_reset_token(email):
    return signer.sign(email)

def verify_reset_token(token, max_age=600):
    try:
        return signer.unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    
def get_reporting_list_by_role(role):

    ROLE_MODEL_MAP = {
        "manager": AdminUser,
        "team_head": Manager_register,
        "executive": TeamHead_register,
    }

    if not role:
        logger.error("Role not provided")
        return []

    model = ROLE_MODEL_MAP.get(role.lower())
    if not model:
        logger.error(f"Invalid role provided: {role}")
        return None
    
    # Base queryset with status filter
    qs = model.objects.filter(status__status_type='Active')

    # Extra filter if model is AdminUser
    if model == AdminUser:
        qs = qs.filter(role__iexact='admin')

    # Return unified values
    return list(qs.values("id", "full_name"))
