from django.shortcuts import render
from django_tenants.utils import schema_context

from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework import status

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from Multitenant.classes import SchemaFromRequest, CreateTenant, SchemaToName
from .serializers import GoogleSocialAuthSerializer, MicrosoftSocialAuthSerializer

test_param = openapi.Parameter('company', openapi.IN_HEADER, description="company for schema", type=openapi.TYPE_STRING)



# Create your views here.
# Google Login View
class GoogleSocialAuthView(GenericAPIView):
    serializer_class = GoogleSocialAuthSerializer

    def post(self, request):
        """

        POST with "auth_token"

        Send an idtoken as from google to get user information

        """
        response = self.execute(request)
        if response['status'] == 'success':
            return Response(response, status.HTTP_200_OK)
        else:
            return Response(response, status.HTTP_400_BAD_REQUEST)

    def execute(self, request, tenant=None):
        try:
            serializer = self.serializer_class(data=request.data, context={"tenant": tenant})
            print("google")
            if serializer.is_valid(raise_exception=True):
                print("validated=========>", serializer.context)
                del serializer.context['tenant']
                return {'status': 'success', 'message': 'User login Successflly', "data": serializer.context}
        except Exception as e:
            return {'status': 'error', 'message': 'Login is not successfull' + str(e)}


class TenantGoogleSocialAuthView(GoogleSocialAuthView):
    @swagger_auto_schema(manual_parameters=[test_param], responses={200: "ok"})
    def post(self, request):
        tenant_data = {}
        schema = SchemaFromRequest(request)
        real_schema = schema
        if schema == 'public':
            data = CreateTenant(request)
            if data.__len__() == 1:
                schema = data[0]
            else:
                tenant, tenant_data = data
                schema = tenant.schema_name
        with schema_context(schema):
            data = super(TenantGoogleSocialAuthView, self).execute(request, real_schema)
            if data['status'] == 'success':
                data['data']['company'] = tenant_data if real_schema == 'public' else SchemaToName(schema)
                if real_schema == 'public':
                    data['message'] = 'Signup is Successful'
                return Response(data, status.HTTP_200_OK)
            else:
                return Response(data, status.HTTP_400_BAD_REQUEST)


class MicrosoftSocialAuthView(GenericAPIView):
    serializer_class = MicrosoftSocialAuthSerializer

    def post(self, request):
        """

        POST with "access_token"

        Send an authorization code as from Microsoft to get user information

        """
        response = self.execute(request)
        if response['status'] == 'success':
            return Response(response, status.HTTP_200_OK)
        else:
            return Response(response, status.HTTP_400_BAD_REQUEST)

    def execute(self, request, tenant=None):
        try:
            serializer = self.serializer_class(data=request.data, context={"tenant": tenant})
            if serializer.is_valid(raise_exception=True):
                del serializer.context['tenant']
                print("validated=========>", serializer.context)
                return {'status': 'success', 'message': 'Microsoft login Successflly', "data": serializer.context}
        except Exception as e:
            return {'status': 'error', 'message': 'Login via Microsoft is not Successfull' + str(e)}


class TenantMicrosoftSocialAuthView(MicrosoftSocialAuthView):
    @swagger_auto_schema(manual_parameters=[test_param], responses={200: "ok"})
    def post(self, request):
        tenant_data = {}
        schema = SchemaFromRequest(request)
        real_schema = schema
        if schema == 'public':
            data = CreateTenant(request)
            if data.__len__() == 1:
                schema = data[0]
            else:
                tenant, tenant_data = data
                schema = tenant.schema_name
        with schema_context(schema):
            data = super(TenantMicrosoftSocialAuthView, self).execute(request, real_schema)
            if data['status'] == 'success':
                data['data']['company'] = tenant_data if real_schema == 'public' else SchemaToName(schema)
                if real_schema == 'public':
                    data['message'] = 'Signup is Successful'
                return Response(data, status.HTTP_200_OK)
            else:
                return Response(data, status.HTTP_400_BAD_REQUEST)
