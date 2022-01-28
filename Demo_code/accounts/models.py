import uuid
from datetime import datetime

from django.contrib.postgres.fields import ArrayField
from django.contrib.auth.models import (AbstractUser, BaseUserManager, Permission)
from django.contrib.auth.models import Group
from django.db import models
from rest_framework_simplejwt.tokens import RefreshToken


# Create your models here.
from Demo_CRM.storage_backends import PublicMediaStorage
from Tenant.serializer import CompanySerializer
from general.models import Subscription, Product


class Profile(Group):
    description = models.CharField(max_length=180, null=True, blank=True)
    cloned_profile = models.ForeignKey('accounts.Profile', on_delete=models.SET_NULL, default=None, null=True)

    def __str__(self):
        return self.name

    @staticmethod
    def serialized_data():
        return list(Profile.objects.values_list('name', flat=True))


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, username=None, company="", **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        extra_fields.setdefault('user_type', 3)
        extra_fields.setdefault('company', company)
        user = self.model(
            email=self.normalize_email(email),
            username=self.normalize_email(email), **extra_fields)

        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)

        return user

    def create_staffuser(self, email, password, company, **extra_fields):
        """
        Creates and saves a staff user with the given email and password.
        """

        extra_fields.setdefault('user_type', 2)
        extra_fields.setdefault('company', company)
        extra_fields.setdefault('is_staff', True)
        # extra_fields.setdefault('is_admin', True)
        user = self.create_user(email, password=password, username=email, **extra_fields)
        user.is_active = True
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        """
        extra_fields.setdefault('user_type', 1)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        user = self.create_user(email, password=password, username=email, **extra_fields)
        # user.is_superuser = True
        user.is_active = True
        user.save(using=self._db)

        return user


AUTH_PROVIDERS = {'google': 'google', 'email': 'email', 'microsoft': 'microsoft'}

USER_CHOICES = (
    ('1', 'superuser'),
    ('2', 'CRM_admin'),
    ('3', 'CRM_user'),

)



class User(AbstractUser):
    email = models.EmailField(max_length=254, unique=True)
    company = models.CharField(max_length=100, default="demo")
    mobile = models.CharField(max_length=30, default=None, null=True)
    mobiles = ArrayField(base_field=models.JSONField(default=dict), default=list, null=True, blank=True)
    emails = ArrayField(base_field=models.JSONField(default=dict), default=list, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    profile_pic = models.FileField(storage=PublicMediaStorage(), null=True, blank=True, default=None)
    user_type = models.CharField(max_length=50, choices=USER_CHOICES, default="")
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, blank=True, null=True, related_name ='userprofile')
    role = models.ForeignKey('accounts.Role', on_delete=models.SET_NULL, null=True, related_name='userole')
    auth_provider = models.CharField(
        max_length=255, blank=False,
        null=False, default=AUTH_PROVIDERS.get('email'))
    city = models.CharField(max_length=70, default=None, null=True)
    country = models.CharField(max_length=70, default=None, null=True)
    timezone = models.CharField(max_length=30, default=None, null=True)
    deletion_date = models.DateField(null=True, blank=True, default=None)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email & Password are required by default.

    objects = UserManager()

    def __str__(self):
        return self.email

    def all_permissions(self):
        perm_list = [str(x).split(".")[1] for x in self.get_all_permissions()]
        return Permission.objects.filter(codename__in=perm_list)

    def user_groups(self):
        return UserGroup.objects.filter(users__email=self.email)

    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def make_primary_contact(self, type_:str, contact_:str):
        list_ = self.emails if type_ == 'email' else self.mobiles
        list_ = list_ if list_ is not None else []
        new_contact = None
        for contact in list_:
            contact['primary'] = False
            if contact[type_] == contact_:
                new_contact = contact
                break
        list_.remove(new_contact)
        if new_contact is not None:
            new_contact['primary'] = True
            list_.insert(0, new_contact)
        if type_ == 'email':
            self.emails = list_
        else:
            self.mobiles = list_
        self.save()

    def add_new_contact(self, type_: str, contact_: str):
        data = {type_: contact_, "primary": False, "date_created": datetime.now().__str__()}
        list_ = self.emails if type_ == 'email' else self.mobiles
        list_ = list_ if list_ is not None else []
        list_.append(data)
        if type_ == 'email':
            self.emails = list_
            if self.email is None:
                self.email = contact_
            self.save()

        elif type_ == 'mobile':
            self.mobiles = list_
            if self.mobile is None:
                self.mobile = contact_
            self.save()

    def update_contact(self, type_:str, old_contact_:str, new_contact_: str):
        list_ = self.emails if type_ == 'email' else self.mobiles
        list_ = list_ if list_ is not None else []
        data = [contact for contact in list_ if contact[type_] == old_contact_][0]
        data_index = list_.index(data)
        new_data = data
        new_data[type_] = new_contact_
        list_.remove(data)
        list_.insert(data_index, new_data)
        if type_ == 'email':
            self.emails = list_
        else:
            self.mobiles = list_
        self.save()


    def delete_contact(self, type_:str, contact_:str):
        list_ = self.emails if type_ == 'email' else self.mobiles
        list_ = list_ if list_ is not None else []
        data = [contact for contact in list_ if contact[type_] == contact_][0]
        list_.remove(data)
        if type_ == 'email':
            self.emails = list_
        else:
            self.mobiles = list_
        self.save()



    def tokens(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token)
        }

    def subscribed_products(self):
        from Tenant.models import Company
        company = Company.objects.filter(name=self.company).first()
        if company:
            return company.subscribed_products(self.id)
        return []

    def unsubscribed_products(self):
        from Tenant.models import Company
        company = Company.objects.filter(name=self.company).first()
        if company:
            return company.unsubscribed_products(self.id)
        return []

    def subscriptions(self):
        from Tenant.models import Company
        company = Company.objects.filter(name=self.company).first()
        if company:
            return company.subscriptions(self.id)
        return {}

    def company_(self):
        from Tenant.models import Company
        company = Company.objects.filter(name=self.company).first()
        if company:
            return CompanySerializer(company).data
        return {}

    @staticmethod
    def serialized_data():
        return list(User.objects.values('first_name', 'last_name', 'email'))



class LoginInformation(models.Model):
    email = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    ip_address = models.GenericIPAddressField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default = 0.0)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default = 0.0)
    country = models.CharField(max_length=20, default="")
    city = models.CharField(max_length=20, default="")
    login_date = models.DateTimeField()
    logout_date = models.DateTimeField(null=True)
    browser_name = models.CharField(max_length=50)
    os = models.CharField(max_length=50)
    device_type = models.CharField(max_length=20, default = "")

    @staticmethod
    def serialized_data():
        return list(LoginInformation.objects.values('email', 'ip_address'))

class Role(models.Model):
    name = models.CharField(max_length=100, default='', unique=True)
    reports_to = models.ManyToManyField('Role', blank=True, related_name='reports')
    lead_role = models.ForeignKey('Role', on_delete=models.SET_NULL, default=None, null=True, blank=True, related_name='lead')
    share_data = models.BooleanField(default=False)
    up_line = models.ForeignKey('Role', on_delete=models.SET_NULL, default=None, null=True, blank=True, related_name='upline')
    description = models.TextField()

    def fix_below(self, role):
        self.up_line = role
        self.save()

    def fix_above(self, role):
        upline = role.up_line if role.up_line is not None else None
        upline = upline.up_line if upline is not None else None
        self.up_line = upline
        self.save()

    def fix_same(self, role):
        self.up_line = role.up_line
        self.save()

    def __str__(self):
        return self.name

    def down_lines(self):
        return Role.objects.filter(up_line=self)

    def sub_roles(self):
        return Role.objects.filter(lead_role_id=self.id)

    def same_lines(self):
        return Role.objects.filter(up_line=self.up_line).exclude(name=self.name)

    @staticmethod
    def serialized_data():
        return list(Role.objects.values_list('name', flat=True))

class Tag(models.Model):
    name = models.CharField(max_length=100, default='', unique=True)
    roles = models.ManyToManyField('Role', blank=True, related_name='roles_tag')

    @staticmethod
    def serialized_data():
        return list(Tag.objects.values_list('name', flat=True))


class UserGroup(models.Model):
    name = models.CharField(max_length=100, default='')
    color = models.CharField(max_length=15, default=None, null=True)
    users = models.ManyToManyField('accounts.User', blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    @staticmethod
    def serialized_data():
        return list(UserGroup.objects.values_list('name', flat=True))

class InvitationLog(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, blank=True, null=True, default=None)
    invitation_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_used = models.BooleanField(default=False)

    @staticmethod
    def serialized_data():
        return list(InvitationLog.objects.values('user__email', 'invitation_key'))