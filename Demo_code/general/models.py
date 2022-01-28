from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models

# Create your models here.
from django.utils import timezone

from Demo_CRM.storage_backends import PublicMediaStorage


class Product(models.Model):
	name = models.CharField(max_length=100, default=None, null=True, blank=True)
	description = models.TextField(default=None, null=True)
	picture = models.FileField(storage=PublicMediaStorage(), null=True, blank=True, default=None)
	video = models.FileField(storage=PublicMediaStorage(), null=True, blank=True, default=None)
	picture_url = models.URLField(null=True, blank=True, default=None)
	video_url = models.URLField(null=True, blank=True, default=None)
	homepage_url = models.URLField(default=None, null=True, blank=True)

	def __str__(self):
		return self.name

	def subscriptions(self):
		return Subscription.objects.filter(plan__product=self)

	def used_subscriptions(self):
		return Subscription.objects.filter(plan__product=self, user__isnull=False, active=True)

	def unused_subscriptions(self):
		return Subscription.objects.filter(plan__product=self, active=True, user__isnull=True)

	def expired_subscriptions(self):
		return Subscription.objects.filter(plan__product=self, active=True, expiry_date__lt=timezone.now())

	def current_users(self):
		return self.used_subscriptions().filter(expiry_date__gt=timezone.now()).count()

	def plans(self):
		return Plan.objects.filter(product=self)

	def video__url(self):
		try:
			return self.video.url
		except ValueError:
			return self.video_url

	def picture__url(self):
		try:
			return self.picture.url
		except ValueError:
			return self.picture_url

	@staticmethod
	def serialized_data():
		return list(Product.objects.values_list('name', flat=True))

class Plan(models.Model):
	class Choice:
		monthly, annually = range(2)
	name = models.CharField(max_length=100, default=None, null=True, blank=True)
	price_currency = models.CharField(max_length=10, default=None, null=True, blank=True)
	annual_price_value = models.DecimalField(decimal_places=2, max_digits=12, default=0)
	monthly_price_value = models.DecimalField(decimal_places=2, max_digits=12, default=0)
	description = models.TextField(default=None, null=True)
	features = ArrayField(base_field=models.CharField(max_length=255), default=list)
	product = models.ForeignKey('general.Product', on_delete=models.CASCADE, blank=True)

	def __str__(self):
		return self.name

	def subscriptions(self, **kwargs):
		return Subscription.objects.filter(plan=self, active=True, **kwargs)

	def used_subscriptions(self, **kwargs):
		return Subscription.objects.filter(plan=self, active=True, user__isnull=False, **kwargs)

	def unused_subscriptions(self, **kwargs):
		return Subscription.objects.filter(plan=self, active=True, user__isnull=True, **kwargs)

	def expired_subscriptions(self, **kwargs):
		return Subscription.objects.filter(plan=self, active=True, expiry_date__lt=timezone.now(), **kwargs)

	def unpaid_subscriptions(self, **kwargs):
		return Subscription.objects.filter(plan=self, active=False, user__isnull=True, **kwargs)

	@staticmethod
	def serialized_data():
		return list(Plan.objects.values('name', 'product__name'))

class Subscription(models.Model):
	company = models.ForeignKey('Tenant.Company', on_delete=models.CASCADE)
	plan = models.ForeignKey('general.Plan', on_delete=models.SET_NULL, null=True)
	user = models.PositiveIntegerField(default=None, null=True, blank=True)
	active = models.BooleanField(default=False)
	transaction_ref = models.CharField(max_length=100, default=None, null=True, blank=True)
	transaction_log = models.JSONField(default=dict, blank=True)
	activated_at = models.DateTimeField(default=None, blank=True, null=True)
	expiry_date = models.DateTimeField(default=None, blank=True, null=True)
	duration = models.PositiveIntegerField(default=0)
	time_choice = models.PositiveSmallIntegerField(choices=((Plan.Choice.monthly, 'Monthly'), (Plan.Choice.annually, 'Annually')), blank=True)

	def expired(self):
		if self.expiry_date:
			return self.expiry_date < timezone.now()
		return None

	def confirm(self):
		self.active = True
		duration = 0
		if self.time_choice == self.plan.Choice.monthly:
			duration = self.duration * 30
		elif self.time_choice == self.plan.Choice.annually:
			duration = self.duration * 365
		self.activated_at = timezone.now()
		self.expiry_date = timezone.now() + timedelta(days=duration)
		data = self.transaction_log
		data['txn_status'] = 'SUCCESS'
		self.transaction_log = data
		self.save()

	def total_price(self):
		if self.time_choice == Plan.Choice.annually:
			return self.plan.annual_price_value * self.duration
		elif self.time_choice == Plan.Choice.monthly:
			return self.plan.monthly_price_value * self.duration
		return 0

	def duration_str(self):
		time = 'Month(s)' if self.time_choice == Plan.Choice.monthly else 'Year(s)'
		return f'{self.duration} {time}'

	def user_(self):
		from accounts.models import User
		if self.user is not None:
			return User.objects.get(id=self.user)
		return None

	def used(self):
		return self.user is not None and self.active is True

	@staticmethod
	def serialized_data():
		return list(Subscription.objects.values('user', 'plan__product', 'plan__name',
													 'transaction_ref', 'expiry_date'))
