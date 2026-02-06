# views.py
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Executive_register,
    ExecutiveLocationLog,
    ExecutiveSiteVisit
)
from .serializers import (
    RouteCoordinateSerializer,
    SiteVisitSerializer
)


class TrackSiteVisitAPIView(APIView):

    def post(self, request):
        data = request.data
        executive_id = data.get("executiveId")

        if not executive_id:
            return Response(
                {"status": False, "message": "executiveId is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            executive = Executive_register.objects.get(emp_id=executive_id)
        except Executive_register.DoesNotExist:
            return Response(
                {"status": False, "message": "Executive not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        location_log = ExecutiveLocationLog.objects.create(
            executive=executive,
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            accuracy=data.get("accuracy"),
            timestamp=data.get("timestamp", datetime.now())
        )

        site_visit_data = data.get("siteVisit")
        if site_visit_data:
            ExecutiveSiteVisit.objects.create(
                executive=executive,
                visit_number=site_visit_data.get("visit_number"),
                site_name=site_visit_data.get("site_name"),
                site_address=site_visit_data.get("site_address"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                visit_duration=site_visit_data.get("visit_duration"),
                status=site_visit_data.get("status"),
                timestamp=data.get("timestamp", datetime.now())
            )

        return Response(
            {
                "status": True,
                "message": "Location & site visit stored successfully"
            },
            status=status.HTTP_201_CREATED
        )

    def get(self, request):
        executive_id = request.query_params.get("executiveId")
        date_str = request.query_params.get("date")

        if not executive_id or not date_str:
            return Response(
                {"status": False, "message": "executiveId and date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            visit_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"status": False, "message": "Invalid date format (YYYY-MM-DD)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            executive = (
                Executive_register.objects
                .select_related("city")
                .get(emp_id=executive_id)
            )
        except Executive_register.DoesNotExist:
            return Response(
                {"status": False, "message": "Executive not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        city_name = executive.city.city_name if executive.city else ""

        route_points = ExecutiveLocationLog.objects.filter(
            executive=executive,
            timestamp__date=visit_date
        )

        start_location = None
        end_location = None

        if route_points.exists():
            start = route_points.first()
            end = route_points.last()

            start_location = {
                "latitude": start.latitude,
                "longitude": start.longitude,
                "timestamp": start.timestamp
            }

            end_location = {
                "latitude": end.latitude,
                "longitude": end.longitude,
                "timestamp": end.timestamp
            }

        site_visits = ExecutiveSiteVisit.objects.filter(
            executive=executive,
            timestamp__date=visit_date
        ).order_by("visit_number")

        route_serializer = RouteCoordinateSerializer(route_points, many=True)
        site_serializer = SiteVisitSerializer(site_visits, many=True)

        return Response(
            {
                "status": True,
                "message": "Tracking data fetched successfully",
                "data": {
                    "executiveId": executive.emp_id,
                    "executiveName": executive.full_name,
                    "date": str(visit_date),

                    "route": {
                        "coordinates": route_serializer.data
                    },

                    "siteVisits": site_serializer.data,

                    "summary": {
                        "totalSiteVisits": site_visits.count(),
                        "startLocation": start_location,
                        "endLocation": end_location,
                        "defaultCity": city_name
                    }
                }
            },
            status=status.HTTP_200_OK
        )
