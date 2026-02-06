from django.urls import path
from .views import TrackSiteVisitAPIView

urlpatterns = [
    path("track-site-visit/", TrackSiteVisitAPIView.as_view(), name='tracksitevisit'),
]
