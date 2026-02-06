import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, Personalization, Bcc
from django.conf import settings
import requests
from utilities import constants
from .models import Vendor_registration
from django.db.models import Q
import re
import logging
logger = logging.getLogger("django")
from python_http_client import exceptions


import hashlib

def calculate_file_hash(file_obj, chunk_size=4096):
    """
    Returns SHA256 hash of uploaded file (works for large files also).
    """
    hash_sha256 = hashlib.sha256()
    file_obj.seek(0)

    for chunk in iter(lambda: file_obj.read(chunk_size), b""):
        hash_sha256.update(chunk)

    file_obj.seek(0)

    return hash_sha256.hexdigest()

def generate_numeric_otp(length=6):
    #Return a numeric OTP as string (e.g. '123456').
    start = 10**(length-1)
    end = (10**length) - 1
    otp = str(random.randint(start, end))
    return otp

def mask_phone(phone):
    if not phone:
        return phone
    phone = str(phone)
    return phone[:2] + "******" + phone[-2:]

def mask_email(email):
    if not email or '@' not in email:
        return email
    name, domain = email.split('@', 1)
    if len(email) <= 2:
        masked_name = name[0] + "****"
    else:
        masked_name = name[:2] + "****"
    return masked_name + '@' + domain

def send_otp_email(email, otp):
    from_email = settings.DEFAULT_FROM_EMAIL
    template_id = constants.VENDOR_EMAIL_VERIFICATION_TEMPLATE

    if not settings.SENDGRID_API_KEY or not from_email:
        logger.error("SendGrid API key or default sender not configured.")
        return None

    dynamic_data = {
        "otp": otp,
        "expiry": "5 minutes",
    }

    mail = Mail(
        from_email=from_email,
        to_emails=email,
    )
    mail.template_id = template_id
    mail.dynamic_template_data = dynamic_data  

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(mail)
        return response.status_code
    except Exception as e:
        logger.error(f"Error sending email OTP to {email}: {e}")
        return None

def send_otp_sms(phone, otp):
    #url = "https://api.textlocal.in/send/"

    # Format your template with the actual OTP
    message = constants.PHONE_VERIFICATION_MSG_TEMPLATE.format(otp)

    payload = {
        "apikey": settings.TEXT_LOCAL_API_KEY,
        "numbers": phone,
        "message": message,
        "sender": settings.TEXTLOCAL_SENDER,   
    }

    try:
        response = requests.post(data=payload)
        data = response.json()

        if data.get("status") == "success":
            return True
        else:
            logger.warning(f"Failed to send OTP SMS to {phone}: {data}")
            return False

    except requests.exceptions.Timeout:
        logger.error(f"Timeout while sending OTP SMS to {phone}")
        return False
    except Exception as e:
        logger.exception(f"Error sending OTP SMS to {phone}: {e}")
        return False
    

class UserIdentifierhelper:

    @staticmethod
    def is_email(value):
        return re.match(r"[^@]+@[^@]+\.[^@]+", value) is not None

    @staticmethod
    def is_phone(value):
        return re.match(r"^[0-9]{10}$", value) is not None

    @staticmethod
    def detect_type(value):
        if UserIdentifierhelper.is_email(value):
            return "email"
        elif UserIdentifierhelper.is_phone(value):
            return "phone"
        return None

class VerifyIsRegistered:

    @staticmethod
    def check(identifier:str):
        """
        Check if email or phone exists in Vendor_registration.
        Returns: user instance or None
        """
        return Vendor_registration.objects.filter(
            Q(email=identifier) | Q(contact_no=identifier)
        ).exists()
    
def send_email(recipient, data_dict, bcc=False):
    """
    Function to connect with sendgrid and send emails to receivers
    """
    sender = settings.DEFAULT_FROM_EMAIL
    sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
    mail = Mail()
    mail.template_id = constants.FORGOT_PASSWORD_TEMPLATE

    mail.from_email = Email(sender)
    personalization = Personalization()
    personalization.add_to(Email(recipient))
    personalization.dynamic_template_data = data_dict
    mail.add_personalization(personalization)
    if bcc:
        # mail.add_bcc(Bcc(VENDOR_FROM_EMAIL))

        mail.add_bcc(Bcc(constants.CLIENT_EMAIL))
    try:
        if recipient:
            response = sg.client.mail.send.post(request_body=mail.get())
    except exceptions.BadRequestsError as e:
        logger.error(f"SendGrid BadRequestsError: {e.body}")
        exit()
    logger.info(f"Email sent successfully to {recipient}. Status code: {response.status_code}")

    return None

def get_status_count(queryset):
    return {
        "all": queryset.count(),
        "registered": queryset.filter(profile_status="Registered").count(),
        "approved": queryset.filter(profile_status="Approved").count(),
        "active": queryset.filter(status__status_type='Active').count(),
        "inactive": queryset.filter(status__status_type='Inactive').count()
    }