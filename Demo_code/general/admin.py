from django.contrib import admin

# Register your models here.
from .models import Product, Plan, Subscription

admin.site.register(Product)
admin.site.register(Plan)
admin.site.register(Subscription)