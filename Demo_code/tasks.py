from celery import Celery
from django.utils import timezone
from django_tenants.utils import schema_context

app = Celery('Demo_CRM')

@app.task
def delete_task():
    from Tenant.models import Company
    tenants = Company.objects.all().values_list('schema_name')
    for schema in tenants:
        with schema_context(schema):
            from accounts.models import User
            User.objects.filter(deletion_date=timezone.now().date()).delete()
            from shared.models import Service
            Service.objects.filter(deletion_date=timezone.now().date()).delete()
            from module.models import Module
            modules = Module.objects.filter(deletion_date=timezone.now().date())
            names = modules.values_list('name', flat=True)
            for name in names:
                from Permission.permissions import delete_module_permissions
                delete_module_permissions(name)
            modules.delete()
