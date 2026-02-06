import jwt
from django.conf import settings
from django.utils import timezone
from datetime import timedelta, time
import pytz


AUTO_LOGOUT_ROLES = ["manager", "executive", "team_head"]
IST = pytz.timezone("Asia/Kolkata")


def _get_today_1159_expiry():
    """
    Returns timezone-aware datetime for today 11:59 PM IST
    """
    now_ist = timezone.now().astimezone(IST)

    expiry_ist = now_ist.replace(
        hour=23,
        minute=59,
        second=0,
        microsecond=0
    )

    # If already past 11:59 PM → expire immediately
    if now_ist >= expiry_ist:
        expiry_ist = now_ist + timedelta(seconds=1)

    return expiry_ist.astimezone(pytz.UTC)


def create_jwt(payload, expiry_minutes=None, expiry_days=None):
    now = timezone.now()
    role = payload.get("role")

    # Priority 1 → explicit expiry
    if expiry_minutes:
        exp = now + timedelta(minutes=expiry_minutes)

    elif expiry_days:
        exp = now + timedelta(days=expiry_days)

    # Priority 2 → auto logout at 11:59 PM IST
    elif role in AUTO_LOGOUT_ROLES:
        exp = _get_today_1159_expiry()

    # Priority 3 → fallback
    else:
        exp = now + timedelta(days=1)

    payload.update({
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp())
    })

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


def verify_jwt(token):
    try:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
