from django.shortcuts import render
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, mixins, status
# Create your views here.
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from Multitenant.classes import SchemaFromRequest, SchemaToTenant
from Utilities.api_response import api_exception, APISuccess, tenant_api_exception, tenant_api
from accounts.models import User
from accounts.views import authorization_header, image_upload, video_upload, company_header
from general.serializers import AddProductSerializer, ProductSerializer, PlanSerializer, AddPlanSerializer, \
    SubscribeSerializer, SubscriptionSerializer, RemoveUserSubscriptionSerializer, AssignUserSubscriptionSerializer, \
    CancelSubscriptionsSerializer, ConfirmSubSerializer


class AddProductAPI(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = AddProductSerializer
    queryset = AddProductSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated, )
    parser_classes = (MultiPartParser, )

    @swagger_auto_schema(manual_parameters=[authorization_header, image_upload, video_upload])
    @api_exception
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        serializer = ProductSerializer(product)
        return APISuccess(message='Product created successfully', data=serializer.data, status=status.HTTP_201_CREATED)


class UpdateProductAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AddProductSerializer
    queryset = AddProductSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated,)
    http_method_names = ('patch', )
    parser_classes = (MultiPartParser,)

    @swagger_auto_schema(manual_parameters=[authorization_header, image_upload, video_upload])
    @api_exception
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        serializer = ProductSerializer(product)
        return APISuccess(message="Product has been updated successfully.", data=serializer.data,
                          status=status.HTTP_200_OK)


class ReadDeleteProductAPI(mixins.DestroyModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProductSerializer
    queryset = ProductSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[authorization_header, company_header ],
                         responses={200: "Ok", 401: "Unauthorized"})
    @tenant_api_exception
    def list(self, request, *args, **kwargs):
        return mixins.ListModelMixin.list(self, request, *args, **kwargs)

    @swagger_auto_schema(manual_parameters=[authorization_header, company_header],
                         responses={200: "Ok", 401: "Unauthorized"})
    @tenant_api_exception
    def retrieve(self, request, *args, **kwargs):
        return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)

    @swagger_auto_schema(manual_parameters=[authorization_header],
                         responses={200: "Ok", 401: "Unauthorized"})
    @api_exception
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APISuccess(message="Deleted successfully", status=status.HTTP_204_NO_CONTENT)

class AddPlanAPI(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = AddPlanSerializer
    queryset = AddPlanSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated, )
    parser_classes = (MultiPartParser,)

    @swagger_auto_schema(manual_parameters=[authorization_header,])
    @api_exception
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        serializer = PlanSerializer(product)
        return APISuccess(message='Plan created successfully', data=serializer.data, status=status.HTTP_201_CREATED)


class UpdatePlanAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AddPlanSerializer
    queryset = AddPlanSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser,)

    @swagger_auto_schema(manual_parameters=[authorization_header])
    @api_exception
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        serializer = PlanSerializer(product)
        return APISuccess(message="Plan has been updated successfully.", data=serializer.data,
                          status=status.HTTP_200_OK)


class ReadDeletePlanAPI(mixins.DestroyModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = PlanSerializer
    queryset = PlanSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[authorization_header,company_header ],
                         responses={200: "Ok", 401: "Unauthorized"})
    @tenant_api_exception
    def list(self, request, *args, **kwargs):
        return mixins.ListModelMixin.list(self, request, *args, **kwargs)

    @swagger_auto_schema(manual_parameters=[authorization_header, company_header ],
                         responses={200: "Ok", 401: "Unauthorized"})
    @tenant_api_exception
    def retrieve(self, request, *args, **kwargs):
        return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)

    @swagger_auto_schema(manual_parameters=[authorization_header, ],
                         responses={200: "Ok", 401: "Unauthorized"})
    @api_exception
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APISuccess(message="Deleted successfully", status=status.HTTP_204_NO_CONTENT)


class SubscribeAPI(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscribeSerializer
    queryset = SubscribeSerializer.Meta.model.objects.all()
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
                         responses={201: "Created", 401: "Unauthorized"})
    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.context['company'] = SchemaToTenant(SchemaFromRequest(request))
        serializer.context['user'] = request.user
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()
        sub_serializer = SubscriptionSerializer(subscription[1], many=True)
        data = {"transaction": subscription[0], "subscriptions": sub_serializer.data}
        return APISuccess(message='License purchase was successful', data=data, status=status.HTTP_201_CREATED)


class RemoveUserSubscriberAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = RemoveUserSubscriptionSerializer
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    http_method_names = ('patch', )
    parser_classes = (MultiPartParser,)

    @swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
                         responses={200: "Ok", 401: "Unauthorized"})
    @tenant_api
    def partial_update(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.context['user_id'] = kwargs['pk']
        serializer.context['company'] = SchemaToTenant(SchemaFromRequest(request))
        serializer.is_valid(raise_exception=True)
        data = serializer.execute()
        return APISuccess(message='user licence successfully removed', data=data, status=status.HTTP_200_OK)


class ReadLicenseAPI(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = SubscriptionSerializer
    queryset = SubscriptionSerializer.Meta.model.objects.all().order_by('plan__product')
    permission_classes = (IsAuthenticated,)

    @swagger_auto_schema(manual_parameters=[authorization_header])
    @api_exception
    def list(self, request, *args, **kwargs):
        return mixins.ListModelMixin.list(self, request, *args, **kwargs)

    @swagger_auto_schema(manual_parameters=[authorization_header, ])
    @api_exception
    def retrieve(self, request, *args, **kwargs):
        return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)


class AssignUserSubscriberAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = AssignUserSubscriptionSerializer
    queryset = User.objects.all()
    permission_classes = (IsAuthenticated,)
    http_method_names = ('patch', )
    parser_classes = (MultiPartParser,)

    @swagger_auto_schema(manual_parameters=[company_header, authorization_header])
    @tenant_api
    def partial_update(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.context['user_id'] = kwargs['pk']
        serializer.context['company'] = SchemaToTenant(SchemaFromRequest(request))
        serializer.is_valid(raise_exception=True)
        data = serializer.execute()
        return APISuccess(message='user licence successfully assigned', data=data, status=status.HTTP_200_OK)


class CancelSubscriptionsAPI(APIView):
    permission_classes = (IsAuthenticated, )
    http_method_names = ('delete',)

    product_id = openapi.Parameter(name="id", in_=openapi.IN_PATH, type=openapi.TYPE_NUMBER, required=True,
                           description="Product ID")
    @swagger_auto_schema(manual_parameters=[company_header, authorization_header, product_id])
    @tenant_api_exception
    def delete(self, request, *args, **kwargs):
        serializer = CancelSubscriptionsSerializer(data=request.data)
        serializer.context['user'] = request.user
        serializer.context['company'] = SchemaToTenant(SchemaFromRequest(request))
        serializer.context['product_id'] = kwargs['id']
        serializer.is_valid(raise_exception=True)
        data = serializer.execute()
        return APISuccess(message='Product Licences cancelled successfully', data=data['company'], status=status.HTTP_200_OK)




class SendConfirmationTest(APIView):
    permission_classes = (IsAuthenticated, )
    http_method_names = ('post', )
    parser_classes = (MultiPartParser, )

    @swagger_auto_schema(request_body=ConfirmSubSerializer, manual_parameters=[company_header, authorization_header])
    @tenant_api
    def post(self, request, *args, **kwargs):
        serializer = ConfirmSubSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.execute()
        return APISuccess(message='Test Confirmation sent successfully', data=data, status=status.HTTP_200_OK)