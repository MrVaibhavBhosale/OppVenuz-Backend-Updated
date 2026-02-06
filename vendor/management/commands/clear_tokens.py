from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from vendor.models import BlacklistedToken

class Command(BaseCommand):
    help = "Clears expired or old blacklisted tokens"

    def handle(self, *args, **options):
        # Example: delete blacklisted tokens older than 7 days
        days = 7
        delete_before = timezone.now() - timedelta(days=days)

        deleted_count, _ = BlacklistedToken.objects.filter(
            blacklisted_at__lt=delete_before
        ).delete()

        self.stdout.write(
            self.style.SUCCESS(f"Deleted {deleted_count} old blacklisted tokens")
        )