# bus_app/tasks.py
from celery import shared_task
from .utils import check_and_send_due_installments

@shared_task
def send_due_installments_task():
    check_and_send_due_installments()
