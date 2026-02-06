from django.urls import path
from .views import (
    ImageUploadView,
    CreateOrderAPIView
)

urlpatterns = [
    path("v1/uploadImageToS3", ImageUploadView.as_view(), name="upload-image-to-s3"),
    path("createOrder/", CreateOrderAPIView.as_view(), name="create-order")
]
