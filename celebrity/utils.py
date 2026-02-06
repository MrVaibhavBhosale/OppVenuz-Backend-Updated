import boto3
import uuid
import hashlib
import os
from decouple import config
import random
import logging
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import requests
from utilities import constants
from django.db.models import Q
import re
logger = logging.getLogger("django")


def get_s3_client():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=config("s3AccessKey"),
        aws_secret_access_key=config("s3Secret"),
    )
    bucket = config("S3_BUCKET_NAME")
    return s3, bucket


def calculate_file_hash(file):
    hash_sha256 = hashlib.sha256()
    for chunk in file.chunks():
        hash_sha256.update(chunk)
    file.seek(0)
    return hash_sha256.hexdigest()


def upload_to_s3(file, folder_path):
    s3, bucket = get_s3_client()

    ext = os.path.splitext(file.name)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    key = f"{folder_path}/{filename}"

    s3.upload_fileobj(
        file,
        bucket,
        key,
        ExtraArgs={"ACL": "public-read"}
    )

    url = f"https://{bucket}.s3.amazonaws.com/{key}"
    return filename, url

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
