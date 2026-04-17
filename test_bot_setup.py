#!/usr/bin/env python3

import os
import sys

# Add project path
sys.path.append("/app")

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main_Bus_Management.settings")

try:
    import django
    django.setup()
    print("✅ Django setup successful")
    
    from django.conf import settings
    token = settings.TELEGRAM_BOT_TOKEN
    
    if token:
        print(f"✅ Token found: {token[:10]}...")
    else:
        print("❌ No token found in settings")
        
    # Test importing models
    from Anaconda_bus_APP.models import passenger, Trip, Booking, Bus
    print("✅ Models imported successfully")
    
    # Test passenger count
    passenger_count = passenger.objects.count()
    print(f"✅ Found {passenger_count} passengers in database")
    
    # Test telegram_id field
    passengers_with_telegram = passenger.objects.filter(telegram_id__isnull=False).count()
    print(f"✅ Found {passengers_with_telegram} passengers with telegram_id")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
