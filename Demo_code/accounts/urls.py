# accounts/urls.py

from django.contrib.auth.decorators import login_required
from django.urls import path
# RESTFRAMEWORK imports
from rest_framework.routers import DefaultRouter

# View and other imports
from .views import *

app_name = 'accounts'

router = DefaultRouter()
router.register(r'user', UserAPI, basename="user")
router.register('role/create', CreateRoleApi, basename='role')
router.register('roles', RolesApi, basename='role')
router.register('role/update', UpdateRoleApi, basename='role')
router.register('role/delete', DeleteRoleApi, basename='role')
router.register('role', RetrieveRoleApi, basename='role')
router.register('tag/create', CreateTagApi, basename='tag')
router.register('tags', TagApi, basename='tag')
router.register('tag/update', UpdateTagApi, basename='tag')
router.register('tag/delete', DeleteTagApi, basename='tag')
router.register('permission/module', PermissionsForModule, basename='permission')
router.register('assign_profile', AssignProfileToUsers, basename='profile')
router.register('group', RDUserGroupAPI, basename='group')

router.register('profiles', GetAllProfilesAPI, basename='profile')
router.register('assign_custom_permission', AddUserPermissionAPIView, basename='permission')
router.register('users', GetUsers, basename='user')




urlpatterns = [
    path('login/',UserLogin.as_view({'post': 'create'}),name="login"),
    path('create_crm_admin/',TenantCreateCRMAdmin.as_view({'post': 'create'}),name="create_crm_admin"),
    path('user/change_password/', ChangeUserPasswordAPI.as_view(), name='change_user_password'),
    path('user/edit/', UserEditBasicDetailsAPI.as_view(), name="edit_user_details"),
    path('user/contact/email/', UserEditEmailAPI.as_view(), name="edit_user_email"),
    path('user/contact/mobile/', UserEditMobileAPI.as_view(), name="edit_user_mobile"),
    path('user/contact/primary/', SetPrimaryContactsAPI.as_view(), name="make_primary_contact" ),
    path('user/<int:id>/delete/', DeleteUserAPI.as_view(), name="admin_delete_user"),
    path('user/<int:id>/restore/', RestoreUserAPI.as_view(), name="admin_restore_user"),
    path('user/upload_profile_pic/', UploadUserProfilePicAPI.as_view(), name='user_upload_pic'),
    path('user/profile_details/', UserProfileAPI.as_view(), name='user_profile'),

    path('create_profile/',CreateProfileAPIView.as_view({'post': 'create'}),name="create_profile"),
    path('update_default_profile/', UpdateDefaultProfile.as_view({'post': 'create'}), name="update_default_profile"),
    path('profile/<int:pk>/update', UpdateProfileAPI.as_view({'patch': 'partial_update'}), name="update_profile"),

    path('group/create/', CreateUserGroupAPI.as_view({"post": "create"}), name="create_group"),
    path('group/<int:pk>/patch/', UpdateUserGroupAPI.as_view({"patch": "partial_update"}), name="patch_group"),
    path('group/<int:pk>/update/', UpdateUserGroupAPI.as_view({"put": "update"}), name="update_group"),
    path('group/<int:pk>/add_or_remove/', AddRemoveUserInGroupAPI.as_view({"patch": "partial_update"}), name="user_group_action"),

    path('invite/', InviteUserApiView.as_view(), name="invite_user"),
    path('invite_from_key/', InviteUserFromKeyApiView.as_view(), name="invite_user_from_key"),
    path('bulk_invite/', BulkInviteUserApiView.as_view(), name="bulk_invite_user"),
    path('user_list/', UserListApiView.as_view(), name="user_list"),

    path('user/<int:pk>/activate/', ActivateDeactivateUserAPI.as_view({"patch": "partial_update"}), name="activate_user"),

    path('user_reset_password/', ResetPasswordApiView.as_view(), name="user_reset_password"),

]
urlpatterns += router.urls

