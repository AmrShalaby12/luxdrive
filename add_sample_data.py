#!/usr/bin/env python
import os
import sys
import django

# إعداد Django
sys.path.append('/home/nixos/allen_bus_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main_Bus_Management.settings')
django.setup()

from Anaconda_bus_APP.models import Category, WeeklySchedule
from datetime import time

def add_sample_schedules():
    # جلب أول category
    category = Category.objects.first()
    if category:
        print(f"Found category: {category.name}")
        
        # إضافة جداول زمنية للذهاب
        schedules = [
            ('saturday', 'departure', time(7, 0)),
            ('sunday', 'departure', time(7, 0)),
            ('monday', 'departure', time(7, 0)),
            ('tuesday', 'departure', time(7, 0)),
            ('wednesday', 'departure', time(7, 0)),
            ('thursday', 'departure', time(7, 0)),
            ('saturday', 'return', time(15, 0)),
            ('sunday', 'return', time(15, 0)),
            ('monday', 'return', time(15, 0)),
            ('tuesday', 'return', time(15, 0)),
            ('wednesday', 'return', time(15, 0)),
            ('thursday', 'return', time(15, 0)),
        ]
        
        for day, trip_type, schedule_time in schedules:
            schedule, created = WeeklySchedule.objects.get_or_create(
                category=category,
                day_of_week=day,
                trip_type=trip_type,
                defaults={'time': schedule_time, 'is_active': True}
            )
            if created:
                print(f"Created schedule: {day} - {trip_type} - {schedule_time}")
            else:
                print(f"Schedule already exists: {day} - {trip_type} - {schedule_time}")
        
        print(f"Sample schedules added for {category.name}")
    else:
        print("No categories found")

if __name__ == "__main__":
    add_sample_schedules()
