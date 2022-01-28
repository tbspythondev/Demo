from itertools import chain

from django.contrib.auth.models import Permission, Group
from rest_framework import permissions
from rest_framework.authentication import BasicAuthentication

from accounts.models import User, Profile


class SuperuserAuthenticationPermission(permissions.BasePermission):
    ADMIN_ONLY_AUTH_CLASSES = [BasicAuthentication,]

    def has_permission(self, request, view):
        user = request.user
        if user and user.is_authenticated and user.is_superuser:
            return user.is_superuser or \
                not any(isinstance(request._authenticator, x) for x in self.ADMIN_ONLY_AUTH_CLASSES)
        return False

def update_profile(profile: str, permissions: dict):
    profile_ = Profile.objects.get(name=profile)
    profile_.permissions.clear()
    profile_.permissions.add(**profile_.cloned_profile.permissions.all())
    permissions_ = json_to_query(permissions)
    profile_.permissions.add(permissions_)
    profile_.save()
    return profile_



def assign_permission(user: User, permissions_dict: dict):
    permissions = json_to_query(permissions_dict)
    user.user_permissions.add(*permissions)
    user.save()
    return user

def remove_permission(user: User, permissions_dict: dict):
    permissions = json_to_query(permissions_dict)
    user.user_permissions.remove(*permissions)
    user.save()
    return user


def remove_profile(user: User):
    user.groups.clear()
    user.profile = None
    user.save()
    user.refresh_from_db()
    return user

def assign_profile(user: User, profile: Profile):
    user.groups.clear()
    user.groups.add(Group.objects.get(name=profile.name))
    user.profile = profile
    user.save()
    user.refresh_from_db()
    return user

def assign_perm_to_profile(profile:str, permissions:dict):
    profile = Profile.objects.get(name=profile)
    permissions = json_to_query(permissions)
    profile.permissions.clear()
    profile.permissions.add(*permissions)
    profile.save()

def json_to_query(permissions:dict):
    permissions_ = list(chain.from_iterable(list(permissions.values())))
    return Permission.objects.filter(codename__in=permissions_)

def query_to_json(permissions, full=False):
    permissions_ = tuple(permissions.values_list('content_type__model', 'codename'))
    data = {a:[] for a,b in permissions_ }
    [data[a].append(b) for a,b in permissions_]
    content_type = set(permissions.values_list('content_type__model', flat=True))
    all_content_type = set(Permission.objects.all().values_list('content_type__model', flat=True))
    all_content_type = [x for x in all_content_type if x not in content_type]
    if full:
        for x in all_content_type:
            data[x] = []
    return data


def create_module_permissions(module):
    module = str(module).lower()
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    if ContentType.objects.filter(model=module).exists():
        raise Exception('A module with this name already exists')
    ct = ContentType.objects.create(model=module, app_label=f'module | {module}')
    for i in ('view', 'add', 'change', 'delete'):
        Permission.objects.create(name=f'Can {i} {module}', content_type=ct,
                                          codename=f'{i}_{module}')
    return {"content_type": ct.app_label,
            "permissions": Permission.objects.filter(content_type=ct).values_list('codename', flat=True)}


def delete_module_permissions(module):
    module = str(module).lower()
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    ct = ContentType.objects.filter(model=module).first()
    if ct is None:
        raise Exception('No module with this name')
    Permission.objects.filter(content_type=ct).delete()
    ct.delete()
    return
