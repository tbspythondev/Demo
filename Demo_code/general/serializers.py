import hashlib
import hmac
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers, status
from rest_framework.response import Response

from Utilities.utils import create_txt_ref
from Utilities.webhooks import PAYSTACK_KEY
from general.models import Product, Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
	features = serializers.ListSerializer(child=serializers.CharField(max_length=255), read_only=True)
	product = serializers.SerializerMethodField('product_detail', read_only=True)
	no_of_subscriptions = serializers.SerializerMethodField('subscriptions', read_only=True)
	class Meta:
		model = Plan
		fields = ('id', 'name', 'product', 'no_of_subscriptions', 'price_currency', 'monthly_price_value', 'annual_price_value', 'description', 'features')

	def product_detail(self, obj):
		return {"id": obj.product.id, "name": obj.product.name}

	def subscriptions(self, obj):
		return obj.subscriptions().count()


class SubscriptionSerializer(serializers.ModelSerializer):
	company = serializers.SerializerMethodField('company_', read_only=True)
	plan = PlanSerializer(read_only=True)
	user = serializers.SerializerMethodField('user_', read_only=True)
	transaction_log = serializers.JSONField(read_only=True)
	total_price = serializers.SerializerMethodField('price', read_only=True)
	duration = serializers.SerializerMethodField('duration_', read_only=True)

	class Meta:
		model = Subscription
		fields = ('id', 'user', 'company', 'active', 'used', 'expired',  'plan', 'duration', 'total_price', 'expiry_date', 'transaction_log')


	def price(self, obj):
		return obj.total_price()

	def duration_(self, obj):
		return obj.duration_str()

	def user_(self, obj):
		if obj.user_() is not None:
			from accounts.serializers import ExtractUsersSerializer
			return ExtractUsersSerializer(obj.user_()).data
		return None

	def company_(self, obj):
		return obj.company.name

	def expired_(self, obj):
		return obj.expired()

	def used_(self, obj):
		return obj.used()


class ProductSerializer(serializers.ModelSerializer):
	picture_url = serializers.SerializerMethodField('picture__url', read_only=True)
	video_url = serializers.SerializerMethodField('video__url', read_only=True)
	plans = serializers.SerializerMethodField('plans_', read_only=True)
	no_of_users = serializers.SerializerMethodField('users_', read_only=True)

	class Meta:
		model = Product
		ref_name = 'Subscription Product'
		fields = ('id', 'name', 'no_of_users', 'description', 'picture_url', 'video_url', 'homepage_url',
				  'plans')

	def picture__url(self, obj):
		return obj.picture__url()

	def video__url(self, obj):
		return obj.video__url()

	def plans_(self, obj):
		return PlanSerializer(obj.plans(), many=True).data

	def users_(self, obj):
		return obj.current_users()

class AddPlanSerializer(serializers.ModelSerializer):
	class Meta:
		model = Plan
		fields = ('name', 'product', 'price_currency', 'annual_price_value',
				  'monthly_price_value', 'description', 'features')

	def validate(self, initial_data):
		if 'name' in initial_data:
			product = initial_data['product']
			if self.Meta.model.objects.filter(name=str(initial_data["name"]).title(), product=product).exists():
				raise Exception('A plan with this name already exists for this product')
			initial_data['name'] = str(initial_data['name']).title()
		return initial_data

class SubscribeSerializer(serializers.ModelSerializer):

	class Meta:
		model = Subscription
		fields = ('plan', 'duration', 'time_choice', 'quantity')

	time_choice = serializers.ChoiceField(choices=['Monthly', 'Annually'], required=True)
	quantity = serializers.IntegerField(min_value=1, required=True)
	duration = serializers.IntegerField(min_value=1, required=True)

	def validate(self, initial_data):
		initial_data['company'] = self.context['company']
		if 'time_choice' in initial_data:
			initial_data['time_choice'] = Plan.Choice.annually if initial_data['time_choice'] == 'Annually' else Plan.Choice.monthly
		return initial_data

	def create(self, validated_data):
		quantity = validated_data['quantity']
		del validated_data['quantity']
		transaction_ref = create_txt_ref()
		from django.utils import timezone
		data = {"txn_ref": transaction_ref, "txn_status": 'PENDING', "txn_time_stamp": timezone.now().timestamp(),
				"company": self.context['company'].name, "email": self.context['user'].email,
				"first_name": self.context['user'].first_name, "last_name": self.context['user'].last_name,
				"country": self.context['user'].country}
		subs = [Subscription.objects.create(**validated_data) for i in range(quantity)]
		data['amount'] = sum(sub.total_price() for sub in subs).__str__()
		for sub in subs:
			sub.transaction_log = data
			sub.transaction_ref = transaction_ref
			sub.save()
		return data, subs

class AddProductSerializer(serializers.ModelSerializer):
	class Meta:
		model = Product
		fields = ('name', 'description', 'picture_url', 'video_url', 'homepage_url')

	def validate(self, initial_data):
		if 'name' in initial_data:
			initial_data['name'] = str(initial_data['name']).title()
			if Product.objects.filter(name=initial_data['name']).exists():
				raise Exception('A product with this name already exists')
		if not settings.USE_S3 and ('video' in initial_data or 'picture' in initial_data):
			raise Exception('Unable to upload media. Server is currently unavailable.')
		if 'picture' in self.context:
			file_name = self.context['picture'].name
			extension = file_name.split(".")[-1]
			available_extensions = ('jpg', 'png', 'jpeg', 'webp')
			if extension.lower() not in available_extensions:
				raise Exception("File format not supported. Please use - {} files".format(available_extensions))
			initial_data['picture'] = self.context['picture']
		if 'video' in self.context:
			file_name = self.context['video'].name
			extension = file_name.split(".")[-1]
			available_extensions = ('mp4', '3gp', 'webm')
			if extension.lower() not in available_extensions:
				raise Exception("File format not supported. Please use - {} files".format(available_extensions))
			initial_data['video'] = self.context['video']
		return initial_data


class RemoveUserSubscriptionSerializer(serializers.Serializer):
	def update(self, instance, validated_data):
		pass

	def create(self, validated_data):
		pass

	subscription_id = serializers.IntegerField(min_value=1, required=True)

	def validate(self, initial_data):
		if not Subscription.objects.filter(id=initial_data['subscription_id']).exists():
			raise Exception('No license with this ID')
		from accounts.models import User
		if not User.objects.filter(id=self.context['user_id']).exists():
			raise Exception('No user with this ID')
		subscription = Subscription.objects.get(id=initial_data['subscription_id'])
		if subscription.company != self.context['company']:
			raise Exception('This license is not for this company')
		if self.context['user_id'] != subscription.user:
			raise Exception('This user is not subscribed to this license')
		return initial_data

	def execute(self):
		subscription = Subscription.objects.get(id=self.validated_data['subscription_id'])
		subscription.user = None
		subscription.save()
		from accounts.models import User
		user = User.objects.get(id=self.context['user_id'])
		from accounts.serializers import UserProfileSerializer
		data = {"user": UserProfileSerializer(user).data, "subscription": SubscriptionSerializer(subscription).data}
		return data


class AssignUserSubscriptionSerializer(serializers.Serializer):
	def update(self, instance, validated_data):
		pass

	def create(self, validated_data):
		pass

	subscription_id = serializers.IntegerField(min_value=1, required=True)

	def validate(self, initial_data):
		if not Subscription.objects.filter(id=initial_data['subscription_id']).exists():
			raise Exception('No license with this ID')
		from accounts.models import User
		if not User.objects.filter(id=self.context['user_id']).exists():
			raise Exception('No user with this ID')
		if Subscription.objects.filter(user=self.context['user_id'], company=self.context['company']).exists():
			raise Exception('This user is already subscribed to a license')
		subscription = Subscription.objects.get(id=initial_data['subscription_id'])
		if subscription.company != self.context['company']:
			raise Exception('This license is not for this company')
		if subscription.user is not None:
			raise Exception('This license is used')
		if subscription.active is not True:
			raise Exception('This license is not active')
		if subscription.expired():
			raise Exception('This license has expired ')
		return initial_data

	def execute(self):
		subscription = Subscription.objects.get(id=self.validated_data['subscription_id'])
		subscription.user = self.context['user_id']
		subscription.save()
		from accounts.models import User
		user = User.objects.get(id=self.context['user_id'])
		from accounts.serializers import UserProfileSerializer
		data = {"user": UserProfileSerializer(user).data, "subscription": SubscriptionSerializer(subscription).data}
		return data


class CancelSubscriptionsSerializer(serializers.Serializer):
	def update(self, instance, validated_data):
		pass

	def create(self, validated_data):
		pass

	def validate(self, initial_data):
		if not Product.objects.filter(id=self.context['product_id']).exists():
			raise Exception('No product with this ID')
		if not Subscription.objects.filter(company=self.context['company'], plan__product_id=self.context['product_id']).exists():
			raise Exception('No License exists for this product')
		return initial_data

	def execute(self):
		Subscription.objects.filter(company=self.context['company'], plan__product_id=self.context['product_id']).delete()
		from accounts.serializers import UserProfileSerializer
		return UserProfileSerializer(self.context['user']).data


class ConfirmSubSerializer(serializers.Serializer):
	company = serializers.CharField(max_length=70, required=True)
	email = serializers.EmailField(required=True)
	reference = serializers.CharField(max_length=100, required=True)
	amount = serializers.DecimalField(decimal_places=2, required=True, max_digits=14)
	result = serializers.ChoiceField(choices=['success', 'failed'], required=True)

	def update(self, instance, validated_data):
		pass

	def create(self, validated_data):
		pass

	def validate(self, initial_data):
		from Multitenant.classes import SchemaToTenant
		from Multitenant.classes import NameToSchema
		initial_data['company'] = SchemaToTenant(NameToSchema(initial_data['company']))
		return initial_data

	def execute(self):
		if self.validated_data['result'] == 'success':
			subscriptions = Subscription.objects.filter(company=self.validated_data['company'],
														transaction_ref=self.validated_data['reference'])
			subscriptions = (sub for sub in subscriptions if
							 Decimal(sub.transaction_log['amount']) >= Decimal(self.validated_data['amount']))
			for sub in subscriptions:
				sub.confirm()
			send_mail('Demo_CRM Platform', 'License purchase  is successful and now active.',
					  settings.EMAIL_HOST_USER, [self.validated_data['email']], fail_silently=True)

		elif self.validated_data['result'] == 'failed':
			subscriptions = Subscription.objects.filter(company=self.validated_data['company'],
														transaction_ref=self.validated_data['reference'])
			subscriptions.delete()
			send_mail('Demo_CRM Platform', 'License purchase Failed. Payment Failed.',
					  settings.EMAIL_HOST_USER, [self.validated_data['email']], fail_silently=True)
		else:
			return Response({'message': 'waiting'}, status=status.HTTP_204_NO_CONTENT)
		return Response({'message': 'ok'}, status=status.HTTP_200_OK)