# social_auth/urls.py
from django.urls import path, include

# View and other imports
from .views import *

app_name = 'social_auth'

urlpatterns = [
    path('google/', TenantGoogleSocialAuthView.as_view(), name='google'),
    path('microsoft/', TenantMicrosoftSocialAuthView.as_view(), name='microsoft'),

]


