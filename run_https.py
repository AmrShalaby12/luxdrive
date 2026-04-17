import os
from django.core.management import execute_from_command_line

# تحديد إعدادات المشروع
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main_Bus_Management.settings")

# تنفيذ أمر الخادم
if __name__ == "__main__":
    execute_from_command_line(["manage.py", "runserver_plus", "0.0.0.0:8082"])  # استخدم "runserver_plus"

