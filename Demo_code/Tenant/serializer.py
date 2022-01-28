from django.conf import settings
from rest_framework import serializers
from .models import Company, Domain

class BasicCompanySerializer(serializers.ModelSerializer):
    domains = serializers.SerializerMethodField('get_domains', read_only=True)
    image = serializers.SerializerMethodField('image_url', read_only=True)

    class Meta:
        model = Company
        fields = ("id", "name", "domains", 'email', 'phone', 'image', 'state', 'country',
                  'currency', 'timezone')

    def get_domains(self, obj):
        domains = Domain.objects.filter(tenant=obj)
        serializers_ = DomainSerializer(domains, many=True)
        return serializers_.data

    def image_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return None


class CompanySerializer(serializers.ModelSerializer):
    domains = serializers.SerializerMethodField('get_domains', read_only=True)
    subscribed_products = serializers.SerializerMethodField('subscribed__products', read_only=True)
    unsubscribed_products = serializers.SerializerMethodField('unsubscribed__products', read_only=True)
    subscriptions = serializers.SerializerMethodField('subscriptions_', read_only=True)
    image = serializers.SerializerMethodField('image_url', read_only=True)

    class Meta:
        model = Company
        fields = ("id", "name",  "domains", 'email', 'phone', 'image', 'state', 'country',
                  'currency', 'timezone', "subscribed_products", "unsubscribed_products", "subscriptions")

    def get_domains(self, obj):
        domains = Domain.objects.filter(tenant=obj)
        serializers_ = DomainSerializer(domains, many=True)
        return serializers_.data

    def subscribed__products(self, obj):
        return obj.subscribed_products()

    def unsubscribed__products(self, obj):
        return obj.unsubscribed_products()

    def subscriptions_(self, obj):
        return obj.subscriptions()

    def image_url(self, obj):
        try:
            return obj.image.url
        except ValueError:
            return None


    def validate(self, initial_data):
        from Multitenant.classes import NameToSchema, NameToUrl
        schema_name = NameToSchema(self.context)
        domain_url = NameToUrl(self.context)

        if schema_name == 'public':
            raise Exception('This schema name is already in use')
        if Company.objects.filter(name=str(self.context).title()).exists():
            raise Exception(f'A company with the name {self.context} already exists.')
        initial_data['schema_name'] = schema_name
        initial_data['company'] = str(self.context).title()
        initial_data['domain_url'] = domain_url
        return initial_data

    def create(self, validated_data):
        company = Company.objects.create(name=validated_data['company'], schema_name=validated_data['schema_name'],)
        Domain.objects.create(tenant=company, domain=validated_data['domain_url'], is_primary=True)
        return company


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ('domain', 'is_primary', )


class EditCompanySerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(max_length=20, required=False)
    state = serializers.CharField(max_length=50, required=False)
    country = serializers.CharField(max_length=50, required=False)
    currency = serializers.CharField(max_length=10, required=False)
    timezone = serializers.CharField(max_length=20, required=False)

    class Meta:
        model = Company
        fields = ('name', 'email', 'phone', 'state', 'country',  'currency', 'timezone')

    def validate(self, initial_data):
        if self.context['company'] != self.instance:
            raise Exception('This is not your company.')
        for x in initial_data:
            if x in initial_data and x in ('name', 'state', 'country'):
                initial_data[x] = str(initial_data[x]).title()
            if x in initial_data and x in ('email', 'phone','timezone'):
                initial_data[x] = str(initial_data[x]).lower()
            if x in initial_data and x in ('currency',):
                initial_data[x] = str(initial_data[x]).upper()
        if 'name' in initial_data:
            if Company.objects.filter(name=initial_data['name']).exists():
                raise Exception('A company with this name already exists')
        return initial_data

    def update(self, instance, validated_data):
        if 'name' in validated_data:
            from accounts.models import User
            User.objects.filter(company=instance.name).update(company=validated_data['name'])
        Company.objects.filter(pk=instance.pk).update(**validated_data)
        instance.refresh_from_db()
        return instance


class CompanyUploadImageSerializer(serializers.Serializer):
    def update(self, instance, validated_data):
        instance.image = self.context['image']
        instance.save()
        return instance

    def create(self, validated_data):
        pass

    def validate(self, initial_data):
        from Multitenant.classes import SchemaToTenant
        instance = Company.objects.filter(id=self.context['company_id']).first()
        if instance is None:
            raise Exception('No Company with this ID exists')
        self.context['company_id'] = instance
        if SchemaToTenant(self.context['schema']) != instance:
            raise Exception('This is not your company.')
        if not settings.USE_S3:
            raise Exception('Unable to upload picture. Server is currently unavailable.')
        file_name = self.context['image'].name
        extension = file_name.split(".")[-1]
        available_extensions = ('jpg', 'png', 'jpeg', 'webp')
        if extension.lower() not in available_extensions:
            raise Exception("File format not supported. Please use - {} files".format(available_extensions))
        self.context['image'].name = f'{self.context["schema"]}_company_image' \
                                     f'.{extension}'
        return initial_data

    def execute(self):
        return self.update(self.context['company_id'], self.validated_data)
