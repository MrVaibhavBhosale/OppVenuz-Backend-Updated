import django_filters
from django_filters import rest_framework as filter
from user.models import Order

class OrderFilter(filter.FilterSet):
    order_status = django_filters.CharFilter(field_name="order_status", lookup_expr='exact')
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = Order
        fields = ["order_status",]