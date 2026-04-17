from rest_framework import serializers
from .models import SpeedData

class SpeedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeedData
        fields = '__all__'
# api/serializers.py

from rest_framework import serializers
from Anaconda_bus_APP.models import Trip, Booking, passenger, Bus, FormReservation

# Serializer بسيط لتفاصيل الراكب
class PassengerSerializer(serializers.ModelSerializer):
    class Meta:
        model = passenger
        fields = ['id', 'name', 'phone_number', 'university_code', 'category']

# Serializer بسيط لتفاصيل الحافلة
class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ['id', 'name', 'plate_number', 'driver_number', 'capacity']

# Serializer لعرض الحجوزات داخل تفاصيل الرحلة
class BookingForTripSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='passenger.name', read_only=True)
    passenger_phone = serializers.CharField(source='passenger.phone_number', read_only=True)
    
    class Meta:
        model = Booking
        fields = ['id', 'passenger_name', 'passenger_phone', 'status', 'attendance_status']

# Serializer لعرض تفاصيل الرحلة الكاملة
class TripDetailSerializer(serializers.ModelSerializer):
    bus = BusSerializer(read_only=True)
    bookings = BookingForTripSerializer(many=True, read_only=True) # عرض الحجوزات المرتبطة

    class Meta:
        model = Trip
        fields = [
            'id', 'trip_name', 'date', 'start_time', 'back_time', 
            'trip_type', 'bus', 'bookings'
        ]

# Serializer لعرض قائمة الرحلات (نسخة مختصرة)
class TripListSerializer(serializers.ModelSerializer):
    bus_name = serializers.CharField(source='bus.name', read_only=True)
    driver_number = serializers.CharField(source='bus.driver_number', read_only=True)

    class Meta:
        model = Trip
        fields = ['id', 'trip_name', 'date', 'start_time', 'bus_name', 'driver_number']

# Serializer لإنشاء وتعديل الحجز
class BookingCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        # حدد الحقول التي يمكن للمستخدم إدخالها عند إنشاء أو تعديل حجز
        fields = ['passenger', 'Trip', 'trip_type', 'selected_route', 'payment_method']

# Serializer لعرض حجوزات راكب معين
class PassengerBookingHistorySerializer(serializers.ModelSerializer):
    trip_name = serializers.CharField(source='Trip.trip_name', read_only=True)
    trip_date = serializers.DateField(source='Trip.date', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'trip_name', 'trip_date', 'status', 'trip_type']

# Serializer لعرض بيانات الراكب مع حجوزاته
class PassengerDetailSerializer(serializers.ModelSerializer):
    # استخدام Serializer الحجوزات الذي أنشأناه في الأعلى
    bookings = PassengerBookingHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = passenger
        fields = [
            'id', 'name', 'phone_number', 'university_code', 'category', 
            'subscription_end_date', 'remaining_rides', 'bookings'
        ]

# Serializer لإحصائيات الحجوزات
class BookingStatsSerializer(serializers.Serializer):
    total_bookings = serializers.IntegerField()
    today_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()

# Serializer لموقع الحافلة المباشر
class BusLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ['id', 'name', 'latitude', 'longitude', 'location_sharing_is_active']
