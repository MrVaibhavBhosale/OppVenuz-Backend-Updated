from django.db import models
from vendor.models import Vendor_registration
from admin_master.models import StatusMaster
# Create your models here.

class OrderStatus:
    QUEUED = 1
    ACCEPTED = 2
    COMPLETED = 3
    CANCELLED = 4

    CHOICES = (
        (QUEUED, "Order in Queue"),
        (ACCEPTED, "On-Going"),
        (COMPLETED, "Completed"),
        (CANCELLED, "Cancelled"),
    )

class PaymentStatus:
    PENDING = 1
    PAID = 2
    FAILED = 3
    REFUNDED = 4

    CHOICES = (
        (PENDING, "Pending"),
        (PAID, "Paid"),
        (FAILED, "Failed"),
        (REFUNDED, "Refunded"),
    )

class Address(models.Model):
    customer = models.IntegerField(default=1)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    landmark = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    address_type = models.CharField(
        max_length=20,
        choices=(("home", "Home"), ("office", "Office"), ("other", "Other")),
        default="home"
    )
    is_default = models.BooleanField(default=False)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50, blank=True)
    updated_by = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.full_name} - {self.address_line_1}, {self.city}"
    

class Order(models.Model):
    customer = models.IntegerField(default=1)
    vendor = models.ForeignKey("vendor.Vendor_registration", on_delete=models.PROTECT, related_name="order_items")
    delivery_address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.PROTECT, default=1)
    order_number = models.CharField(max_length=50, blank=True)
    order_status = models.IntegerField(choices=OrderStatus.CHOICES, default=OrderStatus.QUEUED)
    payment_status = models.IntegerField(choices=PaymentStatus.CHOICES, default=PaymentStatus.PENDING)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    packaging_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon_code = models.CharField(max_length=50, null=True, blank=True)
    order_date = models.DateTimeField(auto_now_add=True, blank=True)
    payment_date = models.DateTimeField(auto_now=True, null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True)
    created_by = models.CharField(max_length=50, default='user')
    updated_by = models.CharField(max_length=50, default='user')

    def save(self,*args, **kwargs):
        if not self.order_number:
            prefix = self.vendor.service_id.service_name.upper()[:4]
            last = Order.objects.filter(order_number__startswith=prefix).last()
            last_no = int(last.order_number.split("-")[-1]) if last else 0
            self.order_number = f"{prefix}-{last_no + 1:06d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number}"


class OrderItem(models.Model):
    order= models.ForeignKey(Order, on_delete=models.PROTECT, related_name="items")
    product_id = models.BigIntegerField()
    product_name = models.CharField(max_length=255)
    product_image = models.URLField()
    product_weight = models.CharField(max_length=20, blank=True)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.product_name} - {self.quantity}"    
