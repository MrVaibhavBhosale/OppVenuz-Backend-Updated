from rest_framework import serializers
from .models import (
    AdminUser,
    Executive_register,
)
from manager.models import (
    Manager_register
)
from django.contrib.auth import authenticate
import re
from django.db import models
import os
from django.db.models import Q
from admin_master.models import AdminUser, State_master, City_master
from .models import ExecutiveLocationLog, ExecutiveSiteVisit
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.hashers import check_password



class ExecutiveDataSerializer(serializers.ModelSerializer):
    mpin = serializers.CharField(write_only=True)
    # documents = VendorDocumentSerializer(many=True, read_only=True)

    def get_city(self, obj):
        if obj.city_id:
            city = City_master.objects.filter(id=obj.city_id).first()
            return city.city_name if city else None
        return None

    def get_state(self, obj):
        if obj.state_id:
            state = State_master.objects.filter(id=obj.state_id).first()
            return state.state_name if state else None
        return None

    class Meta:
        model = Executive_register
        fields = '__all__'

    def to_representation(self, instance):
        return {
            "executive_id": instance.emp_id,
            "first_name": instance.full_name,
            "email": instance.email_id,
            "email_address": instance.email_address,
            "mobile_no": instance.mobile_no,
            "joining_date": instance.joining_date,
            "city": getattr(instance.city_id, 'city_name', None),
            "state": getattr(instance.state_id, 'state_name', None),
            "employment_type": instance.employment_type,
            "work_mode": instance.work_mode,
            "branch": instance.branch,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "profile_image": instance.profile_image_url,
        }

class RouteCoordinateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExecutiveLocationLog
        fields = (
            "latitude",
            "longitude",
            "accuracy",
            "timestamp",
        )


class SiteVisitSerializer(serializers.ModelSerializer):
    visitId = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveSiteVisit
        fields = (
            "visitId",
            "visit_number",
            "latitude",
            "longitude",
            "timestamp",
            "site_name",
            "site_address",
            "visit_duration",
            "status",
        )

    def get_visitId(self, obj):
        return f"SV{obj.id:03d}"