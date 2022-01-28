# accounts/urls.py

from django.contrib.auth.decorators import login_required
from django.urls import path
# RESTFRAMEWORK imports
from rest_framework.routers import DefaultRouter

# View and other imports
from .views import *

app_name = 'Tenant'

router = DefaultRouter()
router.register(r'company', ReadCompanyAPI, basename="company")




urlpatterns = [
    path('company/<int:pk>/edit/', EditCompanyDetailsAPI.as_view({"patch": "partial_update"}), name="edit_company"),
	path('company/<int:pk>/upload_image/', UploadCompanyImageAPI.as_view(), name="upload_image_company"),
]
urlpatterns += router.urls

