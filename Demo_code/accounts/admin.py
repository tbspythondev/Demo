from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile, Tag, Role

# Register your models here.

User = get_user_model()
admin.site.unregister(Group)

    
admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Tag)
admin.site.register(Role)


