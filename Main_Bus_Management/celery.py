import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main_Bus_Management.settings')

app = Celery('Main_Bus_Management')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'send-installment-reminders-every-morning': {
        'task': 'Anaconda_bus_APP.tasks.send_due_installments_task',  
        'schedule': crontab(hour=9, minute=0),  # كل يوم 9 صباحاً
    },
}
