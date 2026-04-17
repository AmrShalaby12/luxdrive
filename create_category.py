import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main_Bus_Management.settings")
django.setup()

from Anaconda_bus_APP.models import Category

try:
    Category.objects.get_or_create(name="رحلة")
    print("Category \"رحلة\" created or already exists.")
except Exception as e:
    print(f"Error creating category: {e}")

