"""Demo_CRM URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
 
from django.conf.urls.static import static
from django.conf import settings
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from Utilities.webhooks import PayStackWebHook, FlutterWaveWebHook, InterSwitchWebHook

schema_view = get_schema_view(
   openapi.Info(
      title="Demo_CRM API",
      default_version='v1',
      description="Test description",
      terms_of_service="",
      contact=openapi.Contact(email=""),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('dop/', include("general.urls", namespace='general')),
    path('admin/', admin.site.urls),
    path('CRM/v1/accounts/', include("accounts.urls", namespace='accounts-urls')),
    path('social_auth/', include("social_auth.urls", namespace='social_auth')),
    path('shared/', include('shared.urls', namespace='shared-urls')),
    path('integrations/', include('integrations.urls', namespace='integrations-urls')),
    path('emails/', include('email_backend.urls', namespace='email-urls')),
    path('webhook/paystack/', PayStackWebHook.as_view(), name="paystack"),
    path('webhook/flutterwave/', FlutterWaveWebHook.as_view(), name="flutterwave"),
    path('webhook/interswitch/', InterSwitchWebHook.as_view(), name='interswitch'),
    path('', include("Tenant.urls", namespace="company")),
    path('module/', include('module.urls', namespace="module"))



] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
