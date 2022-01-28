from django.db import models
from django_tenants.models import TenantMixin, DomainMixin

from Demo_CRM.storage_backends import PublicMediaStorage
from general.models import Product, Subscription, Plan

class Company(TenantMixin):
    name = models.CharField(max_length=50, default='', unique=True)
    image = models.FileField(storage=PublicMediaStorage(), null=True, blank=True, default=None)
    email = models.EmailField(default=None, null=True)
    phone = models.CharField(max_length=20, default=None, null=True)
    state = models.CharField(max_length=50, default=None, null=True)
    country = models.CharField(max_length=50, default=None, null=True)
    currency = models.CharField(max_length=10, default=None, null=True)
    timezone = models.CharField(max_length=30, default=None, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    auto_create_schema = True

    @staticmethod
    def serialized_data():
        return list(Company.objects.values_list('name', flat=True))

    def __str__(self):
        return self.name

    def subscribed_products(self, user=None):
        if user:
            products = Subscription.objects.filter(company=self, user=user, active=True).values_list('plan__product__name', flat=True)
        else:
            products = Subscription.objects.filter(company=self, active=True).values_list('plan__product__name',
                                                                                        flat=True)
        if user:
            return self.products(Product.objects.filter(name__in=products), user)
        return self.products(Product.objects.filter(name__in=products))

    def unsubscribed_products(self, user=None):
        if user:
            products = Subscription.objects.filter(company=self, user=user, active=True).values_list('plan__product__name', flat=True)
        else:
            products = Subscription.objects.filter(company=self, active=True).values_list('plan__product__name',
                                                                                        flat=True)
        sub_products = Product.objects.filter(name__in=products)
        products = Product.objects.all()
        diff = products.difference(sub_products)
        if user:
            return self.products(diff, user)
        return self.products(diff)


    def products(self, products=Product.objects.all(), user=None):
        data = []
        for i in products:
            from general.serializers import ProductSerializer
            dt = ProductSerializer(i).data
            dt['no_of_users'] = i.used_subscriptions().filter(company=self).count()
            dt['plans'] = self.plans(i, user)
            data.append(dt)
        return data

    def plans(self, product, user=None):
        plans = Subscription.objects.filter(company=self).values_list('plan_id', flat=True)
        plans = Plan.objects.filter(id__in=plans, product=product)
        data = []
        for i in plans:
            from general.serializers import PlanSerializer
            dt = PlanSerializer(i).data
            del dt['no_of_subscriptions']
            del dt['product']
            if user:
                filters = {"company": self, "user": user}
                name = 'licenses'
            else:
                filters = {"company": self}
                name = "subscriptions"
            dt[f"paid {name}"] = i.subscriptions().filter(**filters)
            dt[f"no_of_{name}"] = dt[f"paid {name}"].count()
            del dt[f"paid {name}"]
            from general.serializers import SubscriptionSerializer
            dt[f"used_{name}"] = SubscriptionSerializer(i.used_subscriptions(**filters), many=True).data
            dt[f"unused_{name}"] = SubscriptionSerializer(i.unused_subscriptions(**filters), many=True).data
            dt[f"expired_{name}"] = SubscriptionSerializer(i.expired_subscriptions(**filters), many=True).data
            dt[f"unpaid_{name}"] = SubscriptionSerializer(i.unpaid_subscriptions(**filters), many=True).data
            data.append(dt)
        return data

    def subscriptions(self, user=None):
        if user:
            filters = {"company": self, "user": user, "active": True}
            name = 'licenses'
        else:
            filters = {"company": self, "active": True}
            name = 'subscriptions'

        data = {}
        subscriptions = Subscription.objects.filter(**filters)
        used_filter = {"active": True, "user__isnull": False}
        unused_filter = {"active": True, "user__isnull": True}
        unpaid_filter = {"active": False, "user__isnull": True}
        from django.utils import timezone
        expired_filter = {"active": True, "expiry_date__lt": timezone.now()}
        data[f"no_of_{name}"] = subscriptions.count()
        from general.serializers import SubscriptionSerializer
        data[f"used_{name}"] = SubscriptionSerializer(subscriptions.filter(**used_filter), many=True).data
        data[f"unused_{name}"] = SubscriptionSerializer(subscriptions.filter(**unused_filter), many=True).data
        data[f"expired_{name}"] = SubscriptionSerializer(subscriptions.filter(**expired_filter), many=True).data
        data[f"unpaid_{name}"] = SubscriptionSerializer(subscriptions.filter(**unpaid_filter), many=True).data
        return data

class Domain(DomainMixin):
    pass
