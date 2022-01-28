from __future__ import absolute_import
import os
from celery import Celery
from celery.schedules import crontab
from django.conf import settings
from tasks import delete_task

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Demo_CRM.settings')
app = Celery('Demo_CRM')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(minute=0, hour=0), delete_task.s())


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))