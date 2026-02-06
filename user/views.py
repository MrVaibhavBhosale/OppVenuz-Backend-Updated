from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import generics, status
import boto3
from django.conf import settings
from decouple import config
from rest_framework_simplejwt.authentication import JWTAuthentication
from oauth2_provider.contrib.rest_framework.authentication import OAuth2Authentication
from rest_framework.response import Response
import logging
logger = logging.getLogger("django")

from .serializers import (
    CreateOrderSerializer,
    )

class ImageUploadView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = (OAuth2Authentication, JWTAuthentication)

    def post(self, request, *args, **kwargs):
        image = request.FILES.get("image")
        bucket = config("S3_BUCKET_NAME")
        key = request.data.get("key")

        if image:
            # Upload the image to S3 using boto3
            s3 = boto3.client(
                "s3",
                aws_access_key_id=config("s3AccessKey"),
                aws_secret_access_key=config("s3Secret"),
            )
            key = f"{image.name}"  # Change the key as needed
            s3.upload_fileobj(image, bucket, key, ExtraArgs={"ACL": "public-read"})

            # Generate the URL for the uploaded image
            url = f"https://{bucket}.s3.amazonaws.com/{key}"

            return Response({"url": url}, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST
            )

class CreateOrderAPIView(APIView):
    permission_classes = []

    def post(self, request):
        try:
            serializer = CreateOrderSerializer(data=request.data)

            if not serializer.is_valid():
                logger.warning(f"Order validation failed: {serializer.errors}")
                return Response({
                    "error": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST)
            
            order = serializer.save()

            return Response({
                    "success": True,
                    "message": "order created successfully.",
                    "orders": [
                        {
                            "order_id": order.id,
                            "order_number": order.order_number,
                            "vendor_id": order.vendor_id,
                            "subtotal": order.subtotal,
                            "grand_total": order.grand_total

                        }
                        for order in order
                    ]
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.exception("Unexpected error while creating order")
            return Response({
                "error": "something went wrong. Please try again",
                "details": str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
