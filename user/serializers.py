from rest_framework import serializers
from django.utils.text import slugify
from django.db import transaction
from .models import (
    Address,
    Order,
    OrderItem,
)
from vendor.models import Vendor_registration
from admin_master.models import StatusMaster

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "full_name", "phone", "address_line_1", 
                  "address_line_2", "landmark", "city", "state", "pincode"]

class OrderItemserializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    vendor = serializers.IntegerField()
    product_name = serializers.CharField()
    product_image = serializers.URLField()
    product_weight = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class CreateOrderSerializer(serializers.Serializer):
    customer = serializers.IntegerField()
    delivery_address = serializers.IntegerField()
    payment_method = serializers.CharField()
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    items = OrderItemserializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")

        for item in items:
            if item["quantity"] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0.")

            if not Vendor_registration.objects.filter(id=item["vendor"]).exists():
                raise serializers.ValidationError(f"Vendor {item['vendor']} not found.")

        return items

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        discount_percentage = validated_data.pop("discount", 0)

        # Validate address
        delivery_address_id = validated_data.pop("delivery_address")
        address = Address.objects.filter(id=delivery_address_id).first()
        if not address:
            raise serializers.ValidationError("Invalid delivery address.")
        
        # Group items by vendor
        vendor_group = {}
        for item in items_data:
            vendor_group.setdefault(item["vendor"], []).append(item)

        created_orders = []

        with transaction.atomic():
            for vendor_id, vendor_items in vendor_group.items():

                # Create order for each vendor
                order = Order.objects.create(
                    customer=validated_data["customer"],
                    delivery_address=address,
                    vendor_id=vendor_id,
                    payment_method=validated_data["payment_method"],
                    coupon_code=validated_data.get("coupon_code", "")
                )

                subtotal = 0

                # Create all items
                for item in vendor_items:
                    total_price = item["quantity"] * item["unit_price"]
                    subtotal += total_price

                    OrderItem.objects.create(
                        order=order,
                        product_id=item["product_id"],
                        product_name=item["product_name"],
                        product_image=item["product_image"],
                        product_weight=item["product_weight"],
                        quantity=item["quantity"],
                        unit_price=item["unit_price"],
                        total_price=total_price,
                    )

                delivery_fee = 0
                packaging_fee = 0
                platform_fee = 0

                # Discount
                discount_amount = (subtotal * discount_percentage) / 100

                # Final total
                grand_total = subtotal - discount_amount + delivery_fee + platform_fee + packaging_fee

                # Update order totals
                order.subtotal = subtotal
                order.delivery_fee = delivery_fee
                order.packaging_fee = packaging_fee
                order.platform_fee = platform_fee
                order.discount = discount_percentage
                order.grand_total = grand_total
                order.paid_amount = 0
                order.save()

                created_orders.append(order)

        return created_orders

                