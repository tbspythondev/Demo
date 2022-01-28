import json
from collections import OrderedDict
from datetime import timedelta

import django_filters
import pandas
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth.models import Permission
# RESTFRAMEWORK imports
# RESTFRAMEWORK imports
from django.db.models import Value
from django.db.models.functions import Concat
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from django_tenants.utils import schema_context
from drf_yasg import openapi
from drf_yasg.inspectors import PaginatorInspector
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework import viewsets, mixins
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from Multitenant.classes import CreateTenant, SchemaFromRequest, SchemaToName
# Other imports
from Permission.permissions import assign_profile, query_to_json
# from Permission.permissions import get_remain_permission
# Model imports
from Utilities.api_response import tenant_api, tenant_api_exception, APISuccess, APIFailure, api_exception
from Utilities.utils import create_default_profiles
from Utilities.utils import deviceDetails
from common.utils.utilities import StandardResultsSetPagination, LimitOffsetPaginatorInspectorClass
from .models import User, Tag, Role, Profile, UserGroup, USER_CHOICES
# Serializers imports
from .serializers import (UserSerializer, LoginSerializer, CRMUsersignupSerializer,
						  TokenObtainPairSerializer, CreateProfileSerializer,
						  UpdateProfileSerializer,
						  AddUserPermissionSerializer, TagSerializer, UpdateTagSerializer, AddTagSerializer,
						  RoleSerializer,
						  UpdateRoleSerializer,
						  AddRoleSerializer, ContentTypeSerializer,
						  AssignProfileSerializer,
						  UserProfileSerializer,
						  UpdateDefaultProfileSerializer, ProfileSerializer, CreateUserGroupSerializer,
						  UserGroupSerializer, UpdateUserGroupSerializer, AddRemoveUsersInGroupSerializer,
						  UserInviteSerializer, UserInvitationSerializer, ChangeUserPasswordSerializer,
						  ActivateDeactivateUserSerializer, UserEditBasicDetailSerializer, UserEmailSerializer,
						  UserMobileSerializer, UserUploadProfilePicSerializer, AdminResetPasswordSerializer,
						  SetPrimaryContactsSerializer)

# from Permission.permissions import get_remain_permission

company_header = openapi.Parameter('company', openapi.IN_HEADER, description="company for schema",
								   type=openapi.TYPE_STRING)
choice_query = openapi.Parameter('choice', openapi.IN_QUERY, description="oprions are : all_users, active_users, inactive_users, custom_users, admin_users",
								   type=openapi.TYPE_STRING)
authorization_header = openapi.Parameter('authorization', openapi.IN_HEADER, description="Authorization for Login",
										 type=openapi.TYPE_STRING)

file_upload = openapi.Parameter(name="file", in_=openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
								description="Supported files - (csv, xls, xlsx)")
image_upload = openapi.Parameter(name="image", in_=openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
								description="Supported images- ('jpg, png, jpeg, webp')")
video_upload = openapi.Parameter(name="video", in_=openapi.IN_FORM, type=openapi.TYPE_FILE, required=False,
								description="Supported videos- ('3gp, mp4, webm')")


# Create your views here.
class UserAPI(viewsets.ModelViewSet):
	queryset = User.objects.all()
	serializer_class = UserSerializer

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def update(self, request, *args, **kwargs):
		return viewsets.ModelViewSet.update(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		return viewsets.ModelViewSet.partial_update(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def destroy(self, request, *args, **kwargs):
		return viewsets.ModelViewSet.destroy(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def list(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())
		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = UserProfileSerializer(page, many=True)
			return self.get_paginated_response(serializer.data)

		serializer = UserProfileSerializer(queryset, many=True)
		return Response(serializer.data)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = UserProfileSerializer(instance)
		return Response(serializer.data)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		try:
			data = request.data
			# validation for duplicate email
			user_obj = User.objects.filter(email=data.get('email')).exists()
			if user_obj:
				return Response({'status': "error",
								 'message': 'User with this email already exists, Please try a new one'},
								status=status.HTTP_400_BAD_REQUEST)

			serializer = UserSerializer(data=data, partial=True)
			serializer.context['company'] = SchemaToName(SchemaFromRequest(request))
			if serializer.is_valid(raise_exception=True):
				serializer.save()
				# Email with credential sent to the User with change password link
				# print(serializer.data['email'])
				user = User.objects.get(email=data['email'])
				print(user.id)
				# result = sendmail(user.id, data)
				result = True
				if result == True:
					create_default_profiles()
					standard = Profile.objects.get(name='standard')
					assign_profile(user, standard)
					return Response(
						{'status': 'success', 'message': 'user Created Successfully, Kindly check your mail',
						 'data': {'user': serializer.data}}, status=status.HTTP_201_CREATED)
				else:
					return Response({'status': 'error', 'message': result}, status=status.HTTP_400_BAD_REQUEST)
		except Exception as e:
			print(e)
			return Response({'status': 'error', 'message': str(e)},
							status=status.HTTP_400_BAD_REQUEST)


class CreateCRMAdmin(viewsets.ModelViewSet):
	queryset = User.objects.all()
	serializer_class = CRMUsersignupSerializer
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		try:
			data = self.create_crm_admin(request.data)
			if data['status'] == 'error':
				return Response(data, status.HTTP_400_BAD_REQUEST)
			else:
				return Response(data, status.HTTP_201_CREATED)
		except Exception as e:
			print(e)
			return Response({'status': e, 'message': 'CRM User Not Created Successfully'},
							status=status.HTTP_400_BAD_REQUEST)

	def create_crm_admin(self, data, company=None):
		user_obj = User.objects.filter(email=str(data.get('email'))).exists()
		if user_obj:
			return {'status': "error",
					'message': 'User with this email already exists, Please try a new one'}

		serializer = CRMUsersignupSerializer(data=data, partial=True)
		serializer.context['company'] = company
		if serializer.is_valid(raise_exception=True):
			serializer.save()
			# Email with credential sent to the User with change password link
			# print(serializer.data['email'])
			user = User.objects.get(email=data['email'])
			# Send mail with credentials
			# result = sendmail(user.id, data)
			result = True
			if result == True:
				create_default_profiles()
				admin_profile = Profile.objects.get(name='administrator')
				assign_profile(user, admin_profile)
				return {'status': 'success', 'message': 'CRM User Created Successflly, Kindly check your mail',
						'data': {'user': serializer.data}}

			else:
				return {'status': 'error', 'message': result}


class TenantCreateCRMAdmin(CreateCRMAdmin):
	@api_exception
	def create(self, request, *args, **kwargs):
		tenant_data = {}
		schema = SchemaFromRequest(request)
		if schema == 'public':
			data = CreateTenant(request)
			if data.__len__() == 1:
				schema = data[0]
			else:
				tenant, tenant_data = data
				schema = tenant.schema_name
		with schema_context(schema):
			company = SchemaToName(schema)
			data = super(TenantCreateCRMAdmin, self).create_crm_admin(request.data, company)
			if data['status'] == 'error':
				return Response(data, status.HTTP_400_BAD_REQUEST)
			else:
				if tenant_data != {}:
					data['data']['company'] = tenant_data
				return Response(data, status.HTTP_201_CREATED)


class UserLogin(viewsets.ModelViewSet):
	queryset = User.objects.all()
	serializer_class = LoginSerializer
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		data = request.data
		serializer = LoginSerializer(data=data)
		try:
			if serializer.is_valid(raise_exception=True):
				email = serializer.data['email']
				password = serializer.data['password']

				user = authenticate(email=email, password=password)
				if user is None:
					return Response(
						{'status': 'error', 'message': 'User account does not exist, Kindly check credentials'},
						status=status.HTTP_400_BAD_REQUEST)

				obj = TokenObtainPairSerializer()
				token = obj.validate({"email": email, "password": password})

				login(request, user)
				result = deviceDetails(request, user)
				print(result)
				result = "success"
				if result == "success":
					return Response({'status': 'success', 'message': 'User login Successflly', 'token': token},
									status=status.HTTP_200_OK)
				else:
					return Response({'status': 'error', 'message': "error"}, status=status.HTTP_400_BAD_REQUEST)

		except Exception as e:
			print(e)
			return Response({'status': 'error', 'message': str(e)},
							status=status.HTTP_400_BAD_REQUEST)


# Profile and Permissions
class CreateProfileAPIView(viewsets.ModelViewSet):
	queryset = Profile.objects.all()
	serializer_class = CreateProfileSerializer
	permission_classes = [IsAuthenticated, ]
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		data = request.data
		serializer = CreateProfileSerializer(data=data)
		if serializer.is_valid(raise_exception=True):
			profile = serializer.save()
			serializer = ProfileSerializer(profile)
			return APISuccess(message="Profile created successfully", data=serializer.data,
							status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors)

class UpdateProfileAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	serializer_class = UpdateProfileSerializer
	permission_classes = [IsAuthenticated, ]
	queryset = Profile.objects.all()
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.serializer_class(data=request.data, instance=instance, partial=partial)
		if serializer.is_valid(raise_exception=True):
			profile = serializer.save()
			serializer = ProfileSerializer(profile)
			return APISuccess(message="Profile has been updated successfully", data=serializer.data,
							status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors)

class GetUsers(mixins.ListModelMixin, viewsets.GenericViewSet):
	permission_classes = [IsAuthenticated, ]
	serializer_class = UserProfileSerializer
	queryset = User.objects.all()

	def get_queryset(self):
		choices_list=['all_users', 'active_users', 'inactive_users', 'custom_users','admin_users']
		choice = self.request.query_params.get('choice')
		if choice == 'admin_users' and choice in choices_list:
			queryset = User.objects.filter(is_superuser=True)
		elif choice == 'active_users' and choice in choices_list:
			queryset = User.objects.filter(is_active=True)
		elif choice == 'inactive_users' and choice in choices_list:
			queryset = User.objects.filter(is_active=False)
		elif choice == 'custom_users' and choice in choices_list:
			queryset = User.objects.filter()
		elif choice == 'all_users' and choice in choices_list:
			queryset = User.objects.all()
		else:
			return APIFailure(message="Please Enter valid choice", status=status.HTTP_400_BAD_REQUEST)
		return queryset

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, choice_query], responses={200: "ok"})
	@tenant_api
	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)

class AddUserPermissionAPIView(mixins.CreateModelMixin, viewsets.GenericViewSet):
	permission_classes = [IsAuthenticated, ]
	serializer_class = AddUserPermissionSerializer
	queryset = User.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			action = serializer.validated_data['action']
			prep = 'to' if action == 'assign' else 'from'
			verb = 'ed' if action == 'assign' else 'd'

			if action == 'assign':
				users = serializer.assign(serializer.validated_data)
			else:
				users = serializer.remove(serializer.validated_data)
			serializer = UserProfileSerializer(users, many=True)
			return APISuccess(message=f"Custom Permissions {action}{verb} {prep} users successfully",
							  data=serializer.data, status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetAllProfilesAPI(mixins.ListModelMixin, viewsets.GenericViewSet):
	queryset = Profile.objects.all()
	permission_classes = [IsAuthenticated, ]
	serializer_class = ProfileSerializer

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)

class PermissionsForModule(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = ContentTypeSerializer
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid():
			object_ = str(request.data.get('module')).lower()
			permissions = Permission.objects.filter(codename__contains=object_).all()
			data = query_to_json(permissions)
			return APISuccess(message=f"code names for {object_} retrieved successfully.",
							  data=data, status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AssignProfileToUsers(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = AssignProfileSerializer
	queryset = User.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			users = serializer.assign(serializer.validated_data)
			user_profile = UserProfileSerializer(instance=users, many=True).data
			return APISuccess(message="Profile Assigned to users successfully",
							  data=user_profile, status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateDefaultProfile(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = UpdateDefaultProfileSerializer
	queryset = Profile.objects.filter(name__in=['standard', 'administrator'])

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			instance = serializer.update_profile(serializer.validated_data)
			serializer = ProfileSerializer(instance=instance)
			return APISuccess(message='Default Profile has been updated successfully', data=serializer.data,
							  status=status.HTTP_200_OK)
		else:
			APIFailure(message=serializer.errors)


# roles and tags

class CreateRoleApi(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = AddRoleSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Role.objects.all().order_by('-up_line')

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = AddRoleSerializer(data=request.data)
		if serializer.is_valid(raise_exception=True):
			role = serializer.save()
			return APISuccess(message="Role created successfully",
							  data=RoleSerializer(instance=role).data, status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateRoleApi(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	serializer_class = UpdateRoleSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Role.objects.all().order_by('-up_line')
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.is_valid(raise_exception=True)
		role = serializer.save()

		if getattr(instance, '_prefetched_objects_cache', None):
			# If 'prefetch_related' has been applied to a queryset, we need to
			# forcibly invalidate the prefetch cache on the instance.
			instance._prefetched_objects_cache = {}

		return APISuccess(message="Role updated successfully", data=RoleSerializer(role).data,
						  status=status.HTTP_200_OK)


class RetrieveRoleApi(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
	serializer_class = RoleSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Role.objects.all().order_by('-up_line')

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def retrieve(self, request, *args, **kwargs):
		return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)


class RolesApi(mixins.ListModelMixin, viewsets.GenericViewSet):
	serializer_class = RoleSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Role.objects.all().order_by('-up_line')

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)


class DeleteRoleApi(mixins.DestroyModelMixin, viewsets.GenericViewSet):
	serializer_class = RoleSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Role.objects.all().order_by('-up_line')

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def destroy(self, request, *args, **kwargs):
		return mixins.DestroyModelMixin.destroy(self, request, *args, **kwargs)


class TagApi(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
	queryset = Tag.objects.all()
	permission_classes = (IsAuthenticated,)
	serializer_class = TagSerializer

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def retrieve(self, request, *args, **kwargs):
		return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)


class CreateTagApi(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = AddTagSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Tag.objects.all()
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = AddTagSerializer(data=request.data)
		if serializer.is_valid(raise_exception=True):
			tag = serializer.save()
			return APISuccess(message="Tag created successfully.", data=TagSerializer(instance=tag).data,
							  status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UpdateTagApi(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	serializer_class = UpdateTagSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Tag.objects.all()
	http_method_names = ('patch',)
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.is_valid(raise_exception=True)
		tag = serializer.save()

		if getattr(instance, '_prefetched_objects_cache', None):
			# If 'prefetch_related' has been applied to a queryset, we need to
			# forcibly invalidate the prefetch cache on the instance.
			instance._prefetched_objects_cache = {}

		return APISuccess(message="Tag has been updated successfully.", data=TagSerializer(tag).data,
						  status=status.HTTP_200_OK)


class DeleteTagApi(mixins.DestroyModelMixin, viewsets.GenericViewSet):
	serializer_class = TagSerializer
	permission_classes = (IsAuthenticated,)
	queryset = Tag.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def destroy(self, request, *args, **kwargs):
		return mixins.DestroyModelMixin.destroy(self, request, *args, **kwargs)



# user groups

class CreateUserGroupAPI(mixins.CreateModelMixin, viewsets.GenericViewSet):
	serializer_class = CreateUserGroupSerializer
	permission_classes = (IsAuthenticated,)
	queryset = UserGroup.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def create(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data)
		if serializer.is_valid(raise_exception=True):
			user_group = serializer.save()
			serializer = UserGroupSerializer(user_group)
			return APISuccess(message='User Group created successfully.', data=serializer.data, status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors)

class UpdateUserGroupAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	serializer_class = UpdateUserGroupSerializer
	permission_classes = (IsAuthenticated,)
	queryset = UserGroup.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def update(self, request, *args, **kwargs):
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		if serializer.is_valid(raise_exception=True):
			user_group = serializer.save()
			serializer = UserGroupSerializer(user_group)
			return APISuccess(message='User Group updated successfully.', data=serializer.data, status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		return self.update(request, *args, **kwargs)


class RDUserGroupAPI(mixins.RetrieveModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
	serializer_class = UserGroupSerializer
	permission_classes = (IsAuthenticated,)
	queryset = UserGroup.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def list(self, request, *args, **kwargs):
		return mixins.ListModelMixin.list(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def destroy(self, request, *args, **kwargs):
		return mixins.DestroyModelMixin.destroy(self, request, *args, **kwargs)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def retrieve(self, request, *args, **kwargs):
		return mixins.RetrieveModelMixin.retrieve(self, request, *args, **kwargs)

class AddRemoveUserInGroupAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	http_method_names = ('patch',)
	serializer_class = AddRemoveUsersInGroupSerializer
	permission_classes = (IsAuthenticated,)
	queryset = UserGroup.objects.all()

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], responses={200: "ok"})
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.context['user_group_id'] = kwargs['pk']
		if serializer.is_valid(raise_exception=True):
			user_group = serializer.save()
			serializer = UserGroupSerializer(user_group)
			if request.data['action'] == 'add':
				return APISuccess(message='The selected users have been added to the group successfully.', data=serializer.data,
								  status=status.HTTP_200_OK)
			if request.data['action'] == 'remove':
				return APISuccess(message='The selected users have been removed from the group successfully.', data=serializer.data,
								  status=status.HTTP_200_OK)
		else:
			return APIFailure(message=serializer.errors)


class InviteUserApiView(APIView):
	permission_classes = (IsAuthenticated,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header], request_body=UserInviteSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def post(self, request, *args, **kwargs):
		serializer = UserInviteSerializer(data=request.data)
		if serializer.is_valid(raise_exception=True):
			serializer.save()
			return APISuccess(message="Invitation Sent.", data=serializer.data, status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BulkInviteUserApiView(APIView):
	permission_classes = (IsAuthenticated,)
	parser_classes = (MultiPartParser, )

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, file_upload],
						 operation_description="File Upload for Bulk Invite",
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def post(self, request, *args, **kwargs):
		up_file = request.FILES['file']
		file_name = up_file.name
		extension = file_name.split(".")[-1]
		available_extensions = ['csv', 'xls', 'xlsx', ]
		if extension.lower() not in available_extensions:
			return APIFailure(message="File format not supported. Please use - {} files".format(available_extensions),
							  status=status.HTTP_400_BAD_REQUEST)

		if extension.lower() == 'csv':
			df = pandas.read_csv(up_file)
		else:
			df = pandas.read_excel(up_file, engine='openpyxl')

		json_data = df.to_json(orient='records')
		json_data = json.loads(json_data)
		errors = []
		for row in json_data:
			if not User.objects.filter(email=row['email']).exists():
				serializer = UserInviteSerializer(data=row)
				if serializer.is_valid():
					serializer.save()
				else:
					errors.append(serializer.errors)
			else:
				errors.append("User with email {} exists.".format(row['email']))
		if errors:
			return APIFailure(message=errors, status=status.HTTP_400_BAD_REQUEST)
		return APISuccess(message="Invitation Sent.", data=json_data, status=status.HTTP_201_CREATED)


class InviteUserFromKeyApiView(APIView):
	permission_classes = (IsAuthenticated,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=UserInvitationSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def post(self, request, *args, **kwargs):
		serializer = UserInvitationSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return APISuccess(message="User added to CRM.", status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFilter(FilterSet):
	full_name = django_filters.CharFilter(method='full_name_lookup')
	user_type = django_filters.CharFilter(method='choice_lookup')

	class Meta:
		model = User
		fields = (
			'full_name',
			'user_type'
		)

	def choice_lookup(self, queryset, name, value):
		value_map = {v: k for k, v in USER_CHOICES}
		value = value_map.get(value, 'None')
		return queryset.filter(user_type=value)

	def full_name_lookup(self, queryset, name, value):
		return queryset.annotate(full_name=Concat('first_name', Value(' '), 'last_name')).filter(full_name__icontains=value)


class UserListApiView(ListAPIView):
	permission_classes = (IsAuthenticated,)
	queryset = User.objects.all()
	serializer_class = UserProfileSerializer
	pagination_class = StandardResultsSetPagination
	filter_backends = (
		DjangoFilterBackend,
	)
	filter_class = UserFilter

	@swagger_auto_schema(pagination_class=StandardResultsSetPagination,
						 paginator_inspectors=[LimitOffsetPaginatorInspectorClass, ],
						 manual_parameters=[company_header, authorization_header, ])
	@tenant_api_exception
	def get(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())
		page = self.paginate_queryset(queryset)
		serializer = UserProfileSerializer(page, many=True)
		return self.get_paginated_response(serializer.data)


class ActivateDeactivateUserAPI(mixins.UpdateModelMixin, viewsets.GenericViewSet):
	permission_classes = (IsAuthenticated,)
	queryset = User.objects.all()
	serializer_class = ActivateDeactivateUserSerializer
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ])
	@tenant_api_exception
	def partial_update(self, request, *args, **kwargs):
		kwargs['partial'] = True
		partial = kwargs.pop('partial', False)
		instance = self.get_object()
		serializer = self.get_serializer(instance, data=request.data, partial=partial)
		serializer.is_valid(raise_exception=True)
		verb = 'activated' if serializer.validated_data['is_active'] else 'deactivated'
		user = serializer.save()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message=f'This user has been {verb} successfully.',
						  status=status.HTTP_200_OK)


class ChangeUserPasswordAPI(APIView):
	permission_classes = (IsAuthenticated,)
	parser_classes = (MultiPartParser,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=ChangeUserPasswordSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def post(self, request, *args, **kwargs):
		serializer = ChangeUserPasswordSerializer(data=request.data)
		serializer.context['user'] = request.user
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message='Password changed successfully.', status=status.HTTP_200_OK)



class UserEditBasicDetailsAPI(APIView):
	permission_classes = (IsAuthenticated, )
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=UserEditBasicDetailSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		serializer = UserEditBasicDetailSerializer(data=request.data)
		serializer.context['user'] = request.user
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message='Your Details have been updated successfully', status=status.HTTP_200_OK)


class UserEditEmailAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=UserEmailSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api
	def patch(self, request, *args, **kwargs):
		serializer = UserEmailSerializer(data=request.data)
		serializer.context['user'] = request.user
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message=f'Your have {request.data["action"]}ed your email successfully',
						  status=status.HTTP_200_OK)

class UserEditMobileAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=UserMobileSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		serializer = UserMobileSerializer(data=request.data)
		serializer.context['user'] = request.user
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message=f'Your have {request.data["action"]}ed your mobile number successfully',
						  status=status.HTTP_200_OK)


class SetPrimaryContactsAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ('patch',)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=SetPrimaryContactsSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		serializer = SetPrimaryContactsSerializer(data=request.data)
		serializer.context['user'] = request.user
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message=f'contact is now the primary contact.',
						  status=status.HTTP_200_OK)

class DeleteUserAPI(APIView):
	permission_classes = (IsAuthenticated, )
	http_method_names = ('patch', )

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		user = User.objects.filter(id=kwargs['id']).first()
		if user is None:
			return APIFailure(message='This user does not exist.')
		user.deletion_date = (timezone.now() + timedelta(days=30)).date()
		user.is_active = False
		user.save()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message='This user has been scheduled to be deleted in 30 days',
						  status=status.HTTP_200_OK)

class RestoreUserAPI(APIView):
	permission_classes = (IsAuthenticated, )
	http_method_names = ('patch', )

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		user = User.objects.filter(id=kwargs['id']).first()
		if user is None:
			return APIFailure(message='This user does not exist.')
		user.deletion_date = None
		user.is_active = True
		user.save()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message='This user has been restored successfully',
						  status=status.HTTP_200_OK)


class UploadUserProfilePicAPI(APIView):
	permission_classes = (IsAuthenticated,)
	http_method_names = ('patch',)
	parser_classes = (MultiPartParser, )

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, image_upload ],
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api_exception
	def patch(self, request, *args, **kwargs):
		image_file = request.FILES['image']
		serializer = UserUploadProfilePicSerializer(data={})
		serializer.context['user'] = request.user
		serializer.context['image'] = image_file
		serializer.context['schema'] = SchemaFromRequest(request)
		serializer.is_valid(raise_exception=True)
		user = serializer.execute()
		serializer = UserProfileSerializer(user)
		return APISuccess(data=serializer.data, message='User Profile Picture Updated Successfully.',
						  status=status.HTTP_200_OK)

class ResetPasswordApiView(APIView):
	permission_classes = (IsAuthenticated,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ],
						 request_body=AdminResetPasswordSerializer,
						 responses={201: "Created", 401: "Unauthorized"})
	@tenant_api
	def post(self, request, *args, **kwargs):
		serializer = AdminResetPasswordSerializer(data=request.data)
		if serializer.is_valid(raise_exception=True):
			serializer.reset_password()
			return APISuccess(message="Password Reset Done.", status=status.HTTP_201_CREATED)
		else:
			return APIFailure(message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileAPI(APIView):
	permission_classes = (IsAuthenticated,)

	@swagger_auto_schema(manual_parameters=[company_header, authorization_header, ])
	@tenant_api_exception
	def get(self, request, *args, **kwargs):
		serializer = UserProfileSerializer(request.user)
		return APISuccess(message='User Profile details retrieved successfully.', data=serializer.data)