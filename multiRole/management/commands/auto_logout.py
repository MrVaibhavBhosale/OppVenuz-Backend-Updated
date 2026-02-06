import logging
from datetime import time, datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from multiRole.models import DailyWorkLog, RefreshTokenStore, BlacklistedToken

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Auto logout employees with Present / Late / Half Day / Absent"

    AUTO_LOGOUT_TIME = time(23, 59)  # 11:59 PM
    LATE_LOGIN_TIME = time(9, 30)    # 9:30 AM

    def handle(self, *args, **kwargs):
        now_local = timezone.localtime(timezone.now())
        today = now_local.date()

        logger.info(f"AUTO LOGOUT STARTED for {today}")

        # Fetch all logs that haven't logged out yet
        logs = DailyWorkLog.objects.filter(logout_time__isnull=True)

        for log in logs:
            # ---------------- ABSENT (NO LOGIN) ----------------
            if not log.login_time:
                log.work_minutes = 0
                log.work_duration = "Nil"
                log.status = "absent"
                log.working_status = "absent"
                log.save(update_fields=[
                    "work_minutes",
                    "work_duration",
                    "status",
                    "working_status"
                ])
                continue

            # ---------------- AUTO LOGOUT ----------------
            logout_dt = timezone.make_aware(
                datetime.combine(log.date, self.AUTO_LOGOUT_TIME),
                timezone.get_current_timezone()
            )
            log.logout_time = logout_dt

            # Calculate work duration
            log.calculate_work_minutes()
            log.working_status = "auto-logout"

            # ---------------- STATUS LOGIC ----------------
            minutes = log.work_minutes

            if minutes < 240:
                log.status = "absent"
            elif 240 <= minutes < 480:
                log.status = "half-day"
            else:
                if log.login_time > self.LATE_LOGIN_TIME:
                    log.status = "late"
                else:
                    log.status = "present"

            log.save(update_fields=[
                "logout_time",
                "work_minutes",
                "work_duration",
                "status",
                "working_status"
            ])

            # ---------------- TOKEN INVALIDATION ----------------
            token = RefreshTokenStore.objects.filter(
                user_id=log.user_id,
                role=log.role
            ).first()

            if token:
                BlacklistedToken.objects.create(
                    user_id=log.user_id,
                    role=log.role,
                    token=token.token
                )
                token.delete()

        logger.info("AUTO LOGOUT COMPLETED")
