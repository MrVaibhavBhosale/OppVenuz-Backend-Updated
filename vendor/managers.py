from django.contrib.auth.hashers import make_password
from django.db import models

class VendorManager(models.Manager):
    def create_vendor(self, email, contact_no, mpin, **extra_fields):
        """
        Custom method to create a vendor with hashed MPIN
        """
        if not mpin:
            raise ValueError("MPIN is required")
        
        vendor = self.model(
            email=email,
            contact_no=contact_no,
            **extra_fields
        )
        vendor.mpin = make_password(mpin)  # hash MPIN before saving
        vendor.save(using=self._db)
        return vendor

    def get_by_email_or_contact(self, identifier):
        """
        Get vendor by email or contact number
        """
        return self.filter(models.Q(email=identifier) | models.Q(contact_no=identifier)).first()
