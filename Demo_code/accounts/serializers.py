from django.conf import settings
from django.contrib.auth.models import Permission
# RESTFRAMEWORK imports
# RESTFRAMEWORK imports
from django.core.mail import EmailMessage
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# from Permission.permissions import update_group, assign_permission, assign_perm_to_profile
# Model imports
from Permission.permissions import assign_permission, assign_perm_to_profile, query_to_json, \
    json_to_query, assign_profile, remove_permission
from Tenant.models import Company
from general.serializers import ProductSerializer, SubscriptionSerializer
from .models import User, Profile, Role, Tag, UserGroup, InvitationLog


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        user.company = self.context['company']
        user.save()
        user.add_new_contact(type_='email', contact_=validated_data['email'])
        user.make_primary_contact(type_='email', contact_=validated_data['email'])
        return user
    def validate(self, initial_data):
        if str(initial_data['password']).__len__() < 8:
            raise Exception('Password must be at least 8 characters.')
        if 'first_name' in initial_data:
            initial_data['first_name'] = str(initial_data['first_name']).title()
        if 'last_name' in initial_data:
            initial_data['last_name'] = str(initial_data['last_name']).title()
        return initial_data

class ExtractUsersSerializer(serializers.ModelSerializer):
    groups = serializers.SerializerMethodField('groups_', read_only=True)
    role = serializers.SerializerMethodField('role_', read_only=True)
    profile = serializers.SerializerMethodField('profile_', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'role', 'profile', 'groups')

    def role_(self, obj):
        return obj.role.name if obj.role is not None else None

    def groups_(self, obj):
        return obj.user_groups().values_list('name', flat=True)

    def profile_(self, obj):
        return obj.profile.name if obj.profile is not None else None



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(style={'input_type': 'password'})


class ChangeUserPasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    old_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('old_password', 'password', 'password2')

    def validate(self, initial_data):
        user = self.context['user']
        if not user.check_password(initial_data['old_password']):
            raise Exception("Old password is incorrect.")
        if initial_data['password'].__len__() < 8 or initial_data['password2'].__len__() < 8 :
            raise Exception('Password must be at least 8 characters.')
        if initial_data['password'] != initial_data['password2']:
            raise Exception("Password fields do not match.")
        return initial_data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

    def execute(self):
        return self.update(self.context['user'], self.validated_data)


class CRMUsersignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name', 'company')

    def create(self, validated_data):
        staff_user = User.objects.create_user(email=validated_data['email'],
                                                   password=validated_data['password'],
                                                   first_name=validated_data['first_name'],
                                                   last_name=validated_data['last_name'],
                                                   company=self.context['company'])
        # staff_user = User.objects.create_staffuser(**validated_data)
        staff_user.add_new_contact(type_='email', contact_=validated_data['email'])
        staff_user.make_primary_contact(type_='email', contact_=validated_data['email'])
        return staff_user

    def validate(self, initial_data):
        if 'email' in initial_data:
            initial_data['email'] = str(initial_data['email']).lower()
            if self.Meta.model.objects.filter(email=initial_data['email']).exists():
                raise Exception('A user already exists with this email')
        if 'password' in initial_data and str(initial_data['password']).__len__() < 8:
                raise Exception('Password must be at least 8 characters.')
        if 'first_name' in initial_data:
            initial_data['first_name'] = str(initial_data['first_name']).title()
        if 'last_name' in initial_data:
            initial_data['last_name'] = str(initial_data['last_name']).title()
        return initial_data


class TokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token


class ProfileSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField('permission_list', read_only=True)
    clone = serializers.SerializerMethodField('cloned_profile', read_only=True)

    class Meta:
        model = Profile
        fields = ('id', 'name', 'clone', 'description', 'permissions')

    def permission_list(self, obj):
        return query_to_json(obj.permissions.all())

    def cloned_profile(self, obj):
        return obj.cloned_profile.name if obj.cloned_profile is not None else None



class CreateProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)
    clone_profile = serializers.CharField(max_length=50, required=True)
    description = serializers.CharField(max_length=255, required=True)
    permissions = serializers.JSONField(default=dict, allow_null=False)

    class Meta:
        model = Profile
        fields = ('name', 'description', 'clone_profile', 'permissions')


    def validate(self, initial_data):
        permissions = None
        if 'clone_profile' in initial_data:
            initial_data['clone_profile'] = str(initial_data['clone_profile']).lower()
            if not Profile.objects.filter(name=initial_data['clone_profile']).exists():
                raise Exception(f'No Profile with the name {initial_data["clone_profile"]} exists.')
        if 'name' in initial_data:
            initial_data['name'] = str(initial_data['name']).lower()
            if Profile.objects.filter(name=initial_data['name']).exists():
                raise Exception(f'A Profile with the name {initial_data["name"]} already exists.')
        if 'permissions' in initial_data:
            permissions = json_to_query(initial_data['permissions'])
            for code_name in permissions.values_list('codename', flat=True):
                if not Permission.objects.filter(codename=code_name).exists():
                    raise Exception(f'No Permission has the code name {code_name}.')
            if self.instance is not None:
                diff = permissions.difference(self.instance.cloned_profile.permissions.all())
                if diff.count() > 0:
                    raise Exception(f'The following permissions; {diff.values_list("codename", flat=True)} '
                               f'are not in the {self.instance.cloned_profile.name} profile.')
        if 'permissions' in initial_data and 'clone_profile' in initial_data:
            clone = Profile.objects.get(name=initial_data['clone_profile'])
            diff = permissions.difference(clone.permissions.all())
            if diff.count() > 0:
                raise Exception(f'The following permissions; {diff.values_list("codename", flat=True)} '
                                             f'are not in the {clone.name} profile.')
        return initial_data

    def create(self, validated_data):
        profile = Profile()
        profile.name = validated_data['name']
        profile.description = validated_data['description']
        profile.cloned_profile = Profile.objects.get(name=validated_data['clone_profile'])
        profile.save()
        permissions = json_to_query(validated_data['permissions'])
        profile.permissions.add(*permissions)
        profile.save()
        return profile

    def update(self, instance, validated_data):
        profile = instance
        if 'name' in validated_data:
            profile.name = validated_data['name']
            profile.save()
        if 'description' in validated_data:
            profile.description = validated_data['description']
            profile.save()
        if 'clone_profile' in validated_data:
            profile.permissions.remove(*profile.cloned_profile.permissions.all())
            profile.cloned_profile = Profile.objects.get(name=validated_data['clone_profile'])
            profile.save()
            profile.permissions.add(*profile.cloned_profile.permissions.all())
            profile.save()
        if 'permissions' in validated_data:
            profile.permissions.clear()
            new_extra = json_to_query(validated_data['permissions'])
            profile.permissions.add(*new_extra)
            profile.save()
        return profile



class UpdateProfileSerializer(CreateProfileSerializer):
    name = serializers.CharField(max_length=50, required=False)
    clone_profile = serializers.CharField(max_length=50, required=False)
    description = serializers.CharField(max_length=255, required=False)
    permissions = serializers.JSONField(default=dict, allow_null=False)


class UpdateDefaultProfileSerializer(serializers.Serializer):
    profile = serializers.CharField()
    permissions = serializers.JSONField(default=dict, allow_null=False)

    def validate(self, initial_data):
        default_permissions = ['standard', 'administrator']
        if not str(initial_data['profile']).lower() in default_permissions:
            raise Exception(f'The profile "{initial_data["profile"]}" is not a default profile.')
        permissions = json_to_query(initial_data['permissions']).values_list('codename', flat=True)
        for code in permissions:
            if not Permission.objects.filter(codename=code).exists():
                raise Exception(f'The permission  "{code}" does not exist')
        return initial_data

    def update_profile(self, validated_data):
        assign_perm_to_profile(profile=str(validated_data['profile']).lower(), permissions=validated_data['permissions'])
        profile = Profile.objects.get(name=str(validated_data['profile']).lower())
        return profile

class AddUserPermissionSerializer(serializers.Serializer):
    user_ids = serializers.ListSerializer(child=serializers.IntegerField(min_value=1),
                                          required=True, help_text='List of user IDs', allow_empty=True)
    permissions = serializers.JSONField(default=dict, allow_null=False)

    action = serializers.ChoiceField(choices=['assign', 'remove'], required=True)

    def validate(self, initial_data):
        permissions = json_to_query(initial_data['permissions'])
        for code in permissions.values_list('codename', flat=True):
            if not Permission.objects.filter(codename=code).exists():
                raise Exception(f'The permission  "{code}" does not exist')
        if 'user_ids' in initial_data:
            for i in initial_data['user_ids']:
                if not User.objects.filter(id=i).exists():
                    raise Exception(f'No user with the ID "{i}" exists.')
                user = User.objects.get(id=i)
                if initial_data['action'] == 'remove':
                    diff = permissions.difference(user.user_permissions.all())
                    if diff.count() > 0:
                        raise Exception(f'The user with ID "{i}" does not have the following custom '
                                                     f'permissions "{diff.values_list("codename", flat=True)}".')
                if initial_data['action'] == 'assign':
                    diff = user.profile.permissions.all().intersection(permissions)
                    if diff.count() > 0:
                        raise Exception(f'The following permissions "{diff.values_list("codename", flat=True)}" '
                                   f'are in the user profile "{user.profile.name}" and cannot be added as custom permissions.')

        return initial_data

    def assign(self, validated_data):
        users = User.objects.filter(id__in=validated_data['user_ids'])
        for user in users:
            assign_permission(user, validated_data['permissions'])
        return users

    def remove(self, validated_data):
        users = User.objects.filter(id__in=validated_data['user_ids'])
        for user in users:
            remove_permission(user, validated_data['permissions'])
        return users



class UserPermissionSerializer(serializers.ModelSerializer):
    profile_permission = serializers.SerializerMethodField('get_profile_permission', read_only=True)
    custom_permission = serializers.SerializerMethodField('get_custom_permission', read_only=True)
    all_permission = serializers.SerializerMethodField('get_all_permission', read_only=True)
    class Meta:
        model = User
        fields = ('profile_permission', 'custom_permission', 'all_permission')

    def get_profile_permission(self, obj):
        return query_to_json(obj.profile.permissions.all()) if obj.profile is not None else None

    def get_custom_permission(self, obj):
        return query_to_json(obj.user_permissions.all())

    def get_all_permission(self, obj):
        return query_to_json(obj.all_permissions())


class ContentTypeSerializer(serializers.Serializer):
    module = serializers.CharField(max_length=50, required=True)

    def validate(self, initial_data):
        initial_data['module'] = str(initial_data['module']).lower()
        if initial_data['module'] in ['add', 'change', 'delete', 'view']:
            raise Exception('Invalid Module Name.')
        if '_' in str(initial_data['module']):
            raise Exception('Module Name contains Strange Character.')
        permissions = Permission.objects.filter(codename__contains=initial_data['module']).all()
        if permissions.count() == 0:
            raise Exception(f'The Module {initial_data["module"]} has no permissions.',)
        return initial_data


class AssignProfileSerializer(serializers.Serializer):
    profile = serializers.CharField(max_length=50, required=True)
    user_ids = serializers.ListSerializer(child=serializers.IntegerField(min_value=1))



    def validate(self, initial_data):
        if 'user_ids' in initial_data:
            for i in initial_data['user_ids']:
                if not User.objects.filter(id=i).exists():
                    raise Exception(f'No user with the ID "{i}" exists.')
        initial_data['profile'] = str(initial_data['profile']).lower()
        if not Profile.objects.filter(name=initial_data['profile']).exists():
            raise Exception(f'No Profile with name "{initial_data["profile"]}" exists. ')
        return initial_data

    def assign(self, validated_data):
        users = User.objects.filter(id__in=validated_data['user_ids'])
        profile = Profile.objects.get(name=validated_data['profile'])
        for user in users:
            assign_profile(user, profile)
        return users


class UserProfileSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField('get_role', read_only=True)
    profile = serializers.SerializerMethodField('get_profile', read_only=True)
    permissions = serializers.SerializerMethodField('user_permissions', read_only=True)
    groups = serializers.SerializerMethodField('user_groups', read_only=True)
    emails = serializers.ListSerializer(child=serializers.JSONField(), read_only=True)
    mobiles = serializers.ListSerializer(child=serializers.JSONField(), read_only=True)
    profile_pic = serializers.SerializerMethodField('profile_pic_url', read_only=True)
    company = serializers.SerializerMethodField('company_', read_only=True)
    licenses = serializers.SerializerMethodField('licenses_', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'username', 'profile_pic', 'emails', 'mobiles', 'city', 'country', 'timezone',
                  'is_active', 'deletion_date', 'role', 'groups', 'profile', 'permissions', 'company', "licenses")


    def profile_pic_url(self, obj):
        try:
            return obj.profile_pic.url
        except ValueError:
            return None


    def get_role(self, obj):
        return obj.role.name if obj.role is not None else None

    def get_profile(self, obj):
        return obj.profile.name if obj.profile is not None else None

    def user_permissions(self, obj):
        return UserPermissionSerializer(obj).data

    def user_groups(self, obj):
        return UserGroupSerializer(obj.user_groups(), many=True).data

    def licenses_(self, obj):
        return obj.subscriptions()

    def company_(self, obj):
        return obj.company_()


class UserGroupSerializer(serializers.ModelSerializer):
    users = ExtractUsersSerializer(many=True, read_only=True)

    class Meta:
        model = UserGroup
        fields = ('id', 'name', 'color', 'users')

class CreateUserGroupSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)
    user_ids = serializers.ListSerializer(child=serializers.IntegerField(min_value=1),
                                          required=True, help_text='List of user IDs', allow_empty=True)
    color = serializers.CharField(max_length=15, required=True)

    class Meta:
        model = UserGroup
        fields = ("name", "user_ids", "color")

    def validate(self, initial_data):
        if 'name' in initial_data:
            initial_data['name'] = str(initial_data['name']).lower()
            if UserGroup.objects.filter(name=initial_data['name']).exists():
                raise Exception(f'The user group "{initial_data["name"]}" already exists.')
        if 'user_ids' in initial_data:
            for i in initial_data['user_ids']:
                if not User.objects.filter(id=i).exists():
                    raise Exception(f'No user with the ID "{i}" exists.')
        if 'color' in initial_data:
            initial_data['color'] = str(initial_data['color']).lower()
        return initial_data

    def create(self, validated_data):
        user_group = UserGroup()
        user_group.name = validated_data['name']
        user_group.color = validated_data['color']
        user_group.save()
        users = [User.objects.get(id=x) for x in validated_data['user_ids']]
        user_group.users.add(*users)
        user_group.save()
        return user_group

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            instance.name = validated_data['name']
            instance.save()
        if 'color' in validated_data:
            instance.color = validated_data['color']
            instance.save()
        if 'user_ids' in validated_data:
            instance.users.clear()
            users = User.objects.filter(id__in=validated_data['user_ids'])
            instance.users.add(*users)
            instance.save()
        return instance


class UpdateUserGroupSerializer(CreateUserGroupSerializer):
    name = serializers.CharField(max_length=50, required=False)
    user_ids = serializers.ListSerializer(child=serializers.IntegerField(min_value=1), required=False,
                                          help_text='List of user IDs', allow_empty=True)
    color = serializers.CharField(max_length=15, required=False, default=None)

class AddRemoveUsersInGroupSerializer(serializers.ModelSerializer):
    user_ids = serializers.ListSerializer(child=serializers.IntegerField(min_value=1), required=True,
                                          help_text='List of user IDs', allow_empty=False)
    action = serializers.ChoiceField(choices=['add', 'remove'], required=True)

    class Meta:
        model = UserGroup
        fields = ('user_ids', 'action')

    def validate(self, initial_data):
        user_group_id = self.context['user_group_id']
        if not UserGroup.objects.filter(id=user_group_id).exists():
            raise Exception(f'No User Group with the ID "{user_group_id}" exists.')
        user_group = UserGroup.objects.get(id=user_group_id)
        for user_id in initial_data['user_ids']:
            if not User.objects.filter(id=user_id).exists():
                raise Exception(f'No user with the ID "{user_id}" exists.')
            if initial_data['action'] == 'remove' and user_id not in user_group.users.all().values_list('id', flat=True):
                raise Exception(f'The user with ID "{user_id}" is not a member of this group.')
            if initial_data['action'] == 'add' and user_id in user_group.users.all().values_list('id', flat=True):
                raise Exception(f'The user with ID "{user_id}" is already a member of this group.')

        return initial_data

    def update(self, instance, validated_data):
        users = User.objects.filter(id__in=validated_data['user_ids'])
        if validated_data['action'] == 'add':
            instance.users.add(*users)
            instance.save()
            return instance
        if validated_data['action'] == 'remove':
            instance.users.remove(*users)
            instance.save()
            return instance
        return instance




class AddRoleSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, max_length=50, allow_null=False)
    lead_role = serializers.CharField(required=True, max_length=50, allow_null=True)
    reports_tag = serializers.ListField(child=serializers.CharField(max_length=50), help_text='List of role names',
                                        allow_empty=True, default=[])
    reports_role = serializers.ListField(child=serializers.CharField(max_length=50), help_text='List of role names',
                                         allow_empty=True, default=[])
    level = serializers.ChoiceField(choices=(('above', 'above'), ('same', 'same'), ('below', 'below')), required=True,
                                    allow_null=True)
    role = serializers.CharField(required=True, max_length=50, allow_null=True)

    class Meta:
        model = Role
        fields = ('name', 'lead_role', 'reports_tag', 'reports_role', 'level', 'role', 'description', 'share_data')
        depth = 1

    def validate(self, initial_data):
        my_roles = set()
        initial_data['reports_to'] = []
        if initial_data.get('reports_role', None) is not None:
            initial_data['reports_role'] = [str(x).lower() for x in initial_data['reports_role'] if x is not None]
            for i in initial_data['reports_role']:
                if not Role.objects.filter(name=str(i).lower()).exists():
                    raise Exception(f'This role with name {i} does not exist.')
            my_roles.update(set(Role.objects.filter(name__in=initial_data['reports_role']).all()))
            del initial_data['reports_role']

        else:
            pass
        if initial_data.get('reports_tag', None) is not None:
            initial_data['reports_tag'] = [str(x).lower() for x in initial_data['reports_tag'] if x is not None]
            for i in initial_data['reports_tag']:
                if not Tag.objects.filter(name=i).exists():
                    raise Exception(f'This tag with name {i} does not exist.')
            initial_data['reports_tag'] = Tag.objects.filter(name__in=initial_data['reports_tag'])
            for i in initial_data['reports_tag']:
                my_roles.update(set(i.roles.all()))
            del initial_data['reports_tag']
        else:
            pass
        initial_data['reports_to'] = list(my_roles)
        del my_roles
        if initial_data.get('name', None) is not None:
            initial_data['name'] = str(initial_data['name']).lower()
        if initial_data.get('role', None) is not None and initial_data.get('level', None) is not None:
            role = Role.objects.filter(name=str(initial_data['role']).lower()).first()
            if role is None:
                raise Exception(f'The role with name {initial_data["role"]} does not exist.')
            else:
                initial_data['role'] = role
        elif initial_data.get('role', None) is None and initial_data.get('level', None) is None:
            pass
        elif initial_data.get('role', None) is None and initial_data.get('level', None) is not None:
            if initial_data.get('level', None) == 'below':
                pass
            else:
                raise Exception('A role can only be below null not above or the same with null.')
        else:
            raise Exception('role and level field must be present together.')
        if initial_data.get('lead_role', None) is not None:
            role = Role.objects.filter(name=str(initial_data['lead_role']).lower()).first()
            if role is None:
                raise Exception(f'The role with name {initial_data["role"]} does not exist.')
            else:
                initial_data['lead_role'] = role
                initial_data['reports_to'].append(role)
                initial_data['level'] = 'below'
                initial_data['role'] = role
        return initial_data

    def create(self, validated_data):
        role_ = validated_data['role']
        level = validated_data['level']
        del validated_data['role'], validated_data['level']
        reports_to = validated_data['reports_to']
        del validated_data['reports_to']
        reports_to = [x for x in reports_to if x is not None]
        role = Role.objects.create(**validated_data)
        if level == 'above':
            role.fix_above(role_)
        elif level == 'same':
            role.fix_same(role_)
        elif level == 'below':
            role.fix_below(role_)
        role.reports_to.clear()
        role.reports_to.add(*reports_to)
        role.save()
        return role

    def update(self, instance, validated_data):
        role = Role.objects.filter(id=instance.id)
        reports_to = validated_data['reports_to']
        del validated_data['reports_to']
        reports_to = [x for x in reports_to if x is not None]
        role_, level = None, None
        if 'role' in validated_data and 'level' in validated_data:
            role_ = validated_data['role']
            level = validated_data['level']
            del validated_data['role'], validated_data['level']
        role.update(**validated_data)
        role = role.first()
        if level == 'above':
            role.fix_above(role_)
        elif level == 'same':
            role.fix_same(role_)
        elif level == 'below':
            role.fix_below(role_)
        role.reports_to.add(*reports_to)
        role.save()
        return role


class UpdateRoleSerializer(AddRoleSerializer):
    name = serializers.CharField(max_length=50, allow_null=False)
    lead_role = serializers.CharField(max_length=50, allow_null=True)
    reports_tag = serializers.ListField(child=serializers.CharField(max_length=50), help_text='List of tag names',
                                        allow_empty=True, default=[])
    reports_role = serializers.ListField(child=serializers.CharField(max_length=50), help_text='List of role names',
                                         allow_empty=True, default=[])
    level = serializers.ChoiceField(choices=(('above', 'above'), ('same', 'same'), ('below', 'below')),
                                    allow_null=True)
    role = serializers.CharField(max_length=50, allow_null=True)


class MiniRoleSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(max_length=50)
    description = serializers.SlugField()


class RoleSerializer(serializers.ModelSerializer):
    subroles = serializers.SerializerMethodField('sub__roles', read_only=True)
    downlines = serializers.SerializerMethodField('down__lines', read_only=True)
    up_line = serializers.SerializerMethodField('up__line', read_only=True)
    samelines = serializers.SerializerMethodField('same__lines', read_only=True)
    reports_to = serializers.ListSerializer(child=MiniRoleSerializer())

    class Meta:
        model = Role
        fields = ('id', 'name', 'lead_role', 'reports_to', 'share_data', 'up_line', 'downlines', 'samelines',
                  'subroles', 'description')
        depth = 1

    def sub__roles(self, obj):
        serializer = MiniRoleSerializer(obj.sub_roles(), many=True)
        return serializer.data

    def down__lines(self, obj):
        serializer = MiniRoleSerializer(obj.down_lines(), many=True)
        return serializer.data

    def up__line(self, obj):
        return MiniRoleSerializer(obj.up_line).data if obj.up_line is not None else None

    def same__lines(self, obj):
        serializer = MiniRoleSerializer(obj.same_lines(), many=True)
        return serializer.data


class TagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50)
    roles = serializers.ListSerializer(child=RoleSerializer())

    class Meta:
        model = Tag
        fields = ('id', 'name', 'roles')
        depth = 1


class AddTagSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, allow_null=False, required=True)
    roles = serializers.ListSerializer(child=serializers.CharField(max_length=50), allow_empty=False, required=True)

    class Meta:
        model = Tag
        fields = ('name', 'roles')

    def validate(self, initial_data):
        if initial_data.get('name', None) is not None:
            initial_data['name'] = str(initial_data['name']).lower()
        if initial_data.get('roles', None) is not None:
            initial_data['roles'] = [str(x).lower() for x in initial_data['roles'] if x is not None]
            for i in initial_data['roles']:
                if not Role.objects.filter(name=i).exists():
                    raise Exception(f'This role with name {i} does not exist.')
            initial_data['roles'] = Role.objects.filter(name__in=initial_data['roles'])
        else:
            del initial_data['roles']
        return initial_data

    def create(self, validated_data):
        tag = Tag.objects.create(name=validated_data['name'])
        tag.roles.add(*validated_data['roles'])
        tag.save()
        return tag

    def update(self, instance, validated_data):
        tag = Tag.objects.get(id=instance.id)
        if 'roles' in validated_data:
            tag.roles.clear()
            tag.roles.add(*validated_data['roles'])
        if 'name' in validated_data:
            tag.name = validated_data['name']
        tag.save()
        return tag


class UpdateTagSerializer(AddTagSerializer):
    name = serializers.CharField(max_length=50, allow_null=False)
    roles = serializers.ListSerializer(child=serializers.CharField(max_length=50), allow_empty=False)


class UserInviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'email',
            'company',
            'mobile',
            'first_name',
            'last_name',
            'user_type',
            'profile',
            'role'
        )


    def validate(self, initial_data):
        if User.objects.filter(email=initial_data['email']).exists():
            raise Exception("User Email exists in DB.")
        return initial_data

    def create(self, validated_data):
        obj = User.objects.create(username=validated_data['email'], **validated_data)
        # try:
        invite_obj, _ = InvitationLog.objects.get_or_create(user=obj)
        link = "<base_url>/invite/?key={}".format(invite_obj.invitation_key)
        body = """
        Hello {},
        
        You are invited to XYZ.
        
        Please follow this link to join.
        {}
        
        Thank you
        """.format(obj.full_name(), link)
        email = EmailMessage('Invitation to join XYZ', body,
                             to=[obj.email, ],)
        email.send()
        # except:
        #     pass
        return obj


class UserInvitationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    key = serializers.UUIDField()
    password = serializers.CharField()
    password2 = serializers.CharField()

    class Meta:
        model = User
        fields = (
            'email',
            'key',
            'password',
            'password2',
        )

    def validate(self, initial_data):
        if not User.objects.filter(email=initial_data['email']).exists():
            raise Exception("User does not exists.")

        if initial_data['password'] != initial_data['password2']:
            raise Exception("Passwords do not match.")

        if not InvitationLog.objects.filter(user__email=initial_data['email'], invitation_key=initial_data['key'],
                                            is_used=False).exists():
            raise Exception("Invite Key does not match.")
        return initial_data

    def create(self, validated_data):
        user = User.objects.get(email=validated_data['email'])
        user.set_password(validated_data['password'])
        user.save()
        obj = InvitationLog.objects.get(user__email=validated_data['email'], invitation_key=validated_data['key'],
                                        is_used=False)
        obj.is_used = True
        obj.save()
        return user


class ActivateDeactivateUserSerializer(serializers.ModelSerializer):
    activate = serializers.BooleanField(allow_null=False, required=True)

    class Meta:
        model = User
        fields = ('activate', )

    def validate(self, initial_data):
        if initial_data['activate']:
            initial_data['is_active'] = True
        else:
            initial_data['is_active'] = False

        del initial_data['activate']
        return initial_data


    def update(self, instance, validated_data):
        instance.is_active = validated_data['is_active']
        instance.save()
        return instance


class UserEditBasicDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=50, min_length=3, required=False)
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'city', 'timezone', 'country')

    def validate(self, initial_data):
        if 'username' in initial_data:
            initial_data['username'] = str(initial_data['username']).lower()
            if self.Meta.model.objects.filter(username=initial_data['username']).\
                    exclude(id=self.context['user'].id).exists():
                raise Exception('A user already exists with this username')
        title_fields = {x: str(initial_data[x]).title() for x in initial_data if x != 'username'}
        initial_data.update(title_fields)
        return initial_data


    def update(self, instance, validated_data):
        self.Meta.model.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()
        return instance

    def execute(self,):
        return self.update(self.context['user'], self.validated_data)



class SetPrimaryContactsSerializer(serializers.ModelSerializer):
    primary_email = serializers.EmailField(required=False, allow_null=False, allow_blank=False)
    primary_mobile = serializers.CharField(max_length=30, required=False, allow_null=False, allow_blank=False)

    class Meta:
        model = User
        fields = ('primary_email', 'primary_mobile')

    def validate(self, initial_data):
        if 'primary_email' in initial_data:
            emails = self.context['user'].emails if self.context['user'].emails is not None else []
            has_email = sum(1 for email in emails if email['email'] == initial_data['primary_email']) > 0
            if not has_email:
                raise Exception(f'This email "{initial_data["primary_email"]}" does not belong to you.')

        if 'primary_mobile' in initial_data:
            mobiles = self.context['user'].mobiles if self.context['user'].mobiles is not None else []
            has_email = sum(1 for mobile in mobiles if mobile['mobile'] == initial_data['primary_mobile']) > 0
            if not has_email:
                raise Exception(f'This mobile number "{initial_data["primary_mobile"]}" does not belong to you.')
        return initial_data

    def update(self, instance, validated_data):
        if 'primary_email' in validated_data:
            instance.make_primary_contact(type_='email', contact_=validated_data['primary_email'])
        if 'primary_mobile' in validated_data:
            instance.make_primary_contact(type_='mobile', contact_=validated_data['primary_mobile'] )
        return instance

    def execute(self):
        return self.update(self.context['user'], self.validated_data)


class UserEmailSerializer(serializers.Serializer):
    old_email = serializers.EmailField(required=False, allow_null=False, allow_blank=False)
    email = serializers.EmailField(required=True, allow_null=False, allow_blank=False)
    action = serializers.ChoiceField(choices=['add', 'edit', 'delete'], allow_null=False, allow_blank=False, required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        if validated_data['action'] == 'add':
            instance.add_new_contact(type_='email', contact_=validated_data['email'])
            return instance
        if validated_data['action'] == 'delete':
            instance.delete_contact(type_='email', contact_=validated_data['email'])
            return instance
        if validated_data['action'] == 'edit':
            instance.update_contact(type_='email', old_contact_=validated_data['old_email'],
                                    new_contact_=validated_data['email'])
            return instance
        return instance

    def validate(self, initial_data):
        user = self.context['user']
        emails = user.emails if user.emails is not None else []
        has_email = sum(1 for email in emails if email['email'] == initial_data['email']) > 0
        if initial_data['action'] == 'add':
            if has_email:
                raise Exception('You already have this email.')
        if initial_data['action'] == 'edit':
            if 'old_email' not in initial_data:
                raise Exception('The old email is required to update this email.')
            has_email = sum(1 for email in emails if email['email'] == initial_data['old_email']) > 0
            if not has_email:
                raise Exception('You do not have this email.')
            if initial_data['old_email'] == initial_data['email']:
                raise Exception('No change, the email is the same')
        if initial_data['action'] == 'delete':
            if not has_email:
                raise Exception('You do not have this email.')
        return initial_data

    def execute(self):
        return self.update(self.context['user'], self.validated_data)


class UserMobileSerializer(serializers.Serializer):
    old_mobile = serializers.CharField(max_length=30, required=False, allow_null=False, allow_blank=False)
    mobile = serializers.CharField(max_length=30, required=True, allow_null=False, allow_blank=False)
    action = serializers.ChoiceField(choices=['add', 'edit', 'delete'], allow_null=False, allow_blank=False,
                                     required=True)

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        if validated_data['action'] == 'add':
            instance.add_new_contact(type_='mobile', contact_=validated_data['mobile'])
            return instance
        if validated_data['action'] == 'delete':
            instance.delete_contact(type_='mobile', contact_=validated_data['mobile'])
            return instance
        if validated_data['action'] == 'edit':
            instance.update_contact(type_='mobile', old_contact_=validated_data['old_mobile'],
                                    new_contact_=validated_data['mobile'])
            return instance
        return instance

    def validate(self, initial_data):
        user = self.context['user']
        mobiles = user.mobiles if user.mobiles is not None else []
        has_mobile = sum(1 for mobile in mobiles if mobile['mobile'] == initial_data['mobile']) > 0
        if initial_data['action'] == 'add':
            if has_mobile:
                raise Exception('You already have this mobile number.')
        if initial_data['action'] == 'edit':
            if 'old_mobile' not in initial_data:
                raise Exception('The old mobile number is required to update this mobile number.')
            has_mobile = sum(1 for mobile in mobiles if mobile['mobile'] == initial_data['old_mobile']) > 0
            if not has_mobile:
                raise Exception('You do not have this mobile number.')
            if initial_data['old_mobile'] == initial_data['mobile']:
                raise Exception('No change, the mobile number is the same')
        if initial_data['action'] == 'delete':
            if not has_mobile:
                raise Exception('You do not have this mobile number.')
        return initial_data

    def execute(self):
        return self.update(self.context['user'], self.validated_data)


class UserUploadProfilePicSerializer(serializers.Serializer):
    def update(self, instance, validated_data):
        instance.profile_pic = self.context['image']
        instance.save()
        return instance

    def create(self, validated_data):
        pass

    def validate(self, initial_data):
        if not settings.USE_S3:
            raise Exception('Unable to upload picture. Server is currently unavailable.')
        file_name = self.context['image'].name
        extension = file_name.split(".")[-1]
        available_extensions = ('jpg', 'png', 'jpeg', 'webp')
        if extension.lower() not in available_extensions:
            raise Exception("File format not supported. Please use - {} files".format(available_extensions))
        self.context['image'].name = f'{self.context["schema"]}_{self.context["user"].id}_profile_pic' \
                                     f'.{extension}'
        return initial_data

    def execute(self):
        return self.update(self.context['user'], self.validated_data)



class AdminResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise Exception("User does not exists.")
        return value

    def reset_password(self):
        user = User.objects.get(email=self.validated_data['email'])
        password = User.objects.make_random_password()
        body = """
                Hello {},

                Your password has been reset via admin.
                
                Your new password is {}

                Thank you
                """.format(user.first_name, password)
        email = EmailMessage('Password Reset from Admin', body,
                             to=[user.email, ], )
        email.send()
        user.set_password(password)
        user.save()
