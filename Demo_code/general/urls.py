# accounts/urls.py

from django.contrib.auth.decorators import login_required
from django.urls import path
# RESTFRAMEWORK imports
from rest_framework.routers import DefaultRouter

# View and other imports
from .views import *

app_name = 'general'

router = DefaultRouter()
router.register(r'product', ReadDeleteProductAPI, basename="product")
router.register(r'plan', ReadDeletePlanAPI, basename='plan')
router.register(r'license', ReadLicenseAPI, basename='licence')




urlpatterns = [
    path('plan/create/', AddPlanAPI.as_view({'post': 'create'}),name="add_plan"),
	path('plan/<int:pk>/update/', UpdatePlanAPI.as_view({"patch": "partial_update"}), name="update_plan"),
	path('product/create/', AddProductAPI.as_view({'post': 'create'}),name="add_product"),
	path('product/<int:pk>/update/', UpdateProductAPI.as_view({"patch": "partial_update"}), name="update_product"),
	path('subscribe/', SubscribeAPI.as_view({'post': 'create'}), name="subscribe"),
	path('product/<int:id>/licence/cancel/', 	CancelSubscriptionsAPI.as_view(), name="cancel_subscription"),
	path('user/<int:pk>/remove_license/', RemoveUserSubscriberAPI.as_view({"patch": "partial_update"}), name="remove_license"),
	path('user/<int:pk>/assign_license/', AssignUserSubscriberAPI.as_view({"patch": "partial_update"}), name="assign_license"),

	path('webhook/test/', SendConfirmationTest.as_view(), name="test_webhook")

]
urlpatterns += router.urls

