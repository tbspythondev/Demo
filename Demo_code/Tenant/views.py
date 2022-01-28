from django.shortcuts import render
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, mixins, status

# Create your views here.
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from Multitenant.classes import SchemaFromRequest, SchemaToTenant
from Tenant.models import Company
from Tenant.serializer import EditCompanySerializer, CompanySerializer, CompanyUploadImageSerializer, \
	BasicCompanySerializer
from Utilities.api_response import APISuccess, tenant_api_exception, api_exception, tenant_api
from accounts.views import company_header, authorization_header, image_upload


class EditCompanyDetailsAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	http_method_names = ('patch',)
	serializer_class = EditCompanySerializer
	permission_classes = (IsAuthenticated,)
	queryset = Company.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=True)
		serializer.context['company'] = SchemaToTenant(SchemaFromRequest(request))
		serializer.is_valid(raise_exception=True)
		company = serializer.save()
		serializer = CompanySerializer(company)
		return APISuccess(message="Company has been updated successfully.", data=serializer.data,
							  status=status.HTTP_200_OK)


class UploadCompanyImageAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ('patch',)
	parser_classes = (MultiPartParser, )

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, image_upload ],
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api
	def patch(self, request, *args, **kwargs):
		image_file = request.FILES['image']
		serializer = CompanyUploadImageSerializer(data={})
		serializer.context['company_id'] = kwargs['pk']
		serializer.context['user'] = request.user
		serializer.context['image'] = image_file
		serializer.context['schema'] = SchemaFromRequest(request)
		serializer.is_valid(raise_exception=True)
		company = serializer.execute()
		serializer = CompanySerializer(company)
		return APISuccess(data=serializer.data, message='Company Image Updated Successfully.',
						  status=status.HTTP_200_OK)


class ReadCompanyAPI(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
	serializer_class = BasicCompanySerializer
	queryset = Company.objects.all()
	permission_classes = (IsAuthenticated,)



	@swagger_auto_schema(manual_parameters=[authorization_header],
						 responses={200: "Ok", 401: "Unauthorized"})

	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[authorization_header],
						 responses={200: "Ok", 401: "Unauthorized"})
	@api_exception
	def retrieve(self, request, *args, **kwargs):
		return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)
