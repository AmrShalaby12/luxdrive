#shalaby commet 29
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
import qrcode 
from django.core.files import File
from io import BytesIO
from datetime import timedelta, date
from datetime import date, timedelta
from io import BytesIO
import qrcode
from django.db import models
from datetime import date, timedelta
from io import BytesIO
import qrcode
from django.contrib.auth.models import AbstractUser
from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # تعديل الحقول لإضافة related_name لتجنب التصادم
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',  # قم بتغيير اسم الaccessor هنا
        blank=True,
        help_text='The groups this user belongs to.',
        related_query_name='customuser'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_permissions',  # قم بتغيير اسم الaccessor هنا
        blank=True,
        help_text='Specific permissions for this user.',
        related_query_name='customuser_permission'
    )
from django.core.validators import RegexValidator
import requests
import numpy as np
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile
import numpy as np
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.core.files.base import ContentFile
from datetime import date, timedelta
from io import BytesIO
from PIL import Image
import qrcode
import requests


class passenger(models.Model):  
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='passenger', 
        verbose_name="المستخدم",
        null=True,  
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[\u0600-\u06FFa-zA-Z0-9_ ]+$',
                message="يمكنك استخدام الحروف العربية والإنجليزية والأرقام والمسافات فقط."
            )
        ]
    )
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_token = models.CharField(max_length=64, null=True, blank=True, unique=True)
    def generate_telegram_token(self):
        self.telegram_token = secrets.token_urlsafe(32)
        self.save()
    face_thumbnail = models.ImageField(
        upload_to="faces/thumbnails/",
        null=True,
        blank=True,
        verbose_name="صورة الطالب"
    )

    USER_TYPES = [
        ('student', 'طالب جامعي'),
        ('regular', 'مستخدم عادي'),
    ]
    GENDER_TYPES = [
        ('Male', 'ذكر '),
        ('Female', 'انثي '),
    ]

    fixed_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP الثابت")
    university_code = models.CharField(max_length=20, verbose_name="الكود الجامعي", null=True, blank=True, unique=True)
    phone_number = models.CharField(max_length=20, verbose_name="رقم الهاتف", null=True, blank=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="الجامعه")
    name = models.CharField(max_length=64, verbose_name="اسم الطالب")
    subscription_duration = models.IntegerField(verbose_name="مدة الاشتراك")  
    subscription_start_date = models.DateField(verbose_name="تاريخ بداية الاشتراك", null=True, blank=True, editable=False)
    subscription_end_date = models.DateField(verbose_name="تاريخ نهاية الاشتراك", null=True, blank=True, editable=False)
    qr_code = models.BinaryField(null=True, blank=True)
    rides_used = models.IntegerField(default=0, verbose_name="عدد الرحلات المستخدمة")
    last_selected_route = models.CharField(max_length=255, blank=True, null=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='student')
    gender = models.CharField(max_length=20, choices=GENDER_TYPES, null=True, blank=True, verbose_name="الجنس")
    gender_selected = models.BooleanField(default=False)
    parent_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="رقم ولي الأمر")

    @property
    def available_trips(self):
        return self.remaining_rides

    @property
    def total_rides(self):
        return self.subscription_duration

    @property
    def remaining_rides(self):
        remaining = self.total_rides - self.rides_used
        return max(remaining, 0)

    def save(self, *args, **kwargs):
        # تحديث تاريخ البداية والنهاية
        if not self.subscription_start_date:
            self.subscription_start_date = date.today()
        self.subscription_end_date = self.subscription_start_date + timedelta(days=30 * self.subscription_duration)

        # تحديث gender_selected
        if self.gender:
            self.gender_selected = True

        # لو فيه صورة طالب، نصغرها ونضغطها
        if self.face_thumbnail:
            img = Image.open(self.face_thumbnail)
            img = img.convert("RGB")   # تأكد أنها ملونة
            img.thumbnail((300, 300))  # نصغرها
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=100)  # نضغط الجودة
            file_name = f"{self.name}_face.jpg"
            self.face_thumbnail.save(file_name, ContentFile(buffer.getvalue()), save=False)

        # إنشاء كود QR
        qr_data = (
            f"Product ID: {self.id}, "
            f"Name: {self.name}, "
            f"University Code: {self.university_code}, "
            f"Category: {self.category.name if self.category else 'N/A'}, "
            f"Start Date: {self.subscription_start_date}, "
            f"End Date: {self.subscription_end_date}"
        )
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        img_qr = qr.make_image(fill='black', back_color='white')
        buffer = BytesIO()
        img_qr.save(buffer, format="PNG")
        self.qr_code = buffer.getvalue()

        super().save(*args, **kwargs)

    @classmethod
    def send_whatsapp_message(cls, message, passengers):
        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

        for passenger in passengers:
            if passenger.phone_number:
                payload = {
                    "token": API_TOKEN,
                    "to": passenger.phone_number,
                    "body": message
                }
                requests.post(URL, data=payload)

        return f"✅ تم إرسال الرسالة إلى {len(passengers)} راكباً."

    class Meta:
        verbose_name = ' ادارة الركاب '
        verbose_name_plural = '   اداره الركاب '

    def __str__(self):
        return f"{str(self.id).zfill(4)} - {self.name}"


class AdminSettings(models.Model):
    custom_whatsapp_message = models.TextField(
        default="مرحبا {name}، تم تأكيد حجزك في الاشتراك {subscription} بحالة {status} ورمز المعاملة {transaction_code}.",
        help_text="يمكنك استخدام المتغيرات: {name}, {subscription}, {status}, {transaction_code}."
    )

    def __str__(self):
        return "إعدادات المشرف"

# --------------------
# models.py
from django.db import models
class Route(models.Model):
    from_location = models.CharField(max_length=100)
    to_location = models.CharField(max_length=100)
    date = models.DateField()

    def __str__(self):
        return f"{self.from_location} to {self.to_location} on {self.date}"
class Category(models.Model):
    name = models.CharField(max_length=64, verbose_name="اسم الجامعة")
    admin_name = models.CharField(max_length=255, verbose_name="اسم مسؤول الجامعة", null=True, blank=True)
    admin_phone_number = models.CharField(max_length=20, verbose_name="رقم هاتف مسؤول الجامعة", null=True, blank=True)
    Day_support = models.BooleanField(default=False, verbose_name="دعم اشتراك اليوم")  
    Form_support = models.BooleanField(default=False, verbose_name="حجز بأستخدام فورم") 
    Form_active = models.BooleanField(default=True)  # ✅ الحقل الجديد
    one_way_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    round_trip_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allow_cash_payment = models.BooleanField(default=False, verbose_name="السماح بالدفع نقداً")  # 🔥 الحقل الجديد
    one_way_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=25.00,  # يمكنك وضع سعر افتراضي
        verbose_name="سعر رحلة الذهاب أو العودة"
    )
    # هذا سعر الرحلة الكاملة (ذهاب وعودة معاً)
    round_trip_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=50.00,  # يمكنك وضع سعر افتراضي
        verbose_name="سعر رحلة الذهاب والعودة"
    )

    class Meta:
        verbose_name = 'اداره الجامعات'              
        verbose_name_plural = ' الجامعات المضافه  '

    def __str__(self):
        return self.name



from django.db import models

from django.conf import settings  # هذا هو السطر المطلوب إضافته


from django.contrib.auth.models import User  
# استيراد نموذج المستخدم
from django.db import models
from django.contrib.auth.models import User

import os
import telnetlib
import datetime
from django.db import models
from django.contrib.auth.models import User

class Bus(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الباص")
    capacity = models.PositiveIntegerField(verbose_name="السعة الكلية")
    plate_number = models.CharField(max_length=50, verbose_name="رقم النمر")
    driver_number = models.CharField(max_length=50, verbose_name="رقم السائق", blank=True, null=True)
    bus_type = models.CharField(max_length=100, verbose_name="نوع الباص")
    location_url = models.URLField(blank=True, null=True)  # رابط الموقع
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    location_sharing_is_active = models.BooleanField(default=False, verbose_name="مشاركة الموقع نشطة؟")
    location_sharing_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت انتهاء مشاركة الموقع")

    is_active = models.BooleanField(default=False, verbose_name="نشط")

    category = models.ForeignKey(
        'Category', 
        on_delete=models.CASCADE, 
        related_name='buses', 
        verbose_name="الجامعة",
        default='-----',
    )
    Bus_driver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='buses',
        verbose_name="سائق الباص",
        null=True,  
        blank=True
    )
    seats_image = models.ImageField(upload_to='bus_seats/', blank=True, null=True, verbose_name="صورة الكراسي")
    esp_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP كاميرا ESP32")  # ✅ جديد
    bus_image = models.ImageField(upload_to='bus_seats/', blank=True, null=True, verbose_name="صورة الباص")
    class Meta:
        verbose_name = ' الباصات المضافه للرحلات'              
        verbose_name_plural = '  الباصات المضافه  '

    LAST_ONLINE_FILE = "last_online.txt"

    def is_online(self):
        """التأكد مما إذا كان الباص متصلًا بالإنترنت"""
        try:
            with open("bus_status.log", "w", encoding="utf-8") as f:
                last_online = "متصل الآن" 
                f.write(f"آخر وقت اتصال: {last_online}\n")
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False

    def __str__(self):
        return f"{self.name} ({self.category.name}) - {'🟢 متصل' if self.is_online() else '🔴 غير متصل'}"

from django.dispatch import receiver
from django.db.models.signals import post_save

from django.db import models
import datetime

# class Seat(models.Model):
#     bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats')
#     seat_number = models.IntegerField()
#     is_reserved = models.BooleanField(default=False)
#     trip_date = models.DateField(default=datetime.date.today, verbose_name="تاريخ الرحلة")  # تاريخ الرحلة

#     class Meta:
#         unique_together = ('bus', 'seat_number', 'trip_date')  # إضافة قيد فريد على الحقول
# models.py
class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name='seats', null=True, blank=True)
    seat_number = models.IntegerField()
    is_reserved = models.BooleanField(default=False)
    trip_date = models.DateField(null=True)
    row = models.IntegerField(null=True, blank=True)  # الصف
    column = models.IntegerField(null=True, blank=True)  # العمود

    def __str__(self):
        return f"Seat {self.seat_number} on {self.bus.name}"

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Bus, Seat
from dateutil.relativedelta import relativedelta  # لإضافة أشهر

@receiver(post_save, sender=Bus)
def create_seats(sender, instance, created, **kwargs):
    if created and instance.seats.count() == 0: 
        for seat_number in range(1, instance.capacity + 1):
            Seat.objects.create(bus=instance, seat_number=seat_number)

class destination(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم الوجهه")
    class Meta:
        verbose_name = ' اداره الوجهات '
        verbose_name_plural = 'اداره الوجهات'

    def __str__(self):
        return self.name

class Trip(models.Model):
    
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, verbose_name="الجامعة" , null=True, blank=True  
    )
    TRIP_TYPE_CHOICES = [
        ('one_way', 'ذهاب'),
        ('return', 'عودة'),
        ('round_trip', 'ذهاب وعودة'),
        ('round_differentdays', 'ذهاب وعودة (في أيام مختلفة)'),

    ]
    
    related_departure_trip = models.ForeignKey(
    'self',
    null=True, blank=True,
    on_delete=models.SET_NULL,
    related_name='round_trip_departures',
    verbose_name='رحلة الذهاب (موجودة مسبقاً)'
    )

    related_return_trip = models.ForeignKey(
        'self',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='round_trip_returns',
        verbose_name='رحلة العودة (موجودة مسبقاً)'
    )
    departure_seat_price = models.DecimalField(
        max_digits=6, decimal_places=2,
        verbose_name="سعر كرسي الذهاب (أيام مختلفة)",
        null=True, blank=True
    )
    return_selected_route = models.CharField(max_length=255, null=True, blank=True, verbose_name="نقطة النزول في العودة")  # 🆕 مضافة حديثاً

    return_seat_price = models.DecimalField(
        max_digits=6, decimal_places=2,
        verbose_name="سعر كرسي العودة (أيام مختلفة)",
        null=True, blank=True
    )
    DRIVER_STATUS_CHOICES = [
        ('not_arrived', 'لم يصل بعد'),
        ('arrived', 'وصل'),
    ]
    
    route = models.TextField(
        verbose_name="الطريق", 
        default="", 
        help_text="أدخل كل خط في سطر جديد."
    )    
    trip_name = models.TextField(verbose_name="اسم الرحله", default="")
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE , default=1 , null=True, blank=True, verbose_name="الباص")
    date = models.DateField(verbose_name="التاريخ",null=True, blank=True)
    start_time = models.TimeField(verbose_name="وقت الذهاب ", default='00:00:00')
    back_time = models.TimeField(verbose_name="وقت العوده ", default='00:00:00')

    end_time = models.TimeField(verbose_name="وقت التحرك ", default='00:00:00')
    trip_type = models.CharField(
        max_length=30,
        choices=TRIP_TYPE_CHOICES,
        default='round_trip',
        verbose_name="نوع الرحلة"
    )
    # driver_status = models.CharField(
    #     max_length=20,
    #     choices=DRIVER_STATUS_CHOICES,
    #     default='not_arrived',
    #     verbose_name="حالة السائق"
    # )
    start_destination = models.ForeignKey(
        destination,
        on_delete=models.CASCADE,
        related_name='start_schedules',
        verbose_name="البدايه",
    null=True,  
    blank=True    )
    end_destination = models.ForeignKey(
        destination,
        on_delete=models.CASCADE,
        related_name='end_schedules',
        verbose_name="النهايه",
    null=True, 
    blank=True    )
    one_way_price = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="سعر الذهاب فقط", default=1
    )
    return_price = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="سعر العودة فقط", default=1
    )
    round_trip_price = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="سعر الذهاب و العودة", default=1
    )
    is_active = models.BooleanField(default=True)  # لتحديد إذا كانت الرحلة نشطة
    next_trip_date = models.DateTimeField(null=True, blank=True)  # تاريخ الرحلة التالية
    is_old = models.BooleanField(default=False) 
    class Meta:
        verbose_name = ' اداره الرحلات '
        verbose_name_plural = 'اداره  الرحلات'

    def __str__(self):
        # عرض اسم الرحلة (trip_name) إذا كان موجودًا، وإلا يتم عرض تفاصيل أخرى
        return f"{self.trip_name}" if self.trip_name else f"Trip from {self.start_destination} to {self.end_destination}"

from django.contrib.auth.models import User

from django.contrib.auth.models import User

from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models

from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid 
import secrets

class TelegramBotToken(models.Model):
    bot_username = models.CharField(max_length=100, unique=True, verbose_name="Bot Username")
    bot_token = models.CharField(max_length=200, verbose_name="Bot Token")
    webhook_url = models.URLField(blank=True, null=True, verbose_name="Webhook URL")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"@{self.bot_username}"

class Booking(models.Model):
    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('online', 'Online'),
        ('subscription' , 'subscription')
    ]  
    TRIP_TYPE_CHOICES = [
        ('one_way', 'ذهاب فقط'),
        ('return', 'عودة فقط'),
        ('round_trip', 'ذهاب وعودة'),
    ]
    STATUS_CHOICES = [
        ('active', 'نشط'),
        ('pending', 'قيد الانتظار'),  # ✅ جديدة

        ('completed', 'مكتمل'),
        ('cancelled', 'ملغي'),
        ("prepaid", 'مدفوع مسبقًا'),  # إضافة الخيار الجديد

    ]
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
    ]
    
    passenger = models.ForeignKey(
        passenger,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="الراكب",
        default=1,

    )
        
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        verbose_name= 'حاله الدفع'
    )
    attendance_status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_CHOICES,
        default='absent',
        verbose_name='حاله الحضور',
    )
    departure_trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE,
        related_name='departure_bookings',
        null=True, blank=True,
        verbose_name="رحلة الذهاب"
    )

    return_trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE,
        related_name='return_bookings',
        null=True, blank=True,
        verbose_name="رحلة العودة"
    )

    departure_seats = models.ManyToManyField(
        Seat, related_name='departure_bookings',
        blank=True,
        verbose_name="كراسي الذهاب"
    )

    return_seats = models.ManyToManyField(
        Seat, related_name='return_bookings',
        blank=True,
        verbose_name="كراسي العودة"
    )

    return_route = models.CharField(
        max_length=255, null=True, blank=True,
        verbose_name="نقطة النزول في العودة"
    )

    booking_date = models.DateTimeField(auto_now_add=True, null=True,verbose_name="تاريخ الحجز")
    Trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='bookings', default='',verbose_name="الرحله")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookings', default=1,verbose_name="المستخدم")
    selected_route = models.CharField(max_length=255, null=True, blank=True)
    seats_reserved = models.ManyToManyField(Seat, related_name='bookings',verbose_name="الكراسي المحجوزه")
    transfer_message = models.TextField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    transaction_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        unique=True,
        error_messages={'unique': 'رقم المعاملة مستخدم بالفعل'}
    )
    mobile_number = models.CharField(max_length=15, blank=True, null=True,    verbose_name="الرقم المحول منه")
    transaction_image = models.ImageField(upload_to='transactions/', blank=True, null=True)
    trip_type = models.CharField(
        max_length=20,
        choices=TRIP_TYPE_CHOICES,
        default='round_trip',
        verbose_name=_("Trip Type"),
    )

    telegram_token = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Telegram Token"
    )

    serial_code = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True,
        verbose_name="كود الرحلة"
    )

    def reserved_seats_list(self):
        return ", ".join([f"Seat {seat.seat_number}" for seat in self.seats_reserved.all()])
    reserved_seats_list.short_description = "الكراسي المحجوزة"
    def reserved_seats_count(self):
        return self.seats_reserved.count()
    reserved_seats_count.short_description = "عدد الكراسي المحجوزة"

    def passenger_phone(self):
        """Retrieve the passenger's phone number."""
        if self.passenger and self.passenger.phone_number:
            return self.passenger.phone_number
        return "No Phone"
    passenger_phone.short_description = "Passenger Phone"

    def save(self, *args, **kwargs):
        # ضغط صورة التحويل
        if self.transaction_image:
            img = Image.open(self.transaction_image)
            output = BytesIO()
            img = img.convert('RGB')
            img.thumbnail((800, 800))
            img.save(output, format='JPEG', quality=70)
            output.seek(0)
            self.transaction_image = ContentFile(output.read(), self.transaction_image.name)

        # إنشاء الكود التسلسلي إذا لم يكن موجودًا
        if not self.serial_code:
            self.serial_code = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
        
        # إنشاء توكن تيليجرام إذا لم يكن موجودًا
        if not self.telegram_token:
            self.telegram_token = secrets.token_urlsafe(16)

        # استدعاء دالة الحفظ الأساسية
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # إرسال تأكيد التليجرام إذا كان حجز جديد
        if is_new and self.passenger and self.passenger.telegram_id:
            try:
                # استدعاء دالة إرسال التأكيد
                import asyncio
                from .bot.telegram_bot import send_booking_confirmation
                
                # تشغيل الدالة بشكل غير متزامن
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(send_booking_confirmation(self.id))
            except Exception as e:
                print(f"Error sending Telegram confirmation: {e}")
    class Meta:
        verbose_name = ' اداره الحجوزات '
        verbose_name_plural = 'اداره حجوزات الرحلات'

    def __str__(self):
        passenger_phone = self.passenger.phone_number if self.passenger and self.passenger.phone_number else "No Phone"
        return f"Booking {self.id} - {self.user.username} - {self.trip_type} - Phone: {passenger_phone}"

from django.db import models

class Report(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=1)  # تأكد أن الـ ID 1 موجود
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, default=1)  # تأكد أن هناك Trip بـ ID=1
    report_text = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import date

from django.db import models
from django.utils import timezone
from datetime import timedelta

class Attendance(models.Model):
    name = models.CharField(max_length=100, verbose_name='اسم الطالب')
    user_id = models.CharField(max_length=100, verbose_name='كود الطالب')
    category = models.CharField(max_length=255, verbose_name='الجامعة')
    subscription_start_date = models.DateField(verbose_name='تاريخ بداية الاشتراك')
    subscription_end_date = models.DateField(verbose_name='تاريخ نهاية الاشتراك')
    attendance_date = models.DateField(default=timezone.now, verbose_name='موافق يوم')
    ATTENDANCE_CHOICES = [
        ('حضور', 'حضور'),
        ('انصراف', 'انصراف'),
        ('غياب', 'غياب'),
    ]
#رحله الذاهب رحله العوده حضور
# جدول الاشتراكات
# cancle date >> boking
# date مينفعش تتكرر
    attendance_status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_CHOICES,
        default='غياب',
        verbose_name='حالة الحضور',
    )
    departure_status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_CHOICES,
        default='غياب',
        verbose_name='حالة الانصراف',
    )
    ride_deducted = models.BooleanField(default=False, verbose_name='تم خصم الرحلة')  # جديد

    def __str__(self):
        return f"{self.name} - {self.attendance_status} / {self.departure_status} - {self.attendance_date}"

    @classmethod
    def mark_attendance(cls, user_id, status, is_departure=False):
        """تسجيل الحضور أو الانصراف وخصم رحلة واحدة فقط في اليوم"""
        today = timezone.now().date()
        attendance_record, created = cls.objects.get_or_create(
            user_id=user_id,
            attendance_date=today,
            defaults={
                'attendance_status': 'غياب',
                'departure_status': 'غياب',
                'ride_deducted': False,  
            }
        )

        if not is_departure and status == 'حضور':
            attendance_record.attendance_status = status
        elif is_departure and status == 'انصراف':
            attendance_record.departure_status = status

        if not attendance_record.ride_deducted:
            student = passenger.objects.filter(user__id=user_id).first()  
            if student and student.remaining_rides > 0:
                student.rides_used += 1  
                student.save()
                attendance_record.ride_deducted = True

        attendance_record.save()
        return attendance_record

from django.db import models
from django.utils.translation import gettext_lazy as _

from datetime import timedelta, date
def default_display_date():
    return date.today() + timedelta(days=1)











from django.db import models

class PaymentAccount(models.Model):
    PAYMENT_OPTIONS = [
        ('vf-cash', 'VF Cash'),
        ('instapay', 'InstaPay'),
        ('fawry', 'Fawry'),
    ]

    payment_option = models.CharField(max_length=20, choices=PAYMENT_OPTIONS)
    account_name = models.CharField(max_length=100)  # اسم الحساب أو الجهة
    account_number = models.CharField(max_length=50)  # رقم الحساب للتحويل
    additional_info = models.TextField(blank=True, null=True)  # معلومات إضافية، مثل الفرع أو الملاحظات

    def __str__(self):
        return f"{self.get_payment_option_display()} - {self.account_name}"

class Payment(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'نقداً'),
        ('online', 'أونلاين'),
    ]
    STATUS_CHOICES = [
        ('pending', 'قيد المراجعة'),
        ('completed', 'مكتمل'),
        ('failed', 'فشل'),
    ]
    booking = models.OneToOneField(
        'Booking',
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name="الحجز",
        null=True,  # السماح بالقيم الفارغة
        blank=True 
    )
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES,         null=True,  # السماح بالقيم الفارغة
        blank=True )
    payment = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,        null=True,  # السماح بالقيم الفارغة
        blank=True )

from django.db import models
from datetime import date

# class AttendanceRecord(models.Model):
#     student = models.ForeignKey('passenger', on_delete=models.CASCADE, related_name="attendance_records", verbose_name="الطالب")
#     date = models.DateField(default=date.today, verbose_name="تاريخ")
#     attendance_type = models.CharField(
#         max_length=10,
#         choices=[('arrival', 'حضور'), ('departure', 'انصراف')],
#         verbose_name="نوع التسجيل"
#     )

#     class Meta:
#         unique_together = ('student', 'date', 'attendance_type')  # كل تسجيل حضور/انصراف فريد ليوم معين

#     def __str__(self):
#         return f"{self.student.name} - {self.date} - {self.get_attendance_type_display()}"
from django.db import models

# class SubscriptionTransaction(models.Model):
#     student = models.ForeignKey(
#         'passenger',
#         on_delete=models.CASCADE,
#         verbose_name="الطالب"
#     )
#     subscription_type = models.ForeignKey(
#         'SubscriptionType',
#         on_delete=models.CASCADE,
#         verbose_name="نوع الاشتراك",
#         null=True,
#         blank=True
#     )
#     amount = models.DecimalField(
#         max_digits=10, 
#         decimal_places=2,
#         verbose_name="المبلغ المطلوب", null=True, blank=True
#     )
#     transaction_number = models.CharField(
#         max_length=50,
#         unique=True,
#         verbose_name="رقم المعاملة", null=True, blank=True
#     )
#     transferred_from_number = models.CharField(
#         max_length=20,
#         verbose_name="الرقم المحول منه", null=True, blank=True
#     )
#     transfer_message = models.TextField(
#         verbose_name="رسالة التحويل"
#     )
#     status = models.CharField(
#         max_length=20,
#         choices=[
#             ('pending', 'قيد الانتظار'),
#             ('approved', 'تمت الموافقة'),
#             ('rejected', 'مرفوض')
#         ],
#         default='pending',
#         verbose_name="حالة المعاملة", null=True, blank=True
#     )
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء", null=True, blank=True)

#     def save(self, *args, **kwargs):
#         # إذا كانت الحالة "approved"، أضف عدد الرحلات المشمولة إلى الطالب
#         if self.status == 'approved':
#             subscription = self.subscription_type
#             if subscription:
#                 # أضف عدد الرحلات المشمولة إلى Total Rides للراكب
#                 self.student.rides_used += subscription.included_trips
#                 self.student.save()
#         super().save(*args, **kwargs)


# class SubscriptionType(models.Model): 
#     duration = models.IntegerField(
#         choices=[
#             (1, "اشتراك شهر واحد"),
#             (3, "اشتراك 3 أشهر"),
#             (6, "اشتراك 6 أشهر"),
#             (12, "اشتراك 12 شهرًا"),
#         ],
#         unique=True,
#         verbose_name="مدة الاشتراك"
#     )
#     price_per_trip = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         verbose_name="سعر الرحلة",
#         null=True,
#         blank=True
#     )
#     included_trips = models.IntegerField(
#         default=0,
#         verbose_name="عدد الرحلات المشمولة"
#     )

#     def __str__(self):
#         return f"{self.get_duration_display()} - {self.price_per_trip} جنيه لكل رحلة ({self.included_trips} رحلة مشمولة)"
from django.db import models
from django.contrib.auth.models import User

from django.db import models

class Subscription(models.Model):
    DURATION_CHOICES = [
        (12, 'باقه'),
        (7, 'أسبوع'),
        (30, 'شهر'),
        (48, 'نصف ترم'),
        (96, 'ترم كامل'),
        (192, 'سنة كاملة'),
    ]

    number_of_trips = models.IntegerField(default=0, verbose_name="عدد الرحلات")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="الفئة")
    subscription_duration = models.IntegerField(choices=DURATION_CHOICES, verbose_name="مدة الاشتراك",null=True,blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")
    description = models.TextField(verbose_name="الوصف", null=True, blank=True)
    class Meta:
        verbose_name = '  اضافه اشتراك للطلاب'              
        verbose_name_plural = '  الاشتراكات '

    def __str__(self):
        return f"{self.get_subscription_duration_display()} - {self.category.name}"
from django.db import models
from django.contrib.postgres.fields import ArrayField  # لو PostgreSQL
from django.core.exceptions import ValidationError

class InstallmentPlan(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="installment_plans")
    name = models.CharField(max_length=100, verbose_name="اسم الخطة (مثال: 3 أقساط كل شهر)")
    number_of_installments = models.IntegerField(verbose_name="عدد الأقساط")
    interval_days = models.IntegerField(default=30, verbose_name="الفاصل بين الأقساط (بالأيام)")
    increase_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="نسبة الزيادة %")
    installment_percentages = ArrayField(
        models.DecimalField(max_digits=5, decimal_places=2),
        verbose_name="النسب المئوية لكل دفعة (مجموعها = 100%)",
        default=list
    )

    def clean(self):
        if sum(self.installment_percentages) != 100:
            raise ValidationError("مجموع نسب الدفعات يجب أن يساوي 100%.")

    def __str__(self):
        return f"{self.name} - {self.subscription}"
class Installment(models.Model):
    plan = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE, related_name="installments")
    passenger = models.ForeignKey('passenger', on_delete=models.CASCADE, related_name="installments")
    due_date = models.DateField(verbose_name="تاريخ الاستحقاق")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قيمة القسط")
    is_paid = models.BooleanField(default=False, verbose_name="مدفوع")

    def __str__(self):
        return f"قسط {self.amount} - {self.passenger} - {self.due_date}"

from django.db import models
import uuid
STATUS_CHOICES = [
    ('pending', 'قيد الانتظار'),
    ('completed', 'مكتمل'),
    ('canceled', 'ملغي'),
    ('indebtedness', 'مديونيه'),
    ('Reviewed', 'تم المراجعه'),
    
]

class SubscriptionBooking(models.Model):
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الحجز")
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE, verbose_name="الاشتراك")
    passenger = models.ForeignKey('passenger', on_delete=models.CASCADE, verbose_name="الراكب")
    transaction_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="كود المعاملة"
    )
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="المبلغ المدفوع", null=True, blank=True)
    account_info = models.CharField(max_length=100, verbose_name="اسم أو رقم الحساب المحول منه", null=True, blank=True)
    payment_proof = models.ImageField(
        upload_to='compressed_proofs/',
        verbose_name="صورة التحويل",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء", null=True, blank=True)
    status = models.CharField(
        choices=STATUS_CHOICES,
        default='pending',  # القيمة الافتراضية الجديدة
        verbose_name="حالة الحجز"
    )
    indebtedness_reason = models.TextField(null=True, blank=True , verbose_name="سبب او قيمه المديونيه ")

    number_of_trips = models.IntegerField(default=0, verbose_name="عدد الرحلات")
    class Meta:
        verbose_name = 'حجوزات اشتراكات الطلاب'
        verbose_name_plural = 'حجوزات اشتراكات الطلاب'

    def __str__(self):
        return f"حجز: {self.subscription} - {self.passenger}"

from django.db import models
from django.db import models
from django.core.exceptions import ValidationError
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.validators import RegexValidator

# 🚗 **Model: Car**
class Car(models.Model):
    name = models.CharField(max_length=100 , verbose_name="اسم السيارة")
    model = models.CharField(max_length=50 , verbose_name="موديل السيارة")
    brand = models.CharField(max_length=50 , verbose_name="ماركة السيارة")

    car_driver_number = models.CharField(
        max_length=15,
        verbose_name="رقم سائق السياره",
        blank=True,
        null=True,
        validators=[
            RegexValidator(r'^\+20\d{10}$', message="رقم الهاتف يجب أن يبدأ بـ +20 ويحتوي على 12 رقم بالضبط.")
        ]
    )
    transmission = models.CharField(
        max_length=10,
        choices=[('Automatic', 'Automatic'), ('Manual', 'Manual')],
        default='Automatic' , verbose_name="نوع ناقل الحركة"
    )
    seats = models.IntegerField(verbose_name="عدد المقاعد")
    price_per_km_0_100 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 0 إلى 100")
    price_per_km_101_200 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 101 إلى 200")
    price_per_km_201_300 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 201 إلى 300")
    price_per_km_301_400 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 301 إلى 400")
    price_per_km_401_500 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 401 إلى 500")
    price_per_km_501_600 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 501 إلى 600")
    price_per_km_601_700 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 601 إلى 700")
    price_per_km_701_800 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 701 إلى 800")
    price_per_km_801_900 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 801 إلى 900")
    price_per_km_901_1000 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم من 901 إلى 1000")
    price_per_km_above_1000 = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="السعر لكل كم أكثر من 1000")

    DAY_USE = models.DecimalField(max_digits=10, decimal_places=2, default=0.00 , verbose_name="سعر الاستخدام اليومي")
    day_use_12_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00 , verbose_name="سعر الاستخدام اليومي - 12 ساعة")
    day_use_10_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00 , verbose_name="سعر الاستخدام اليومي - 10 ساعات")
    day_use_8_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00 , verbose_name="سعر الاستخدام اليومي - 8 ساعات")
    airport_pickup_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00 , verbose_name="سعر الاستقبال من المطار")

    image = models.ImageField(upload_to='car_images/', blank=True, null=True , verbose_name="صورة السيارة الخارجيه")
    additional_images = models.ManyToManyField('CarImage', blank=True, related_name='car_images', verbose_name="صور  باقي السيارات")
    description = models.TextField(blank=True, null=True , verbose_name="وصف السيارة")
    is_available = models.BooleanField(default=True    , verbose_name="متاحة للحجز")
    panorama_image = models.ImageField(upload_to='panorama_images/', blank=True, null=True , verbose_name="صورة 360 للسيارة")
    class Meta:
        verbose_name = 'اداره سيارات الايجار الكامله'              
        verbose_name_plural = ' اداره سيارات الايجار الكامله'

    def __str__(self):
        return f"{self.brand} {self.name} ({self.model})"

# 📸 **Model: CarImage**
class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='car_images')
    image = models.ImageField(upload_to='car_images/')

    def __str__(self):
        return f"Image for {self.car.name}"
class GeoBooking(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
# 📅 **Model: CarBooking**
class CarBooking(models.Model):
    TRIP_TYPE_CHOICES = [
        ('one_way_go', 'ذهاب فقط'),
        ('one_way_return', 'عودة فقط'),
        ('round_trip', 'ذهاب وعودة'),
        ('day_use', 'ذهاب وعوده في نفس اليوم'),
        ('day_use_12', 'استخدام يومي - 12 ساعة'),
        ('day_use_10', 'استخدام يومي - 10 ساعات'),
        ('day_use_8', 'استخدام يومي - 8 ساعات'),
        ('airport_pickup', 'استقبال من المطار'),
    ]
    go_time = models.TimeField(blank=True, null=True)   
    back_time = models.TimeField(blank=True, null=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_PERCENTAGE_CHOICES = [
        (100, 'دفع كامل (100%)'),
        (50, 'دفع جزئي (50%)'),
    ]
    from_location = models.CharField(max_length=255, null=True, blank=True, verbose_name='نقطة البداية')
    to_location = models.CharField(max_length=255, null=True, blank=True, verbose_name='نقطة النهاية')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    merchant_order_id = models.CharField(max_length=50, unique=True, null=True, blank=True)

    car = models.ForeignKey(Car, on_delete=models.CASCADE ,null=True, blank=True)   
    customer_name = models.CharField(max_length=100,null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    trip_type = models.CharField(max_length=20, choices=TRIP_TYPE_CHOICES , default='round_trip',null=True, blank=True)
    go_date = models.DateField(null=True, blank=True)
    return_date = models.DateField(null=True, blank=True)
    payment_percentage = models.IntegerField(choices=PAYMENT_PERCENTAGE_CHOICES, default=100,null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True,null=True, blank=True)
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True , verbose_name="السعر الإجمالي")
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'حجز سيارة'
        verbose_name_plural = 'حجوزات ايجار السيارات الكامله'

    def clean(self):
        # التحقق من صحة التواريخ حسب نوع الرحلة
        if self.trip_type in ['round_trip', 'one_way_go', 'one_way_return'] and not self.go_date:
            raise ValidationError("تاريخ الذهاب مطلوب لهذا النوع من الرحلات")
        
        if self.trip_type == 'round_trip' and not self.return_date:
            raise ValidationError("تاريخ العودة مطلوب لرحلة الذهاب والعودة")
        
        if self.go_date and self.return_date and self.go_date >= self.return_date:
            raise ValidationError("تاريخ العودة يجب أن يكون بعد تاريخ الذهاب")

        # التحقق من توفر السيارة
        if self.pk:  # فقط للتحقق عند التعديل
            overlapping_bookings = CarBooking.objects.filter(
                car=self.car,
                status__in=['pending', 'confirmed'],
                go_date__lt=self.return_date if self.return_date else self.go_date,
                return_date__gt=self.go_date if self.go_date else self.return_date
            ).exclude(id=self.id)
            
            if overlapping_bookings.exists():
                raise ValidationError("السيارة محجوزة في هذه الفترة")

    def save(self, *args, **kwargs):
        self.full_clean()  # تطبيق جميع قواعد التحقق
        super().save(*args, **kwargs)

    def calculate_total_price(self):
        """
        حساب السعر الإجمالي بناءً على نوع الرحلة والمسافة
        """
        if self.trip_type in ['day_use_12', 'day_use_10', 'day_use_8', 'airport_pickup']:
            # الأسعار الثابتة
            price_map = {
                'day_use_12': self.car.day_use_12_price,
                'day_use_10': self.car.day_use_10_price,
                'day_use_8': self.car.day_use_8_price,
                'airport_pickup': self.car.airport_pickup_price,
            }
            self.total_price = price_map[self.trip_type]
        else:
            # الرحلات حسب المسافة
            if not self.distance_km:
                raise ValueError("المسافة مطلوبة لحساب سعر الرحلة")
            
            if self.distance_km <= 300:
                price_per_km = self.car.price_per_km_below_300
            else:
                price_per_km = self.car.price_per_km_above_300
            
            base_price = self.distance_km * price_per_km
            
            if self.trip_type == 'round_trip':
                base_price *= 2
            
            self.total_price = base_price
        
        # حساب المبلغ المدفوع
        self.paid_amount = (self.total_price * self.payment_percentage) / 100

    def __str__(self):
        return f"{self.customer_name} - {self.car.name} ({self.get_trip_type_display()})"


class FormBooking(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    selected_form_route = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} - {self.phone}"


class SpeedData(models.Model):
    sensor_id = models.CharField(max_length=50)
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor_id} - {self.value} km/h at {self.timestamp}"

from django.db import models

class SensorData(models.Model):
    sensor_type = models.CharField(max_length=100)
    value = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor_type}: {self.value} at {self.timestamp}"
# models.py - النماذج المحدثة

from django.db import models
from django.conf import settings
import datetime


class City(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم المدينة")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="الجامعة", null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name="نشط في الفرونت إند")
    
    class Meta:
        verbose_name = 'إدارة مدن الركوب في الفورم'              
        verbose_name_plural = 'إدارة مدن الركوب في الفورم'

    def __str__(self):
        return self.name

class PickupLocation(models.Model):
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='pickup_locations',
        verbose_name="المدينة", 
        null=True, 
    )
    name = models.TextField(verbose_name="أماكن الركوب (كل مكان في سطر)")
    is_active = models.BooleanField(default=True, verbose_name="نشط في الفرونت إند")
    
    class Meta:
        verbose_name = 'نقاط الركوب في الفورم'              
        verbose_name_plural = 'إدارة نقاط الركوب في الفورم'

    def __str__(self):
        if self.city:
            return f"{self.city.name} - نقاط الركوب"
        else:
            return "نقاط الركوب"

class DropoffLocation(models.Model):
    TRIP_TYPE_CHOICES = [
        ('ذهاب', 'نقاط نزول الذهاب'),
        ('عودة', 'نقاط ركوب العودة'),
    ]

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='dropoff_locations',
        verbose_name="الجامعة",
        null=True, blank=True
    )
    name = models.TextField(verbose_name="أماكن النزول (كل مكان في سطر)")
    is_active = models.BooleanField(default=True, verbose_name="نشط في الفرونت إند")
    trip_type = models.CharField(
        max_length=10,
        choices=TRIP_TYPE_CHOICES,
        verbose_name="نوع الرحلة"
    )

    class Meta:
        verbose_name = 'نقطة نزول في الفورم'              
        verbose_name_plural = 'إدارة نقاط النزول في الفورم'

    def __str__(self):
        category_name = self.category.name if self.category else "بدون جامعة"
        return f"{category_name} - نقاط نزول {self.trip_type}"


class Round(models.Model):
    TRIP_TYPE_CHOICES = [
        ('ذهاب', 'ذهاب'),
        ('عودة', 'عودة'),
        ('ذهاب وعودة', 'ذهاب وعودة'),
    ]
    
    category = models.ForeignKey('Category', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    trip_type = models.CharField(max_length=50, choices=TRIP_TYPE_CHOICES, null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    back_time = models.TimeField(null=True, blank=True)
    cities = models.ManyToManyField('City', null=True, blank=True)


class FormReservation(models.Model):
    # الحقول الأساسية الموجودة
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    university_code = models.CharField(max_length=20, blank=True, null=True)
    category = models.ForeignKey(
        "Category",
        on_delete=models.CASCADE,
        verbose_name="الجامعة"
    )
    merchant_order_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="رقم الطلب في الدفع"
    )
    transaction_number = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        unique=True,
        verbose_name="رقم المعاملة (يدوي)",
        help_text="يستخدم لتسجيل رقم التحويل أو الدفع النقدي اليدوي",
        error_messages={'unique': 'رقم المعاملة هذا مستخدم بالفعل في حجز آخر.'}
    )

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'قيد الانتظار'),
            ('confirmed', 'تم التأكيد'),
            ('failed', 'فشل الدفع'),
            ('cash', 'نقداً'),
            ('subscription', 'اشتراك'),
            ('attended', 'حضر'),
        ],
        default='pending',
        verbose_name="حالة الدفع"
    )

    ATTENDANCE_CHOICES = [
        ('present', 'حضر'),
        ('absent', 'غائب'),
    ]
    attendance_status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_CHOICES,
        default='absent',
        verbose_name='حالة الحضور',
    )
    
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="السعر الكلي"
    )

    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="المبلغ المدفوع"
    )

    seat = models.ForeignKey(
        'Seat',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        verbose_name="رقم الكرسي"
    )
    
    passenger = models.ForeignKey(
        'passenger',
        on_delete=models.CASCADE,
        verbose_name="الراكب",
        related_name='form_reservations',
        null=True,
        blank=True
    )
    
    round = models.ForeignKey('Round', on_delete=models.SET_NULL, null=True, blank=True)
    
    # الحقل القديم للمدينة (سيبقى للتوافق مع البيانات القديمة)
    city = models.ForeignKey('City', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="المدينة (قديم)")
    
    student_name = models.CharField(
        max_length=255, 
        verbose_name="اسم الطالب",
        blank=True
    )
    seat_number = models.CharField(max_length=10, null=True, blank=True, verbose_name="رقم المقعد")

    arrival_time = models.TimeField(
        verbose_name="وقت الذهاب",
        null=True, blank=True  
    )
    back_time = models.TimeField(verbose_name="وقت العودة", null=True, blank=True)

    trip_date = models.DateField(verbose_name="تاريخ الرحلة")
    
    trip_type = models.CharField(
        max_length=15,
        choices=[
            ('ذهاب', 'ذهاب'),
            ('عودة', 'عودة'),
            ('ذهاب وعودة', 'ذهاب وعودة'),
        ],
        verbose_name="نوع الرحلة"
    )
    
    trip = models.ForeignKey(
        'Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الرحلة"
    )

    # ========== الحقول الجديدة لمدن الذهاب والعودة ==========
    
    # حقول الذهاب
    going_city = models.ForeignKey(
        'City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='going_reservations',
        verbose_name="مدينة الذهاب"
    )
    going_pickup_location = models.CharField(
        max_length=255,
        verbose_name="نقطة ركوب الذهاب",
        null=True, blank=True
    )
    going_dropoff_location = models.CharField(
        max_length=255,
        verbose_name="نقطة نزول الذهاب",
        null=True, blank=True
    )
    
    # حقول العودة
    return_city = models.ForeignKey(
        'City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='return_reservations',
        verbose_name="مدينة العودة"
    )
    return_pickup_location = models.CharField(
        max_length=255,
        verbose_name="نقطة ركوب العودة",
        null=True, blank=True
    )
    return_dropoff_location = models.CharField(
        max_length=255,
        verbose_name="نقطة نزول العودة",
        null=True, blank=True
    )
    
    # ========== نهاية الحقول الجديدة ==========

    # الحقول القديمة (ستبقى للتوافق مع البيانات القديمة)
    pickup_location = models.CharField(
        max_length=255,
        verbose_name="نقطة الركوب (قديم)",
        null=True, blank=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="المستخدم",
        related_name='reservations',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    
    class Meta:
        verbose_name = 'إدارة حجوزات الفورم'
        verbose_name_plural = 'إدارة حجوزات الفورم'

    def save(self, *args, **kwargs):
        """تعبئة الحقول تلقائياً قبل الحفظ"""
        # إذا المستخدم موجود ومعاه passenger ومفيش passenger محدد في الحجز
        if self.user and not self.passenger and hasattr(self.user, 'passenger'):
            self.passenger = self.user.passenger

        # إذا الاسم مش متحدد
        if not self.student_name:
            if self.passenger:
                self.student_name = self.passenger.name
            elif self.user:
                self.student_name = self.user.get_full_name() or self.user.username

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student_name} - {self.trip_type} - {self.trip_date}"


from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class BonusPoint(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=6, decimal_places=2)  # القيمة النقدية
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    class Meta:
        verbose_name = 'اداره نقاط المكافأه'
        verbose_name_plural = ' اداره نقاط المكافأه'

    def is_valid(self):
        return not self.used and (timezone.now() - self.created_at).days < 7
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class DiscountCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    value = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and timezone.now() <= self.created_at + timedelta(days=10)

    def __str__(self):
        return f"{self.code} - {self.user.username}"
from django.db import models

class Esp32Data(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    accX = models.FloatField()
    accY = models.FloatField()
    accZ = models.FloatField()
    gyroX = models.FloatField()
    gyroY = models.FloatField()
    gyroZ = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} - Lat: {self.latitude}, Lng: {self.longitude}"
# Anaconda_bus_APP/models.py

from django.db import models
# ... (باقي المودلز الموجودة)

# Anaconda_bus_APP/models.py
from django.db import models
from django.utils import timezone
from datetime import timedelta

class BusLocation(models.Model):
    bus = models.OneToOneField(Bus, on_delete=models.CASCADE, primary_key=True, related_name='live_location')
    latitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    longitude = models.DecimalField(max_digits=12, decimal_places=9, null=True, blank=True)
    last_updated = models.DateTimeField(null=True, blank=True)
    
    # --- الحقول الجديدة ---
    is_active = models.BooleanField(default=False) # هل المشاركة نشطة حاليًا؟
    expires_at = models.DateTimeField(null=True, blank=True) # متى تنتهي صلاحية هذه الجلسة؟

    def __str__(self):
        return f"Location for {self.bus.name} (Active: {self.is_active})"

    # دالة مساعدة للتحقق من الصلاحية
    def is_session_valid(self):
        if not self.is_active or not self.expires_at:
            return False
        return timezone.now() < self.expires_at
# في ملف models.py، أضف هذا النموذج الجديد

class LocationLink(models.Model):
    """
    نموذج مخصص لتخزين روابط خرائط جوجل لنقاط الركوب والنزول.
    يربط اسم النقطة (كنص) برابط الخريطة الخاص بها.
    """
    point_name = models.CharField(
        max_length=255,
        unique=True,  # نضمن عدم تكرار اسم النقطة
        verbose_name="اسم نقطة الركوب/النزول"
    )
    google_maps_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="رابط خرائط جوجل"
    )

    class Meta:
        verbose_name = 'رابط موقع جغرافي'
        verbose_name_plural = 'إدارة روابط المواقع الجغرافية'

    def __str__(self):
        return self.point_name
from django.db import models

class Advertisement(models.Model):
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name="عنوان الإعلان")
    image = models.ImageField(upload_to="ads/", verbose_name="صورة الإعلان")
    link = models.URLField(blank=True, null=True, verbose_name="رابط الإعلان")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "إعلان"
        verbose_name_plural = "الإعلانات"

    def __str__(self):
        return self.title if self.title else f"إعلان {self.id}"
import random
from datetime import datetime, timedelta

class WhatsAppOTP(models.Model):
    passenger = models.ForeignKey('passenger', on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def is_valid(self):
        return datetime.now() - self.created_at.replace(tzinfo=None) < timedelta(minutes=5)

    @staticmethod
    def generate_otp():
        return str(random.randint(100000, 999999))


# Weekly Booking Models
class WeeklySchedule(models.Model):
    """الجداول الزمنية الأسبوعية التي يحددها الأدمن"""
    DAYS_OF_WEEK = [
        ('saturday', 'السبت'),
        ('sunday', 'الأحد'),
        ('monday', 'الإثنين'),
        ('tuesday', 'الثلاثاء'),
        ('wednesday', 'الأربعاء'),
        ('thursday', 'الخميس'),
        ('friday', 'الجمعة'),
    ]
    
    TRIP_TYPES = [
        ('departure', 'ذهاب'),
        ('return', 'عودة'),
    ]
    
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="الجامعة")
    day_of_week = models.CharField(max_length=10, choices=DAYS_OF_WEEK, verbose_name="اليوم")
    trip_type = models.CharField(max_length=10, choices=TRIP_TYPES, verbose_name="نوع الرحلة")
    time = models.TimeField(verbose_name="الوقت")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    
    class Meta:
        unique_together = ['category', 'day_of_week', 'trip_type', 'time']
        verbose_name = 'جدول أسبوعي'
        verbose_name_plural = 'الجداول الأسبوعية'
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} - {self.get_trip_type_display()} - {self.time}"


class WeeklyBooking(models.Model):
    """حجوزات المستخدمين الأسبوعية"""
    DAYS_OF_WEEK = [
        ('saturday', 'السبت'),
        ('sunday', 'الأحد'),
        ('monday', 'الإثنين'),
        ('tuesday', 'الثلاثاء'),
        ('wednesday', 'الأربعاء'),
        ('thursday', 'الخميس'),
        ('friday', 'الجمعة'),
    ]
    
    passenger = models.ForeignKey(passenger, on_delete=models.CASCADE, verbose_name="الطالب")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="الجامعة")
    
    # أيام الذهاب
    departure_days = models.JSONField(default=list, verbose_name="أيام الذهاب", help_text="قائمة بأيام الذهاب المختارة")
    departure_time = models.TimeField(null=True, blank=True, verbose_name="وقت الذهاب المفضل")
    
    # أيام العودة
    return_days = models.JSONField(default=list, verbose_name="أيام العودة", help_text="قائمة بأيام العودة المختارة")
    return_time = models.TimeField(null=True, blank=True, verbose_name="وقت العودة المفضل")
    
    # نقاط الالتقاط والنزول
    pickup_location = models.CharField(max_length=255, null=True, blank=True, verbose_name="نقطة الالتقاط")
    dropoff_location = models.CharField(max_length=255, null=True, blank=True, verbose_name="نقطة النزول")
    
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    
    class Meta:
        unique_together = ['passenger', 'category']
        verbose_name = 'حجز أسبوعي'
        verbose_name_plural = 'الحجوزات الأسبوعية'
    
    def __str__(self):
        return f"{self.passenger.name} - {self.category.name}"
    
    def get_departure_days_display(self):
        """عرض أيام الذهاب كنص"""
        days_dict = dict(self.DAYS_OF_WEEK)
        return ', '.join([days_dict[day] for day in self.departure_days])
    
    def get_return_days_display(self):
        """عرض أيام العودة كنص"""
        days_dict = dict(self.DAYS_OF_WEEK)
        return ', '.join([days_dict[day] for day in self.return_days])
