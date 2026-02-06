from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model

from multiRole.models import DailyWorkLog

User = get_user_model()


class Command(BaseCommand):
    help = "Mark absent users who never logged in"

    def handle(self, *args, **kwargs):
        today = timezone.localdate()

        for user in User.objects.all():
            DailyWorkLog.objects.get_or_create(
                emp_id=user.id,
                date=today,
                defaults={
                    "status": "absent",
                    "work_duration": "Nil"
                }
            )
