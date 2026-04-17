from django.contrib import admin
from django.utils.safestring import mark_safe
from .views import send_whatsapp_confirmation  # Import the function from the views module
from .models import Category, passenger, WeeklySchedule, WeeklyBooking
from django.utils.translation import gettext_lazy as _
from io import BytesIO
import qrcode
import base64
from django.utils.translation import gettext_lazy as _

import requests

from django.contrib import admin
from django.utils.safestring import mark_safe
import qrcode
from io import BytesIO
import base64
from PIL import Image, ImageDraw, ImageFont

from django.utils.timezone import now
from datetime import timedelta
from django.contrib import messages

@admin.action(description="إرسال رسالة واتساب لتذكير الركاب بحجز الرحلات")
def send_weekly_booking_whatsapp(modeladmin, request, queryset):
    message_template = "🚍 مرحبًا {name} ، تم فتح الحجز لرحلتك  يوم {day} \n🔗 رابط الحجز: {booking_url}  \n   *ان طلب منك النظام تسجيل الدخول اكتب الكود الجامعي في كلا من اسم المستخدم و كلمه المرور ان قمت بالتسجيل علي الموقع مسبقا* \nAlen_AI-moodel"
    
    INSTANCE_ID = "instance105329"
    API_TOKEN = settings.ULTRAMSG_API_TOKEN
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    today = now().date()
    last_week_date = today - timedelta(days=7)

    messages_sent = 0

    for passenger in queryset:
        last_booking = Booking.objects.filter(
            passenger=passenger,
            booking_date__date=last_week_date
        ).first()

        if last_booking:
            trip = last_booking.Trip
            if trip.available_seats > 0:
                booking_url = f"https://allen.allentravels.com//book-trip/{trip.id}/"
            else:
                booking_url = "https://allen.allentravels.com//allen/login/"
        else:
            booking_url = "https://bus.esolvelabs.com:4433/allen/login/"

        if passenger.phone_number:
            message = message_template.format(
                name=passenger.name,
                day=last_week_date.strftime("%A"),
                booking_url=booking_url
            )
            
            payload = {
                "token": API_TOKEN,
                "to": passenger.phone_number,
                "body": message
            }
            requests.post(URL, data=payload)
            messages_sent += 1

    modeladmin.message_user(request, f"✅ تم إرسال الرسائل إلى {messages_sent} راكب.", messages.SUCCESS)

class AdminSettingsAdmin(admin.ModelAdmin):
    list_display = ['custom_whatsapp_message']

@admin.action(description="إرسال رسالة واتساب")
def send_whatsapp_notification(modeladmin, request, queryset):
    message = "يرجى الدخول الآن وحجز رحلتكم لضمان مقعدكم.\n🔗 https://yourwebsite.com/book-ride"
    
    # استدعاء الدالة بشكل صحيح عبر الكلاس وليس ككائن
    result = passenger.send_whatsapp_message(message, list(queryset))
    
    modeladmin.message_user(request, result, messages.SUCCESS)
from django import forms
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.utils.safestring import mark_safe
import qrcode
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

class WhatsAppMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea, label="اكتب الرسالة هنا")

from django import forms
from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.utils.safestring import mark_safe
import requests

# بيانات API
INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
API_URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

class WhatsAppMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 3, "cols": 50}), label="اكتب الرسالة لإرسالها:")
    passenger_ids = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="اختر الركاب الذين تريد إرسال الرسالة لهم"
    )

from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.utils.safestring import mark_safe
import requests
from .models import passenger
from .forms import WhatsAppMessageForm
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.core.cache import cache
import uuid
import requests
from .models import passenger
from .forms import WhatsAppMessageForm

# ضع هنا بيانات الـ API
API_URL = "https://example.com/api/sendMessage"  # ✅ غيّرها إلى رابط واجهة واتساب الخاصة بك
API_TOKEN = settings.ULTRAMSG_API_TOKEN  # ✅ غيّرها إلى التوكن الصحيح
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path
from .models import passenger
from .forms import WhatsAppMessageForm
import requests
import uuid

# إعدادات API
INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
API_URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
import uuid
import requests
from django.conf import settings
from django.core.cache import cache
from django.urls import path
from django.shortcuts import redirect, render
from django.contrib import admin, messages
from .models import passenger
from .forms import WhatsAppMessageForm

INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
API_URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"


class PassengerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_type', 'name', 'category', 'last_selected_route',
        'subscription_start_date', 'subscription_end_date',
        'phone_number', 'university_code',
        'total_rides', 'remaining_rides', 'subscription_duration'
    )
    search_fields = ('name', 'university_code',)
    list_filter = (
        'category', 'user_type', 'subscription_start_date',
        'subscription_end_date', 'subscription_duration'
    )
    readonly_fields = ('subscription_start_date', 'subscription_end_date')

    actions = ['send_whatsapp_selected', 'reset_all_subscription']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('alenmasr/', self.admin_site.admin_view(self.alenmasr_view), name="alenmasr"),
        ]
        return custom_urls + urls
    def reset_all_subscription(self, request, queryset):
        count = 0

        for p in queryset:
            p.subscription_duration = 0   # Total rides + مدة الاشتراك
            p.rides_used = 0              # الرحلات المستخدمة

            # علشان remaining_rides يبقى 0 فعلًا
            # ولمنع إعادة توليد تواريخ اشتراك جديدة
            p.subscription_start_date = None
            p.subscription_end_date = None

            p.save(update_fields=[
                "subscription_duration",
                "rides_used",
                "subscription_start_date",
                "subscription_end_date",
            ])
            count += 1

        self.message_user(
            request,
            f"🧹 تم تصفير (إجمالي الرحلات + المتبقي + مدة الاشتراك) لـ {count} راكب.",
            level=messages.SUCCESS
        )

    reset_all_subscription.short_description = "🚫 تصفير الاشتراك بالكامل (Total + Remaining + المدة)"


    # ✅ نحفظ الـ IDs مؤقتًا بدل من تمريرها في URL
    def send_whatsapp_selected(self, request, queryset):
        selected_ids = [p.id for p in queryset]
        cache_key = f"selected_passengers_{uuid.uuid4()}"
        cache.set(cache_key, selected_ids, timeout=600)  # تخزين لمدة 10 دقائق
        return redirect(f"alenmasr/?cache_key={cache_key}")

    send_whatsapp_selected.short_description = "📩 إرسال رسالة واتساب للطلاب المحددين"

    def alenmasr_view(self, request):
        cache_key = request.GET.get("cache_key")
        selected_ids = cache.get(cache_key, [])

        selected_passengers = passenger.objects.filter(id__in=selected_ids) if selected_ids else []
        choices = [(str(p.id), f"{p.name} - {p.phone_number}") for p in selected_passengers]
        selected_values = [str(p.id) for p in selected_passengers]

        if request.method == "POST":
            form = WhatsAppMessageForm(request.POST, request.FILES)
            form.fields['passenger_ids'].choices = choices

            if form.is_valid():
                selected_passenger_ids = form.cleaned_data.get('passenger_ids', [])
                custom_message = form.cleaned_data['message']
                image = request.FILES.get('image')
                document = request.FILES.get('document')

                if not selected_passenger_ids:
                    self.message_user(request, "⚠️ لم يتم تحديد أي ركاب!", level=messages.WARNING)
                    return redirect("..")

                selected_passengers = passenger.objects.filter(id__in=selected_passenger_ids)
                success_count, fail_count = 0, 0

                for p in selected_passengers:
                    sent = self.send_whatsapp_message(
                        phone_number=p.phone_number,
                        message=custom_message,
                        image=image,
                        document=document
                    )
                    if sent:
                        success_count += 1
                    else:
                        fail_count += 1

                msg = f"✅ تم إرسال الرسالة إلى {success_count} راكب بنجاح."
                if fail_count > 0:
                    msg += f" ❌ فشل الإرسال إلى {fail_count}."
                self.message_user(request, msg, level=messages.SUCCESS if fail_count == 0 else messages.WARNING)
                return redirect("..")

        else:
            form = WhatsAppMessageForm(initial={'passenger_ids': selected_values})
            form.fields['passenger_ids'].choices = choices

        return render(request, "admin/alenmasr.html", {
            "form": form,
            "selected_passengers": selected_passengers
        })

    def send_whatsapp_message(self, phone_number, message, image=None, document=None):
        """إرسال رسالة واتساب عبر UltraMsg"""
        if not phone_number:
            return False

        phone_number = phone_number.strip()
        if not phone_number.startswith("+20"):
            phone_number = "+20" + phone_number.lstrip("0")

        try:
            # إرسال الرسالة النصية
            payload = {
                "token": API_TOKEN,
                "to": phone_number,
                "body": message,
            }
            response = requests.post(API_URL, data=payload, timeout=15)
            print(f"[DEBUG] Text to {phone_number}: {response.status_code} - {response.text}")

            if response.status_code != 200:
                return False

            # إرسال الصورة إن وجدت
            if image:
                image_url = f"{settings.DOMAIN}{settings.MEDIA_URL}{image.name}"
                img_url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/image"
                img_payload = {
                    "token": API_TOKEN,
                    "to": phone_number,
                    "image": image_url,
                    "caption": message or "",
                }
                img_response = requests.post(img_url, data=img_payload, timeout=15)
                print(f"[DEBUG] Image to {phone_number}: {img_response.status_code} - {img_response.text}")

            # إرسال الملف إن وجد
            if document:
                document_url = f"{settings.DOMAIN}{settings.MEDIA_URL}{document.name}"
                doc_url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/document"
                doc_payload = {
                    "token": API_TOKEN,
                    "to": phone_number,
                    "document": document_url,
                    "caption": message or "",
                }
                doc_response = requests.post(doc_url, data=doc_payload, timeout=15)
                print(f"[DEBUG] Document to {phone_number}: {doc_response.status_code} - {doc_response.text}")

            return True
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send message to {phone_number}: {e}")
            return False
from django.contrib import admin, messages
from django.utils import timezone
from .models import Category, Trip, Booking
import requests

from django.contrib import admin, messages
from django.utils import timezone
import requests
from .models import Trip, Booking

from django.utils import timezone
from django.contrib import messages
import requests
import requests
from django.utils import timezone
from django.contrib import admin, messages
from .models import Trip, Booking
import requests
from django.contrib import admin, messages
from django.utils import timezone
from .models import Trip, Booking, Report
import requests
from django.contrib import admin, messages
from django.utils import timezone
from .models import Trip, Booking, Report
INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

def send_whatsapp_message(phone_number, message):
    max_length = 4096  # الحد الأقصى لحجم الرسالة
    messages_parts = [message[i:i+max_length] for i in range(0, len(message), max_length)]
    
    for part in messages_parts:
        payload = {"token": API_TOKEN, "to": phone_number, "body": part}
        response = requests.post(URL, data=payload)
        if response.status_code != 200:
            return response.json().get("error", "لم يتم تحديد الخطأ")
    return None

def send_trip_report(modeladmin, request, queryset, target_date, report_title):
    if queryset.count() != 1:
        modeladmin.message_user(request, "يرجى اختيار جامعة واحدة فقط.", level=messages.ERROR)
        return

    category = queryset.first()
    if not category.admin_phone_number:
        modeladmin.message_user(request, f"لا يوجد رقم هاتف مسجل لإرسال التقرير إلى {category.name}.", level=messages.WARNING)
        return

    trips = Trip.objects.filter(is_active=True, bus__category=category, date=target_date)
    report_data, reports = [], []
    
    for trip in trips:
        bus = trip.bus
        total_capacity = bus.capacity or 0
        total_reservations = Booking.objects.filter(Trip=trip).count()
        remaining_seats = total_capacity - total_reservations
        occupancy_rate = (total_reservations / total_capacity * 100) if total_capacity > 0 else 0
        
        bus_status = "ضعيف" if occupancy_rate < 50 else "متوسط" if occupancy_rate <= 75 else "جيد"
        
        route_stations = [station.strip() for station in trip.route.split("\n") if station.strip()]
        station_reservations = [
            f"{station}: {Booking.objects.filter(Trip=trip, selected_route__iexact=station).count()} حجز"
            for station in route_stations
        ]
        
        report_text = (
            f"رحلة: {trip.trip_name}\n"
            f"المسار:\n" + "\n".join(route_stations) + "\n"
            f"التاريخ: {trip.date} - {trip.start_time}\n"
            f"الباص: {bus.name}\n"
            f"السعة: {total_capacity}، الحجوزات: {total_reservations}، المتبقي: {remaining_seats}\n"
            f"الإشغال: {round(occupancy_rate, 2)}%، حالة الباص: {bus_status}\n"
            f"تفاصيل الحجز في المحطات:\n" + "\n".join(station_reservations) + "\n"
        )
        
        report_data.append(report_text)
        reports.append(Report(category=category, trip=trip, report_text=report_text))

    Report.objects.bulk_create(reports)
    
    report_message = f"{report_title} ({target_date})\n\n"
    report_message += "=== الرحلات الحالية ===\n"
    report_message += "\n---------------------\n".join(report_data) if report_data else "لا توجد رحلات حالية.\n"
    
    error = send_whatsapp_message(category.admin_phone_number, report_message)
    if error:
        modeladmin.message_user(request, f"حدث خطأ أثناء إرسال التقرير: {error}", level=messages.ERROR)
    else:
        modeladmin.message_user(request, f"تم إرسال التقرير إلى {category.name} بنجاح.", level=messages.SUCCESS)

@admin.action(description="إرسال تقرير رحلات اليوم عبر واتساب")
def send_today_trip_report(modeladmin, request, queryset):
    send_trip_report(modeladmin, request, queryset, timezone.now().date(), "تقرير رحلات اليوم")

@admin.action(description="إرسال تقرير رحلات الغد عبر واتساب")
def send_tomorrow_trip_report(modeladmin, request, queryset):
    send_trip_report(modeladmin, request, queryset, timezone.now().date() + timezone.timedelta(days=1), "تقرير رحلات الغد")

@admin.action(description="إرسال تقرير رحلات بعد الغد عبر واتساب")
def send_day_after_tomorrow_trip_report(modeladmin, request, queryset):
    send_trip_report(modeladmin, request, queryset, timezone.now().date() + timezone.timedelta(days=2), "تقرير رحلات بعد الغد")

@admin.action(description="إرسال تقرير رحلات 7 أيام قادمة عبر واتساب")
def send_next_seven_days_trip_report(modeladmin, request, queryset):
    if queryset.count() != 1:
        modeladmin.message_user(request, "يرجى اختيار جامعة واحدة فقط.", level=messages.ERROR)
        return

    category = queryset.first()
    if not category.admin_phone_number:
        modeladmin.message_user(request, f"لا يوجد رقم هاتف مسجل لإرسال التقرير إلى {category.name}.", level=messages.WARNING)
        return

    start_date, end_date = timezone.now().date(), timezone.now().date() + timezone.timedelta(days=7)
    trips = Trip.objects.filter(is_active=True, bus__category=category, date__range=(start_date, end_date))
    
    report_data = [
        f"رحلة: {trip.trip_name}\nالمسار: {trip.route}\nالتاريخ: {trip.date} - {trip.start_time}\nالباص: {trip.bus.name}\n"
        for trip in trips
    ]
    
    report_message = f"تقرير رحلات {category.name} للأيام السبعة القادمة\n\n"
    report_message += "=== الرحلات ===\n"
    report_message += "\n---------------------\n".join(report_data) if report_data else "لا توجد رحلات.\n"
    
    error = send_whatsapp_message(category.admin_phone_number, report_message)
    if error:
        modeladmin.message_user(request, f"حدث خطأ أثناء إرسال التقرير: {error}", level=messages.ERROR)
    else:
        modeladmin.message_user(request, f"تم إرسال تقرير 7 أيام القادمة إلى {category.name} بنجاح.", level=messages.SUCCESS)

def get_route_booking_details(route_text, trip):
    """
    تقسيم خط السير (route) إلى محطات فردية وحساب عدد الحجوزات لكل محطة
    """
    route_stations = route_text.split("\n")  # تقسيم المسار إلى خطوط
    station_data = []
    
    for station in route_stations:
        station_reservations = Booking.objects.filter(Trip=trip, selected_route=station).count()
        station_data.append(f"{station}: {station_reservations} حجز")
    
    return "\n".join(station_data) if station_data else "لا توجد حجوزات في المحطات."

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id','name','admin_name'  ,'admin_phone_number' ]
    search_fields = ['name']
    actions = [send_today_trip_report , send_tomorrow_trip_report , send_day_after_tomorrow_trip_report ]



from django.utils.html import mark_safe
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Attendance, passenger


from .models import passenger
from django.utils.safestring import mark_safe
from django.contrib import admin
from django.utils import timezone
from datetime import date, timedelta

from django.contrib import admin
from .models import Bus, Trip, Booking

from django.contrib import admin
from .models import Bus, Category


from django.contrib import admin
from .models import Trip,destination

@admin.register(destination)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
@admin.action(description=_("تجديد الرحلات المختارة لمدة يوم / أسبوع / شهر"))
def renew_selected_trips(modeladmin, request, queryset):
    """
    تجديد الرحلات بناءً على الخيار الذي يختاره المستخدم.
    """
    # اطلب من المستخدم إدخال نوع التجديد
    period = request.POST.get('period', 'day')  # القيمة الافتراضية يوم
    days = 0
    weeks = 0
    months = 0

    if period == 'day':
        days = 1
    elif period == 'week':
        weeks = 1
    elif period == 'month':
        months = 1

    for trip in queryset:
        try:
            trip.renew_trip(days=days, weeks=weeks, months=months)
        except ValueError as e:
            modeladmin.message_user(request, f"فشل تجديد الرحلة {trip.id}: {e}")

    modeladmin.message_user(request, _("تم تجديد الرحلات بنجاح."))
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib import messages

# دالة تجديد الرحلات
# def renew_selected_trips(modeladmin, request, queryset):
#     # تحديث حالة جميع المقاعد في الرحلات المختارة إلى غير محجوزة
#     for trip in queryset:
#         seats = Seat.objects.filter(bus=trip.bus)  # الحصول على المقاعد المرتبطة بالرحلة
#         seats.update(is_reserved=False)  # إعادة المقاعد إلى حالة غير محجوزة
#         messages.success(request, f"تم تجديد الرحلة '{trip.trip_name}' وإعادة جميع المقاعد إلى الحالة الأصلية.")
from django.utils.timezone import now, timedelta
from django.utils.timezone import now, timedelta

from datetime import timedelta

# def renew_selected_trips(modeladmin, request, queryset):
#     """
#     إجراء لتجديد الرحلات المحددة عن طريق إضافة يوم إلى تاريخ الرحلة وجعل حجوزاتها غير نشطة.
#     """
#     for trip in queryset:
#         # تحديث حالة الحجوزات المرتبطة إلى "غير نشطة"
#         trip.bookings.filter(status="active").update(status="inactive")
        
#         # إضافة يوم واحد إلى تاريخ الرحلة الحالي
#         trip.date += timedelta(days=1)
        
#         # إعادة تنشيط الرحلة
#         trip.is_active = True  
#         trip.save()
        
#         # تحديث حالة المقاعد المرتبطة بالرحلة
#         seats = Seat.objects.filter(bus=trip.bus)
#         seats.update(is_reserved=False)

#     # رسالة تأكيد للمسؤول
#     modeladmin.message_user(request, "تم تجديد الرحلات وإضافة يوم إلى تاريخ الرحلة.")

from datetime import timedelta
from .models import Booking, Seat, Trip
from datetime import timedelta
import requests
from django.contrib import messages

from datetime import timedelta
import requests
from django.contrib import messages
# تأكد من استيراد كل النماذج والدوال اللازمة في بداية الملف
import requests
from datetime import timedelta
from django.contrib import messages
from .models import Trip, Seat, Booking, FormReservation


def renew_trips_by_days(modeladmin, request, queryset, days_to_add):
    """
    إجراء عام لتجديد الرحلات بناءً على عدد الأيام المضاف.
    الرحلة الجديدة تنشأ بدون حافلة (حقل الباص يكون فارغاً).
    """
    # إعدادات UltraMsg (يمكنك إزالتها إذا لم تعد تستخدمها هنا)
    INSTANCE_ID = "instance105329"
    API_TOKEN = settings.ULTRAMSG_API_TOKEN
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    
    renewed_count = 0
    for trip in queryset:
        # 1. تفريغ الحجوزات من الرحلة القديمة (اختياري، لكنه ممارسة جيدة)
        # تحديث حجوزات Booking
        trip.bookings.filter(status="active").update(status="inactive")
        # تحديث حجوزات FormReservation
        form_reservations = FormReservation.objects.filter(trip=trip)
        for form_res in form_reservations:
            form_res.trip = None
            form_res.seat = None
            form_res.status = 'pending'
            form_res.save()
        
        # 2. تحرير المقاعد في الحافلة القديمة (إذا كانت موجودة)
        if trip.bus:
            Seat.objects.filter(bus=trip.bus).update(is_reserved=False)

        # 3. تحديث الرحلة الحالية لجعلها قديمة وغير نشطة
        trip.is_active = False
        trip.is_old = True
        trip.save()

        # 4. إنشاء نسخة جديدة من الرحلة بنفس كل البيانات القديمة (ماعدا الباص والجامعة)
        trip_data = {
            field.name: getattr(trip, field.name)
            for field in Trip._meta.fields
            if field.name not in ['id', 'bus', 'category', 'date', 'is_active', 'is_old']
        }

        # تعديل القيم المطلوبة
        trip_data['date'] = trip.date + timedelta(days=days_to_add)
        trip_data['is_active'] = True
        trip_data['is_old'] = False
        trip_data['bus'] = None
        trip_data['category'] = None

        # إنشاء الرحلة الجديدة
        new_trip = Trip.objects.create(**trip_data)
        renewed_count += 1

        # 5. إرسال إشعارات للركاب لإعلامهم بتوفر الرحلة الجديدة (لو محتاج تستخدم UltraMsg هنا)
        # يمكنك لاحقاً إضافة كود إرسال رسالة واتساب لكل راكب لو حبيت
        # payload = {
        #     "token": API_TOKEN,
        #     "to": "<رقم الهاتف>",
        #     "body": f"تم إنشاء رحلة جديدة بتاريخ {new_trip.date}"
        # }
        # requests.post(URL, data=payload)

    # رسالة نجاح نهائية ومحسّنة
    if renewed_count > 0:
        modeladmin.message_user(
            request,
            f"✅ تم تجديد عدد {renewed_count} رحلة بنجاح بنفس جميع البيانات القديمة (بدون الجامعة والباص)."
        )

def renew_trips_one_day(modeladmin, request, queryset):
    renew_trips_by_days(modeladmin, request, queryset, days_to_add=1)

renew_trips_one_day.short_description = "تجديد الرحلات المختارة - إضافة يوم واحد"

def renew_trips_two_days(modeladmin, request, queryset):
    renew_trips_by_days(modeladmin, request, queryset, days_to_add=2)

renew_trips_two_days.short_description = "تجديد الرحلات المختارة - إضافة يومين"

def renew_trips_one_week(modeladmin, request, queryset):
    renew_trips_by_days(modeladmin, request, queryset, days_to_add=7)

renew_trips_one_week.short_description = "تجديد الرحلات المختارة - إضافة أسبوع"

def renew_trips_one_month(modeladmin, request, queryset):
    renew_trips_by_days(modeladmin, request, queryset, days_to_add=30)

renew_trips_one_month.short_description = "تجديد الرحلات المختارة - إضافة شهر"

from django.utils.timezone import now
from django.contrib import admin
from django import forms
from .models import Trip

class TripAdminForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = '__all__'

    # تخصيص حقل route ليكون واجهة نصية متعددة الأسطر
    route = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 40}),
        help_text="أدخل كل خط في سطر جديد."
    )

from datetime import timedelta
from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils.html import format_html
from .models import Trip, Seat

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import path
from datetime import timedelta
import requests
from django.shortcuts import redirect
from Anaconda_bus_APP.models import Trip, Seat

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse
from datetime import timedelta
import requests
from .models import Trip, Seat

from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.http import HttpResponse
from datetime import timedelta
import requests
from .models import Trip, Seat
from .models import FormReservation
from django.contrib import admin
from .models import FormReservation
from .forms import FormReservationAdminForm  # إذا كنت عامل فورم مخصص
import io
import requests

import logging

logger = logging.getLogger(__name__)  # ✅ لازم السطر ده
from django.template.loader import render_to_string
from weasyprint import HTML
from django import forms
from django.contrib import admin
from .models import Trip, Bus

class TripForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(TripForm, self).__init__(*args, **kwargs)
        if 'category' in self.data:  
            try:
                category_id = int(self.data.get('category'))
                self.fields['bus'].queryset = Bus.objects.filter(category_id=category_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:  
            self.fields['bus'].queryset = Bus.objects.filter(category=self.instance.category)
        else:
            self.fields['bus'].queryset = Bus.objects.none()
from .views import renew_trip_view, load_buses_ajax # ✅ --- استيراد الـ views الجديدة --- ✅
from django.contrib import admin
from .models import Trip

@admin.action(description="تعطيل كل رحلات الذهاب")
def deactivate_go_trips(modeladmin, request, queryset):
    Trip.objects.filter(type='go').update(is_active=False)
    modeladmin.message_user(request, "تم تعطيل جميع رحلات الذهاب ✅")

@admin.action(description="تعطيل كل رحلات العودة")
def deactivate_return_trips(modeladmin, request, queryset):
    Trip.objects.filter(type='return').update(is_active=False)
    modeladmin.message_user(request, "تم تعطيل جميع رحلات العودة ✅")
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
import arabic_reshaper
from bidi.algorithm import get_display
from io import BytesIO
@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    form = TripForm
    list_display = (
        'trip_name', 'category', 'date', 'start_time', 'bus', 'is_active', 'is_old',
         'view_bookings_button', 'generate_pdf_button' , 'view_report_button'  

    )
    class Media:
        css = {
            'all': ('admin/custom.css',)
        }

    list_filter = ('is_active', 'is_old', 'date', 'bus__category')
    search_fields = ('trip_name', 'bus__name')
    actions = [
        renew_trips_one_day,
        renew_trips_two_days,
        renew_trips_one_week,
        renew_trips_one_month,
        
    ]
    def deactivate_go_trips(self, request):
        count = Trip.objects.filter(trip_type='one_way').update(is_active=False)
        messages.success(request, f"✅ تم تعطيل {count} رحلة ذهاب.")
        return redirect("admin:Anaconda_bus_APP_trip_changelist")

    def deactivate_return_trips(self, request):
        count = Trip.objects.filter(trip_type='return').update(is_active=False)
        messages.success(request, f"✅ تم تعطيل {count} رحلة عودة.")
        return redirect("admin:Anaconda_bus_APP_trip_changelist")
    def view_report_button(self, obj):
        # هذا الزر سيفتح الرابط في نافذة جديدة (target="_blank")
        return format_html(
            f'<a href="{obj.id}/view_report/" target="_blank" class="button btn btn-info">👁️ عرض التقرير</a>'
        )
    view_report_button.short_description = "عرض التقرير (HTML)"
    view_report_button.allow_tags = True
    def generate_pdf_button(self, obj):
        return format_html(
            f'<a href="{obj.id}/generate_pdf/" class="button btn btn-success">📄 PDF & WhatsApp</a>'
        )
    generate_pdf_button.short_description = "PDF للرحلة"
    def generate_pdf_view(self, request, trip_id):
        try:
            from django.utils import timezone
            
            trip = Trip.objects.get(id=trip_id)
            form_reservations = FormReservation.objects.filter(trip=trip).order_by('created_at')
            bookings = Booking.objects.filter(Trip=trip).order_by('booking_date')

            # 📝 render HTML template
            html_string = render_to_string("trip_report.html", {
                "trip": trip,
                "form_reservations": form_reservations,
                "bookings": bookings,
                "now": timezone.now()  # إضافة التاريخ والوقت الحالي
            })

            # 🖨️ generate PDF
            pdf_content = HTML(string=html_string).write_pdf()

            # 📤 إرسال واتساب
            driver_number = trip.bus.driver_number if trip.bus else None
            if driver_number:
                try:
                    # تنظيف رقم الهاتف
                    driver_number = driver_number.replace(" ", "").replace("+", "").replace("-", "")
                    if not driver_number.startswith("2"):
                        driver_number = "2" + driver_number

                    # استخدام ملف مؤقت
                    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                        tmp_file.write(pdf_content)
                        tmp_file.flush()

                        url = "https://api.ultramsg.com/instance105329/messages/document"
                        payload = {
                            "token": settings.ULTRAMSG_API_TOKEN,
                            "to": f"+{driver_number}",
                            "filename": f"trip_{trip.id}_details.pdf",
                            "caption": f"📄 تفاصيل الرحلة {trip.trip_name}\n\n🔗 لعرض حجوزاتك: https://allen.allentravels.com/allen/my-buses/",
                        }

                        with open(tmp_file.name, 'rb') as pdf_file:
                            files = {'document': pdf_file}
                            response = requests.post(url, data=payload, files=files)

                    # حذف الملف المؤقت
                    os.unlink(tmp_file.name)

                    if response.status_code == 200:
                        messages.success(request, f"✅ تم إنشاء الـ PDF وإرساله على واتساب للسائق {driver_number}")
                    else:
                        messages.error(request, f"⚠️ PDF تم إنشاؤه لكن فشل الإرسال. كود: {response.status_code}")
                except Exception as e:
                    messages.error(request, f"⚠️ PDF تم إنشاؤه لكن حصل خطأ أثناء الإرسال: {e}")
            else:
                messages.warning(request, "✅ PDF تم إنشاؤه لكن لا يوجد رقم سائق مسجل.")

            # 📥 تقديم ملف PDF للتحميل
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="trip_{trip.id}_{trip.trip_name}.pdf"'
            return response

        except Trip.DoesNotExist:
            messages.error(request, "❌ الرحلة غير موجودة.")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")

        except Exception as e:
            logger.error(f"Unexpected error in generate_pdf_view: {e}", exc_info=True)
            messages.error(request, f"❌ حصل خطأ غير متوقع: {e}")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")
    def get_fields(self, request, obj=None):
        fields = [
            'trip_name', 'trip_type', 'route','category', 'bus',
            'date', 'start_time', 'back_time', 'end_time',
            'start_destination', 'end_destination',
            'one_way_price', 'return_price', 'round_trip_price',
            'is_active', 'next_trip_date', 'is_old'
        ]
        if obj and obj.trip_type == 'round_differentdays':
            fields += ['related_departure_trip', 'related_return_trip','departure_seat_price', 'return_seat_price']
        return fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ['related_departure_trip', 'related_return_trip']:
            kwargs['queryset'] = Trip.objects.filter(date__gte=timezone.now().date(), is_active=True, is_old=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_old=False)

    def save_model(self, request, obj, form, change):
        # لو تعديل موجود ومش عملية duplicate أو تجديد
        is_duplicate = 'duplicate' in request.path or 'renew' in request.path
        if change and not is_duplicate and obj.bus:
            self.send_update_notification(request, obj)

        super().save_model(request, obj, form, change)
        
    def send_update_notification(self, request, trip):
        driver_number = trip.bus.driver_number if trip.bus else None
        if driver_number:
            # تنظيف رقم الهاتف
            driver_number = driver_number.replace(" ", "").replace("+", "").replace("-", "")
            if not driver_number.startswith("2"):
                driver_number = "2" + driver_number
                
            message = (
                f" تحديث مهم: تم تعديل بيانات رحلتك '{trip.trip_name}'.\n"
                f"التاريخ الجديد: {trip.date.strftime('%d-%m-%Y')}\n"
                f" التوقيت الجديد: {trip.start_time.strftime('%H:%M')}\n"
                f" المسار: {trip.route}\n"
                "لبيانات الرحله ادخل علي الرابط التالي:\n https://allen.allentravels.com/allen/my-buses/\n"
            )
            INSTANCE_ID = "instance105329"
            API_TOKEN = settings.ULTRAMSG_API_TOKEN
            URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
            payload = {"token": API_TOKEN, "to": f"+{driver_number}", "body": message}
            try:
                response = requests.post(URL, data=payload)
                if response.status_code == 200:
                    messages.success(request, f"تم إرسال إشعار تحديث للسائق {driver_number}")
                else:
                    messages.error(request, f"فشل إرسال الإشعار للسائق {driver_number}. رمز الخطأ: {response.status_code}")
            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء إرسال الإشعار للسائق {driver_number}: {e}")

    def duplicate_trip(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id)
            base_name = trip.trip_name
            counter = 1
            new_name = f"{base_name} {counter}"
            while Trip.objects.filter(trip_name=new_name).exists():
                counter += 1
                new_name = f"{base_name} {counter}"

            trip.bookings.filter(status="active").update(status="inactive")
            Seat.objects.filter(bus=trip.bus).update(is_reserved=False)

            trip.is_active = False
            trip.is_old = False
            trip.save()

            new_trip = Trip.objects.create(
                trip_name=new_name,
                route=trip.route,
                date=trip.date + timedelta(days=1),
                start_time=trip.start_time,
                bus=trip.bus,
                is_active=True,
                is_old=False,
            )

            trip.bus.location_url = None
            trip.bus.latitude = None
            trip.bus.longitude = None
            trip.bus.save()

            messages.success(request, f"تم تكرار الرحلة {trip.trip_name} لليوم التالي باسم جديد {new_name}!")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")
        except Trip.DoesNotExist:
            messages.error(request, "الرحلة غير موجودة!")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")

    def assign_random_seats(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id)
            unassigned = FormReservation.objects.filter(trip=trip, seat__isnull=True)
            available_seats = list(Seat.objects.filter(bus=trip.bus, is_reserved=False))

            if not available_seats or not unassigned.exists():
                messages.warning(request, "لا يوجد كراسي متاحة أو لا يوجد ركاب بدون كراسي.")
                return redirect("admin:Anaconda_bus_APP_trip_changelist")

            import random
            random.shuffle(available_seats)

            for reservation, seat in zip(unassigned, available_seats):
                reservation.seat = seat
                reservation.save()
                seat.is_reserved = True
                seat.save()

            messages.success(request, f"تم توزيع الكراسي عشوائيًا على {unassigned.count()} راكب.")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")
        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء التوزيع العشوائي: {e}")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")

    def assign_random_seats_button(self, obj):
        return format_html(f'<a href="{obj.id}/assign_random_seats/" class="button btn btn-warning">🎲 توزيع عشوائي</a>')

    assign_random_seats_button.short_description = "توزيع كراسي عشوائيًا"

    def duplicate_trip_button(self, obj):
        return format_html(f'<a href="{obj.id}/duplicate/" class="button">📑 تكرار</a>')

    duplicate_trip_button.allow_tags = True
    duplicate_trip_button.short_description = "تكرار الرحلة"

    def view_bookings(self, request, trip_id):
        try:
            trip = Trip.objects.get(id=trip_id)
            form_reservations = FormReservation.objects.filter(trip=trip)
            bookings = Booking.objects.filter(Trip=trip)

            if not form_reservations.exists() and not bookings.exists():
                messages.warning(request, "لا توجد حجوزات لهذه الرحلة.")
                return redirect("admin:Anaconda_bus_APP_trip_changelist")

            # الكراسي المتاحة في الباص
            seats = Seat.objects.filter(bus=trip.bus)
            reserved_seats_ids = list(
                FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list("seat__id", flat=True)
            ) + list(
                Seat.objects.filter(bookings__Trip=trip).values_list("id", flat=True)
            )

            response = f"""
            <html>
            <head>
                <title>حجوزات الرحلة {trip.trip_name}</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
                <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
            </head>
            <body class="container mt-4">
                <h2 class="mb-4">تخطيط مقاعد الحافلة للرحلة: {trip.trip_name}</h2>
                <div class="bus-layout-container" style="direction: rtl;">
                    <div class="bus-layout" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 40px;">
            """

            for seat in seats:
                is_reserved = seat.id in reserved_seats_ids
                seat_color = "#ff0000" if is_reserved else "#4CAF50"
                seat_status_class = "reserved" if is_reserved else "available"
                seat_price_html = f"""
                    <span class="seat-price" 
                        style="position: absolute;
                                top: -8px;
                                right: -5px;
                                background: #ffc107;
                                color: #000;
                                padding: 2px 5px;
                                border-radius: 10px;
                                font-size: 12px;
                                font-weight: bold;">
                    </span>"""  
                seat_row = seat.row if seat.row is not None else 0
                seat_col = seat.column if seat.column is not None else 0
                response += f"""
                    <div class="seat" 
                        style="grid-row: {seat_row + 1}; 
                                grid-column: {seat_col + 1};
                                position: relative;">
                        <label class="seat-label">
                            <div class="seat-icon {seat_status_class}"
                                style="width: 50px; 
                                        height: 50px;
                                        border: 2px solid {seat_color};
                                        border-radius: 5px;
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        justify-content: center;
                                        padding-top: 5px;
                                        transition: all 0.3s;">
                                <i class="fas fa-chair" style="font-size: 18px;"></i>
                                <span class="seat-number" style="font-weight: bold; margin-top: 3px;">{seat.seat_number}</span>
                            </div>
                            {seat_price_html}
                        </label>
                    </div>
                """

            response += """
                    </div>
                </div>

                <h2 class="mb-3">قائمة الحجوزات</h2>
                <table class="table table-striped table-bordered">
                    <thead class="table-dark">
                        <tr>
                            <th>اسم الراكب</th>
                            <th>تاريخ الحجز</th>
                            <th>مكان الركوب</th>
                            <th>رقم الكرسي</th>
                            <th>طريقه الدفع </th>
                            <th>مصدر الحجز</th>
                            <th>إجراء</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            # حجوزات الفورم
            for booking in form_reservations:
                student_name = booking.student_name or 'غير متوفر'
                booking_date = booking.created_at.strftime('%d-%m-%Y') if booking.created_at else 'غير متوفر'
                pickup_location = booking.pickup_location or '---'
                seat_number = booking.seat.seat_number if booking.seat else '---'
                cancel_url = reverse("admin:Anaconda_bus_APP_formreservation_delete", args=[booking.id])

                response += f"""
                    <tr>
                        <td>{student_name}</td>
                        <td>{booking_date}</td>
                        <td>{pickup_location}</td>
                        <td>{seat_number}</td>
                        <td>{booking.get_status_display()}</td>

                        <td>📝 الفورم</td>
                        <td>
                            <form action="{cancel_url}" method="post" style="display:inline;">
                                <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
                                <button type="submit" class="btn btn-danger btn-sm"
                                        onclick="return confirm('هل أنت متأكد من إلغاء الحجز؟');">
                                    إلغاء الحجز
                                </button>
                            </form>
                        </td>
                    </tr>
                """

            # حجوزات البوك سيت
            for booking in bookings:
                student_name = booking.passenger.name if hasattr(booking.passenger, "name") else "غير متوفر"
                booking_date = booking.created_at.strftime('%d-%m-%Y') if hasattr(booking, "created_at") else "غير متوفر"
                pickup_location = booking.selected_route or "---"
                seats_list = [str(s.seat_number) for s in booking.seats_reserved.all()]
                seat_numbers = ", ".join(seats_list) if seats_list else "---"
                cancel_url = reverse("admin:Anaconda_bus_APP_booking_delete", args=[booking.id])

                response += f"""
                    <tr>
                        <td>{student_name}</td>
                        <td>{booking_date}</td>
                        <td>{pickup_location}</td>
                        <td>{seat_numbers}</td>
                        <td>اختيار كرسي  </td>
                        <td>
                            <form action="{cancel_url}" method="post" style="display:inline;">
                                <input type="hidden" name="csrfmiddlewaretoken" value="{request.COOKIES.get('csrftoken', '')}">
                                <button type="submit" class="btn btn-danger btn-sm"
                                        onclick="return confirm('هل أنت متأكد من إلغاء الحجز؟');">
                                    إلغاء الحجز
                                </button>
                            </form>
                        </td>
                    </tr>
                """

            response += """
                    </tbody>
                </table>
            </body>
            </html>
            """

            return HttpResponse(response)

        except Trip.DoesNotExist:
            messages.error(request, "الرحلة غير موجودة!")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")

    def view_bookings_button(self, obj):
        return format_html(f'<a href="{obj.id}/bookings/" class="button">👀 عرض الحجوزات</a>')

    view_bookings_button.short_description = "عرض الحجوزات"
    
    def create_round_trip_view(self, request):
        if request.method == 'POST':
            departure_id = request.POST.get('departure_trip')
            return_ids = request.POST.getlist('return_trips')

            if not departure_id or not return_ids:
                messages.error(request, "يرجى اختيار رحلة ذهاب ورحلات عودة.")
                return redirect(request.path)

            try:
                departure_trip = Trip.objects.get(id=departure_id)
                return_trips = Trip.objects.filter(id__in=return_ids)

                created_count = 0

                for return_trip in return_trips:
                    new_trip_name = f"{departure_trip.trip_name} + {return_trip.trip_name}"
                    
                    Trip.objects.create(
                        trip_name=new_trip_name,
                        trip_type='round_differentdays',
                        route=departure_trip.route,  # أو تدمج route من الاثنين لو حبيت
                        bus=departure_trip.bus,  # أو تخليه return_trip.bus حسب اللوجيك
                        date=departure_trip.date,
                        start_time=departure_trip.start_time,
                        back_time=return_trip.back_time,
                        related_departure_trip=departure_trip,
                        related_return_trip=return_trip,
                        one_way_price=departure_trip.one_way_price,
                        return_price=return_trip.return_price,
                        round_trip_price=departure_trip.round_trip_price,
                        departure_seat_price=departure_trip.departure_seat_price,
                        return_seat_price=return_trip.return_seat_price,
                        start_destination=departure_trip.start_destination,
                        end_destination=return_trip.end_destination,
                        is_active=True,
                        is_old=False,
                    )

                    created_count += 1

                messages.success(request, f"✅ تم إنشاء {created_count} رحلة ذهاب وعودة (round_differentdays) بنجاح.")
                return redirect('admin:Anaconda_bus_APP_trip_changelist')

            except Trip.DoesNotExist:
                messages.error(request, "حدث خطأ أثناء اختيار الرحلة.")
                return redirect(request.path)

        trips = Trip.objects.order_by('-date')
        return render(request, 'admin/create_round_trip.html', {'trips': trips})
    
    def changelist_view(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['custom_button'] = True
        return super().changelist_view(request, extra_context=extra_context)
 # --- الخطوة 1: أضف الدالة المفقودة هنا ---
    def view_report_view(self, request, trip_id):
        """
        هذه الدالة تعرض صفحة الـ HTML للتقرير مباشرة في المتصفح.
        """
        try:
            trip = Trip.objects.get(id=trip_id)
            form_reservations = FormReservation.objects.filter(trip=trip)
            bookings = Booking.objects.filter(Trip=trip)

            # نستخدم render لعرض القالب مباشرة
            return render(request, "trip_report.html", {
                "trip": trip,
                "form_reservations": form_reservations,
                "bookings": bookings
            })

        except Trip.DoesNotExist:
            messages.error(request, "الرحلة غير موجودة.")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")
        except Exception as e:
            # من الجيد تسجيل الخطأ للمساعدة في التصحيح لاحقاً
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.error(f"Unexpected error in view_report_view: {e}", exc_info=True)
            messages.error(request, f"حصل خطأ غير متوقع: {e}")
            return redirect("admin:Anaconda_bus_APP_trip_changelist")
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:trip_id>/view_report/', self.admin_site.admin_view(self.view_report_view), name='view_report'),
            path('bus-report/', self.admin_site.admin_view(bus_report_view), name='bus_report'),
            # path('<int:old_trip_id>/renew/', self.admin_site.admin_view(renew_trip_view), name='renew_trip'),
            # path('ajax/load-buses/', self.admin_site.admin_view(load_buses_ajax), name='ajax_load_buses'),
 
            path('<int:trip_id>/generate_pdf/', self.admin_site.admin_view(self.generate_pdf_view), name='generate_pdf'),
            path('create_round_trip/', self.admin_site.admin_view(self.create_round_trip_view), name='create_round_trip'),
            path('<int:trip_id>/duplicate/', self.admin_site.admin_view(self.duplicate_trip), name='duplicate_trip'),
            path('<int:trip_id>/bookings/', self.admin_site.admin_view(self.view_bookings), name='view_bookings'),
            path('<int:trip_id>/assign_random_seats/', self.admin_site.admin_view(self.assign_random_seats), name='assign_random_seats'),
          path('deactivate_go_trips/', self.admin_site.admin_view(self.deactivate_go_trips), name='deactivate_go_trips'),
            path('deactivate_return_trips/', self.admin_site.admin_view(self.deactivate_return_trips), name='deactivate_return_trips'),

        ]
        return custom_urls + urls


from django.contrib import admin
from .models import Booking

from django.contrib import admin
from .models import Booking

from django.contrib import admin
from .models import Booking

class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'Trip', 'get_selected_route', 'reserved_seats_list',
        'reserved_seats_count', 'payment_method', 'transaction_number'
        , 'passenger_phone', 'status', 
        'attendance_status', 'serial_code', 
    )
    search_fields = (
        'transaction_number', 'user__username'
        , 'attendance_status'
    )
    list_filter = ('selected_route','payment_method', 'status', 'attendance_status')
    fields = (
        'user', 'Trip', 'seats_reserved', 'payment_method', 
        'transaction_number', 'mobile_number', 'transaction_image', 
        'status', 'attendance_status'
    )
    actions = ['cancel_booking']
    def get_selected_route(self, obj):
            return obj.selected_route or "-"  # عرض القيمة أو عرض "-" إذا كانت فارغة
    get_selected_route.short_description = "Selected Route"
    def cancel_booking(self, request, queryset):
        for booking in queryset:
            if booking.status == 'completed':
                self.message_user(
                    request, 
                    f"لا يمكن إلغاء الحجز {booking.id} لأنه مكتمل.", 
                    level="error"
                )
                continue
            # إلغاء الحجز وإرجاع المقاعد
            booking.status = 'cancelled'
            booking.seats_reserved.update(is_reserved=False)
            booking.save()

        self.message_user(request, "تم إلغاء الحجوزات المحددة وإعادة المقاعد إلى حالتها.")
    cancel_booking.short_description = "إلغاء الحجوزات وإعادة المقاعد"

admin.site.register(Booking, BookingAdmin)

from django.contrib import admin
from .models import Seat

# @admin.register(Seat)
# class SeatAdmin(admin.ModelAdmin):
#     list_display = ('bus', 'seat_number', 'is_reserved','trip_date')
#     list_filter = (
#         'bus', 
#         'seat_number', 

#     ) 

admin.site.register(passenger, PassengerAdmin)
admin.site.register(Category, CategoryAdmin)


# User id
# Name
# Category
# Subscription start date
# Subscription end date
# Attendance date
# Attendance status
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from .models import Bus, Booking
from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.contrib.auth.models import User
from .models import Bus, Seat, Category, passenger
from django.contrib import admin
from django.utils.html import format_html
from .models import Bus

from django.contrib import admin
from django.utils.html import format_html
from .models import Bus
from django.utils.html import format_html
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import admin, messages
from .models import Bus

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from .models import Bus, Category

from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import Bus, Category

# 🔹 فلتر مخصص لدعم اختيار أكثر من كاتيجوري
from django.contrib import admin
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django import forms
from .models import Bus, Category

class CategoryFilter(admin.SimpleListFilter):
    title = _("الفئة")  
    parameter_name = "category"

    def lookups(self, request, model_admin):
        """عرض قائمة بجميع الفئات المتاحة"""
        return [(c.id, c.name) for c in Category.objects.all()]

    def queryset(self, request, queryset):
        """تصفية البيانات بناءً على القيم المختارة"""
        if self.value():
            category_ids = self.value().split(",")  # السماح باختيار أكثر من قيمة
            return queryset.filter(category__id__in=category_ids)
        return queryset

# ✅ 2️⃣ نموذج اختيار متعدد
class MultiCategoryForm(forms.Form):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # 🔥 تفعيل تحديد أكثر من قيمة
        required=False
    )
from django.urls import reverse

from django.contrib import admin
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render, get_object_or_404
from .models import Bus
from .views import bus_report_view # استورد الـ view الخاص بك

class BusAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'bus_type', 'capacity', 'Bus_driver', 'is_active', 'status_display', 'duplicate_bus_button')
    actions = ['duplicate_buses_with_new_category']  # الإجراء الجديد
    def duplicate_buses_with_new_category(self, request, queryset):
            if 'apply' in request.POST:
                new_category_id = request.POST.get('category')
                new_category = Category.objects.get(id=new_category_id)  # ✅ استخدم الموديل الصحيح

                for bus in queryset:
                    bus.pk = None  # لإنشاء نسخة جديدة
                    bus.category = new_category  # تحديث الكاتيجوري
                    bus.save()

                self.message_user(request, f"✅ تم تكرار {queryset.count()} باص وتعيينهم للكاتيجوري الجديد.", messages.SUCCESS)
                return HttpResponseRedirect(request.get_full_path())

            categories = Category.objects.all()  # ✅ استدعاء الكاتيجوري الصح
            return render(request, 'admin/duplicate_buses_category.html', {
                'buses': queryset,
                'categories': categories,
                'action': 'duplicate_buses_with_new_category',
            })

    duplicate_buses_with_new_category.short_description = "📋 تكرار الباصات مع اختيار كاتيجوري مختلف"
    list_filter = (
        'is_active',
        CategoryFilter,  # ✅ الفلتر الجديد لاختيار أكثر من كاتيجوري
    )
    change_form_template = 'admin/bus_change_form.html'
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [

            path('<int:bus_id>/layout/', self.admin_site.admin_view(self.seat_layout_view), name='bus_seat_layout'),
        ]
        return custom_urls + urls

    def seat_layout_view(self, request, bus_id):
        bus = get_object_or_404(Bus, id=bus_id)

        if request.method == 'POST':
            Seat.objects.filter(bus=bus).delete()
            seats_data = request.POST.getlist('seats[]')
            for seat in seats_data:
                if ',' not in seat:
                    continue
                parts = seat.split(',')
                if len(parts) != 3:
                    continue
                seat_number, row, col = parts
                Seat.objects.create(
                    bus=bus,
                    seat_number=seat_number.strip(),
                    row=int(row),
                    column=int(col)
                )

            change_url = reverse('admin:Anaconda_bus_APP_bus_change', args=[bus_id])
            return redirect(change_url)

        # ✅ إرسال المقاعد الموجودة
        seats = Seat.objects.filter(bus=bus)
        reserved_seats = []  # عدلها حسب النظام الفعلي لو عندك حجز

        rows_range = range(25)         # عدد الصفوف
        columns_range = range(5)       # عدد الأعمدة

        return TemplateResponse(request, 'admin/seat_layout.html', {
            'bus': bus,
            'seats': seats,
            'reserved_seats': reserved_seats,
            'rows_range': rows_range,
            'columns_range': columns_range,
        })

    @admin.display(description="حالة الاتصال")
    def status_display(self, obj):
        if obj.is_online():  
            return format_html('<span style="color: green; font-weight: bold;">🟢 متصل</span>')
        return format_html('<span style="color: red; font-weight: bold;">🔴 غير متصل</span>')

    @admin.display(description="تكرار")
    def duplicate_bus_button(self, obj):
        return format_html(f'<a href="{obj.id}/duplicate/" class="button">📑 تكرار</a>')

admin.site.register(Bus, BusAdmin)

#  docker exec -it allen___bus-main-web-1 python manage.py makemigrations
# from django.contrib import admin
# from .models import SubscriptionTransaction

# from django.contrib import admin
# from .models import SubscriptionTransaction, SubscriptionType
# from django.contrib import admin
# from django.db.models import F
# from .models import SubscriptionTransaction, SubscriptionType, passenger

# @admin.register(SubscriptionTransaction)
# class SubscriptionTransactionAdmin(admin.ModelAdmin):
#     list_display = (
#         'student_name',
#         'subscription_duration',
#         'amount',
#         'transaction_number',
#         'status',
#         'included_trips',
#         'created_at',
#     )
#     list_filter = ('status', 'created_at',)
#     search_fields = ('transaction_number', 'student__name')

#     def student_name(self, obj):
#         return obj.student.name
#     student_name.short_description = "اسم الطالب"

#     def subscription_duration(self, obj):
#         if obj.subscription_type:
#             return obj.subscription_type.get_duration_display()
#         return "غير محدد"

#     def included_trips(self, obj):
#         subscription = obj.subscription_type
#         return subscription.included_trips if subscription else "غير محدد"
#     included_trips.short_description = "عدد الرحلات المشمولة"

#     # تعديل الحفظ
#     def save_model(self, request, obj, form, change):
#         # التحقق من تغيير الحالة إلى "approved"
#         if change and 'status' in form.changed_data and obj.status == 'approved':
#             subscription = obj.subscription_type
#             if subscription:
#                 # تحديث إجمالي عدد الرحلات للراكب
#                 passenger_obj = obj.student
#                 passenger_obj.subscription_duration += subscription.included_trips
#                 passenger_obj.save()

#         super().save_model(request, obj, form, change)

# from django.contrib import admin
# from .models import SubscriptionType

# @admin.register(SubscriptionType)
# class SubscriptionTypeAdmin(admin.ModelAdmin):
#     list_display = ('get_duration_display', 'price_per_trip', 'included_trips')
#     list_editable = ('price_per_trip', 'included_trips')
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from .models import Subscription, SubscriptionBooking

from django.contrib import admin
from .models import Subscription

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('category', 'get_subscription_duration_display', 'price')
    list_filter = ('category', 'subscription_duration')

from django.contrib import admin
from .models import SubscriptionBooking, passenger
import requests

@admin.action(description="تعيين الحجز كمكتمل")
def mark_as_completed(modeladmin, request, queryset):
    INSTANCE_ID = "instance105329"  
    API_TOKEN = settings.ULTRAMSG_API_TOKEN  
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    for booking in queryset:
        if booking.status != 'completed':  
            booking.status = 'completed'
            booking.save()

            passenger_instance = booking.passenger

            # ✅ إرسال إشعار واتساب مباشرة بعد التحديث
            message = f"✅ عزيزي {passenger_instance.name}، تم تأكيد اشتراكك بنجاح! 🎉 شكراً لاختيارك خدمتنا. 🚍😊"
            payload = {
                "token": API_TOKEN,
                "to": passenger_instance.phone_number,
                "body": message,
            }
            requests.post(URL, data=payload)

            # ✅ عرض رسالة نجاح في Django Admin
            modeladmin.message_user(
                request,
                f"تم تأكيد الاشتراك وإرسال إشعار للراكب {passenger_instance.name}.",
                level="success"
            )

import requests

@admin.action(description="تعيين الحجز كمكتمل")
def mark_as_completed(modeladmin, request, queryset):
    INSTANCE_ID = "instance105329"  
    API_TOKEN = settings.ULTRAMSG_API_TOKEN  
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    for booking in queryset:
        if booking.status != 'completed':  
            booking.status = 'completed'
            booking.save()

            passenger_instance = booking.passenger
            subscription_instance = booking.subscription

            # ✅ تحديث مدة الاشتراك بإضافة عدد الرحلات الجديدة
            passenger_instance.subscription_duration += subscription_instance.number_of_trips
            passenger_instance.save()

            # ✅ إرسال إشعار واتساب بعد تحديث الاشتراك
            message = f"✅  {passenger_instance.name}، تم تأكيد اشتراكك بنجاح!  يمكنك الان حجز الرحلات  بكل سهوله! . "
            payload = {
                "token": API_TOKEN,
                "to": passenger_instance.phone_number,
                "body": message,
            }
            requests.post(URL, data=payload)

            # ✅ عرض رسالة نجاح في Django Admin
            modeladmin.message_user(
                request,
                f"تم تحديث مدة الاشتراك للراكب {passenger_instance.name}، وتم إرسال إشعار واتساب.",
                level="success"
            )

import requests

@admin.action(description="تعيين الحجز كملغي")
def mark_as_canceled(modeladmin, request, queryset):
    INSTANCE_ID = "instance105329"  
    API_TOKEN = settings.ULTRAMSG_API_TOKEN  
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    for booking in queryset:
        if booking.status != 'canceled':  
            booking.status = 'canceled'
            booking.save()

            passenger_instance = booking.passenger
            message = f"⚠️  {passenger_instance.name}  طلب الاشتراك في الرحلات الخاص بك به مشكله. نأسف لهذا الإزعاج. للمزيد من التفاصيل، يرجى التواصل معنا. 📞"
            payload = {
                "token": API_TOKEN,
                "to": passenger_instance.phone_number,
                "body": message,
            }
            requests.post(URL, data=payload)

            # ✅ عرض رسالة نجاح في Django Admin
            modeladmin.message_user(
                request,
                f"تم إلغاء الحجز للراكب {passenger_instance.name}، وتم إرسال إشعار واتساب.",
                level="warning"
            )

from django.urls import reverse

from django.utils.html import format_html
from django.urls import reverse

class SubscriptionBookingAdmin(admin.ModelAdmin):
    list_display = ('subscription', 'passenger_link', 'whatsapp_button', 'status', 'payment_amount', 'transaction_code')
    list_filter = ('status', 'created_at', 'subscription')
    actions = [mark_as_completed, mark_as_canceled]
    search_fields = ('transaction_code', 'passenger__name', 'passenger__phone_number','passenger__university_code')

    def passenger_link(self, obj):
        """إرجاع اسم الراكب كرابط إلى صفحة تفاصيله في Django Admin"""
        url = reverse('admin:Anaconda_bus_APP_passenger_change', args=[obj.passenger.id])
        return format_html('<a href="{}">{}</a>', url, obj.passenger.name)

    passenger_link.short_description = "الراكب"  

    def whatsapp_button(self, obj):
        try:
            phone_number = f"{obj.passenger.phone_number}" if obj.passenger.phone_number else "غير متوفر"
            message = f"مرحبا {obj.passenger.name}، تم تأكيد حجزك في الاشتراك {obj.subscription} بحالة {obj.status} ورمز المعاملة {obj.transaction_code}."
            whatsapp_url = f"https://wa.me/{phone_number}?text={message.replace(' ', '%20')}"

            return format_html('<a href="{}" target="_blank" class="button" style="background:#25D366;color:white;padding:5px 10px;border-radius:5px;text-decoration:none;">واتساب</a>', whatsapp_url)
        except Exception as e:
            return format_html('<span style="color:red;">خطأ: {}</span>', e)  # عرض الخطأ في Django Admin

    whatsapp_button.short_description = "تواصل عبر واتساب"

admin.site.register(SubscriptionBooking, SubscriptionBookingAdmin)
from django.contrib import admin
from .models import Car, CarBooking

from django.contrib import admin
from .models import Car, CarImage

class CarImageInline(admin.TabularInline):
    model = CarImage
    extra = 1 

@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'model', 'is_available')
    list_filter = ('brand', 'model', 'is_available')
    search_fields = ('name', 'brand', 'model')
    inlines = [CarImageInline]  # إضافة صور إضافية من واجهة الإدارة
from django.contrib import admin
from .models import CarBooking

class CarBookingAdmin(admin.ModelAdmin):
    list_display = (
        'car',
        'customer_name',
        'phone_number',
        'get_trip_type_display',
        'go_date',
        'return_date',
        'payment_percentage',
        'status',
        'distance_km',
        'created_at',
        'from_location',
        'to_location',
        'total_price',
    )
    
    list_filter = (
        'status',
        'trip_type',
        'payment_percentage',
        'go_date',
        'created_at'
    )
    
    search_fields = (
        'customer_name',
        'phone_number',
        'car__name',
        'car__brand'
    )
    
    list_editable = ('status',)  # يسمح بتعديل الحالة مباشرة من القائمة
    
    readonly_fields = (
        'created_at',
    )
    
    fieldsets = (
        ('معلومات الحجز', {
            'fields': (
                'car',
                'customer_name',
                'phone_number'
            )
        }),
        ('تفاصيل الرحلة', {
            'fields': (
                'trip_type',
                'go_date',
                'return_date',
                'distance_km',
                'total_price',
            )
        }),
        ('المعلومات المالية', {
            'fields': (
                'payment_percentage',
            )
        }),
        ('حالة الحجز', {
            'fields': (
                'status',
                'created_at'
            )
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
    mark_as_confirmed.short_description = "تأكيد الحجوزات المحددة"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "إلغاء الحجوزات المحددة"
    
    def save_model(self, request, obj, form, change):
        if 'distance_km' in form.changed_data or 'trip_type' in form.changed_data:
            obj.calculate_total_price()
        super().save_model(request, obj, form, change)

admin.site.register(CarBooking, CarBookingAdmin)
from .models import FormReservation

from django.urls import reverse
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect  # تأكد من إضافة هذا الاستيراد
from django.utils.html import format_html
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import FormReservation, Trip , Round

from django.contrib import admin
from .models import FormReservation, Trip
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.urls import reverse

from django.contrib import messages
from django.shortcuts import render, redirect
from django import forms
from .models import Trip
from django.contrib import admin
from .models import DiscountCode

@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'user', 'value', 'is_used', 'created_at')
    search_fields = ('code', 'user__username')
    list_filter = ('is_used', 'created_at')


class TripSelectForm(forms.Form):
    trip = forms.ModelChoiceField(
        queryset=Trip.objects.none(),
        label="اختر الرحلة",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        trip_queryset = kwargs.pop('trip_queryset', None)
        super().__init__(*args, **kwargs)
        if trip_queryset is not None:
            self.fields['trip'].queryset = trip_queryset
from django.contrib.admin import SimpleListFilter
from django.utils.translation import gettext_lazy as _
from .models import Round, City

class RoundFilter(SimpleListFilter):
    title = _('الراوند')  # يظهر في واجهة الفلتر
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        rounds = Round.objects.all()
        return [(round.id, round.name) for round in rounds]

    def queryset(self, request, queryset):
        if self.value():
            try:
                selected_round = Round.objects.get(pk=self.value())
                # استخراج كل المدن المرتبطة بالراوند المحدد
                round_cities = selected_round.cities.all()
                return queryset.filter(city__in=round_cities)
            except Round.DoesNotExist:
                return queryset
        return queryset
import requests
from django.utils.timezone import localdate
from django.conf import settings  # أضف هذا الاستيراد في الأعلى
from django.db import models
from .forms import FormReservationAdminForm 
from django import forms

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, redirect
from django.utils.timezone import localdate
import requests

from .models import FormReservation, City, Round, Trip, Seat, Booking
class MultiTimeFilter(admin.SimpleListFilter):
    title = 'وقت العودة'
    parameter_name = 'back_time'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category__name")

        qs = FormReservation.objects.all()
        if category_id:
            qs = qs.filter(category__name=category_id)

        times = qs.order_by('back_time').values_list('back_time', flat=True).distinct()
        return [(str(t), t.strftime("%H:%M")) for t in times if t]

    def queryset(self, request, queryset):
        values = request.GET.getlist(self.parameter_name)
        if values:
            return queryset.filter(back_time__in=values)
        return queryset


class MultiArrivalTimeFilter(admin.SimpleListFilter):
    title = 'وقت الوصول'
    parameter_name = 'arrival_time'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category__name")

        qs = FormReservation.objects.all()
        if category_id:
            qs = qs.filter(category__name=category_id)

        times = qs.order_by('arrival_time').values_list('arrival_time', flat=True).distinct()
        return [(str(t), t.strftime("%H:%M")) for t in times if t]

    def queryset(self, request, queryset):
        values = request.GET.getlist(self.parameter_name)
        if values:
            return queryset.filter(arrival_time__in=values)
        return queryset


# ✅ فلتر مدينة الذهاب
class GoingCityFilter(admin.SimpleListFilter):
    title = "مدينة الذهاب"
    parameter_name = "going_city"

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category__name")
        if category_id:
            cities = City.objects.filter(category__name=category_id)
        else:
            cities = City.objects.all()
        return [(city.id, city.name) for city in cities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(going_city__id=self.value())
        return queryset


# ✅ فلتر مدينة العودة
class ReturnCityFilter(admin.SimpleListFilter):
    title = "مدينة العودة"
    parameter_name = "return_city"

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category__name")
        if category_id:
            cities = City.objects.filter(category__name=category_id)
        else:
            cities = City.objects.all()
        return [(city.id, city.name) for city in cities]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(return_city__id=self.value())
        return queryset


# ✅ فلتر الراوندات
class RoundFilter(admin.SimpleListFilter):
    title = "الراوند"
    parameter_name = "round"

    def lookups(self, request, model_admin):
        rounds = Round.objects.all()
        return [(round.id, round.name) for round in rounds]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(trip__round__id=self.value())
        return queryset
from django.contrib import admin
from .models import Category # تأكد من استيراد موديل Category
from django.contrib import admin
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from urllib.parse import urlencode
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from urllib.parse import urlencode
from .models import FormReservation, City, Round, Trip, Seat, Booking, Category
from django import forms

# نموذج الفلتر الأساسي المتعدد
class MultiSelectFilter(admin.SimpleListFilter):
    template = 'admin/multi_select_filter.html'
    
    def lookups(self, request, model_admin):
        return []
    
    def queryset(self, request, queryset):
        if self.value():
            values = self.value().split(',')
            # للعلاقات نستخدم __in، للحقول العادية نستخدم __in أيضاً
            if '__' in self.parameter_name:
                # إذا كان حقل علاقة (يحتوي على __)
                field_name = self.parameter_name
                return queryset.filter(**{f'{field_name}__in': values})
            else:
                # للحقول العادية
                return queryset.filter(**{f'{self.parameter_name}__in': values})
        return queryset
    
    def choices(self, changelist):
        current_values = self.value().split(',') if self.value() else []
        query_params = dict(changelist.get_filters_params())
        
        for lookup, title in self.lookup_choices:
            selected = str(lookup) in current_values
            
            if selected:
                new_values = [v for v in current_values if v != str(lookup)]
            else:
                new_values = current_values + [str(lookup)]
            
            # إزالة القيم الفارغة
            new_values = [v for v in new_values if v]
            
            if new_values:
                query_params[self.parameter_name] = ','.join(new_values)
            elif self.parameter_name in query_params:
                del query_params[self.parameter_name]
            
            query_string = urlencode(query_params, doseq=True)
            
            yield {
                "selected": selected,
                "query_string": f"?{query_string}",
                "display": title,
            }

# فلتر الجامعات المتعدد
class MultiCategoryFilter(MultiSelectFilter):
    title = 'الجامعة'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return [(c.id, c.name) for c in Category.objects.all()]

# فلتر مدن الذهاب المتعدد
class MultiGoingCityFilter(MultiSelectFilter):
    title = 'مدينة الذهاب'
    parameter_name = 'going_city'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category")
        if category_id:
            cities = City.objects.filter(category__id__in=category_id.split(','))
        else:
            cities = City.objects.all()
        return [(city.id, city.name) for city in cities]

# فلتر مدن العودة المتعدد
class MultiReturnCityFilter(MultiSelectFilter):
    title = 'مدينة العودة'
    parameter_name = 'return_city'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category")
        if category_id:
            cities = City.objects.filter(category__id__in=category_id.split(','))
        else:
            cities = City.objects.all()
        return [(city.id, city.name) for city in cities]

# فلتر الراوندات المتعدد
class MultiRoundFilter(MultiSelectFilter):
    title = "الراوند"
    parameter_name = "trip__round"

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category")
        if category_id:
            rounds = Round.objects.filter(category__id__in=category_id.split(','))
        else:
            rounds = Round.objects.all()
        return [(round.id, round.name) for round in rounds]

# فلتر أوقات العودة المتعدد
class MultiBackTimeFilter(MultiSelectFilter):
    title = 'وقت العودة'
    parameter_name = 'back_time'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category")
        qs = FormReservation.objects.all()
        if category_id:
            qs = qs.filter(category__id__in=category_id.split(','))
        times = qs.order_by('back_time').values_list('back_time', flat=True).distinct()
        return [(str(t), t.strftime("%H:%M")) for t in times if t]

# فلتر أوقات الوصول المتعدد
class MultiArrivalTimeFilter(MultiSelectFilter):
    title = 'وقت الوصول'
    parameter_name = 'arrival_time'

    def lookups(self, request, model_admin):
        category_id = request.GET.get("category")
        qs = FormReservation.objects.all()
        if category_id:
            qs = qs.filter(category__id__in=category_id.split(','))
        times = qs.order_by('arrival_time').values_list('arrival_time', flat=True).distinct()
        return [(str(t), t.strftime("%H:%M")) for t in times if t]

# فلتر نوع الرحلة
class MultiTripTypeFilter(MultiSelectFilter):
    title = 'نوع الرحلة'
    parameter_name = 'trip_type'

    def lookups(self, request, model_admin):
        return [
            ('ذهاب', 'ذهاب'),
            ('عودة', 'عودة'),
            ('ذهاب وعودة', 'ذهاب وعودة')
        ]

# فلتر الحالة
class MultiStatusFilter(MultiSelectFilter):
    title = 'الحالة'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('confirmed', 'تم التأكيد'),
            ('pending', 'قيد الانتظار'),
            ('cancelled', 'ملغى')
        ]
from django.contrib import admin
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponseRedirect
from .forms import SuggestionApplyForm
from .utils import get_optimized_route_with_eta # استيراد الدالة
GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY # استخدم مفتاحك

@admin.register(FormReservation)
class FormReservationAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'get_user_name',
        'going_city',
        'back_time',
        'arrival_time',
        'pickup_location',
        'return_city',
        'status',
        'get_category_name',
        'trip_type',
        'get_trip_date',
        'get_rounds',
        'get_created_at',
        'get_trip_name',
        'get_passenger_phone',
        'merchant_order_id',
        'transaction_number',
    )

    list_editable = ('pickup_location','status')
    
    # تعريف الفلاتر
    list_filter = ( 
        MultiStatusFilter,
        MultiCategoryFilter,
        MultiTripTypeFilter,
        MultiGoingCityFilter,
        MultiReturnCityFilter,
        MultiRoundFilter,
        MultiBackTimeFilter,
        MultiArrivalTimeFilter,
    )

    date_hierarchy = 'trip_date'

    search_fields = (
        'student_name',
        'passenger__name',
        'passenger__university_code',
        'pickup_location',
        'user__username',
    )

    list_select_related = ('passenger', 'category', 'trip', 'user')
    actions = ['assign_trip_to_selected_reservations' , 'analyze_route_for_selected']
    def analyze_route_for_selected(self, request, queryset):
        if not queryset.exists() or not queryset.first().category:
            self.message_user(request, "الرجاء اختيار حجوزات تابعة لجامعة محددة.", level='warning')
            return HttpResponseRedirect(request.get_full_path())
        
        request.session['selected_reservations_pks'] = list(queryset.values_list('pk', flat=True))
        
        url = reverse('admin:Anaconda_bus_APP_formreservation_route_analysis')
        return HttpResponseRedirect(url)

    analyze_route_for_selected.short_description = "تحليل وإنشاء خط السير للحجوزات المختارة"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'route-analysis/',
                self.admin_site.admin_view(self.route_analysis_view),
                name='Anaconda_bus_APP_formreservation_route_analysis'
            ),
        ]
        return custom_urls + urls

    def route_analysis_view(self, request):
        """
        دالة العرض (View) لصفحة تحليل خط السير (النسخة المصححة والنهائية).
        """
        queryset_pks = request.session.get('selected_reservations_pks', [])
        queryset = FormReservation.objects.filter(pk__in=queryset_pks)
        university_name = queryset.first().category.name if queryset.exists() else ""
        
        context = {
            'title': f'تحليل خط السير لجامعة {university_name}',
            'university_name': university_name,
            'google_maps_api_key': GOOGLE_MAPS_API_KEY,
        }

        # --- منطق التعديل ---
        if request.method == 'POST' and 'update_location' in request.POST:
            new_location = request.POST.get('new_location')
            booking_ids_str = request.POST.get('booking_ids', '')
            
            if new_location and booking_ids_str:
                booking_ids = [int(id) for id in booking_ids_str.split(',')]
                updated_count = FormReservation.objects.filter(id__in=booking_ids).update(going_pickup_location=new_location)
                self.message_user(request, f"تم تحديث {updated_count} حجز بنجاح. نقطة الركوب الجديدة هي '{new_location}'.", messages.SUCCESS)
            else:
                self.message_user(request, "حدث خطأ: لم يتم توفير الموقع الجديد أو معرّفات الحجوزات.", messages.ERROR)
            
            # إعادة تحميل الصفحة مع البيانات الأولية بعد التحديث
            initial_data = get_optimized_route_with_eta({}, queryset=queryset)
            context.update(initial_data)
            return render(request, 'admin/route_analysis_page.html', context)
        
        # --- منطق حساب المسار أو العرض الأولي ---
        if request.method == 'POST':
            # هذا الجزء يعمل عند الضغط على "حساب وعرض خط السير"
            analysis_result = get_optimized_route_with_eta(request.POST, queryset=None)
            context.update(analysis_result)
        else: # GET Request
            # هذا الجزء يعمل عند فتح الصفحة لأول مرة
            initial_data = get_optimized_route_with_eta({}, queryset=queryset)
            context.update(initial_data)

        return render(request, 'admin/route_analysis_page.html', context)

    def get_rounds(self, obj):
        if obj.city:
            rounds = Round.objects.filter(cities=obj.city).values_list("name", flat=True)
            if rounds.exists():
                return " / ".join(rounds)
        return "---"

    get_rounds.short_description = "الراوندات"
    get_rounds.admin_order_field = "trip__round__name"

    def get_back_time(self, obj):
        return obj.back_time.strftime("%I:%M %p") if obj.back_time else "---"
    get_back_time.short_description = "وقت العودة"
    get_back_time.admin_order_field = 'back_time'

    def get_user_name(self, obj):
        return obj.user.username if obj.user else "---"
    get_user_name.short_description = "اسم المستخدم"
    get_user_name.admin_order_field = 'user__username'

    def get_student_name(self, obj):
        return obj.student_name or (obj.passenger.name if obj.passenger else "---")
    get_student_name.short_description = "اسم الطالب"
    get_student_name.admin_order_field = 'student_name'

    def get_category_name(self, obj):
        return obj.category.name if obj.category else "---"
    get_category_name.short_description = "الجامعة"
    get_category_name.admin_order_field = 'category__name'

    def get_trip_date(self, obj):
        return obj.trip_date.strftime("%Y-%m-%d") if obj.trip_date else "---"
    get_trip_date.short_description = "تاريخ الرحلة"
    get_trip_date.admin_order_field = 'trip_date'

    def get_arrival_time(self, obj):
        return obj.arrival_time.strftime("%H:%M") if obj.arrival_time else "---"
    get_arrival_time.short_description = "وقت الوصول"
    get_arrival_time.admin_order_field = 'arrival_time'

    def get_created_at(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M") if obj.created_at else "---"
    get_created_at.short_description = "تاريخ الحجز"
    get_created_at.admin_order_field = 'created_at'

    def get_trip_name(self, obj):
        return obj.trip.trip_name if obj.trip else "---"
    get_trip_name.short_description = "الرحلة"
    get_trip_name.admin_order_field = 'trip__trip_name'

    def get_passenger_phone(self, obj):
        return obj.passenger.phone_number if obj.passenger else "---"
    get_passenger_phone.short_description = "هاتف الراكب"
    get_passenger_phone.admin_order_field = 'passenger__phone_number'

    def assign_trip_to_selected_reservations(self, request, queryset):
        from django.db.models import Q
        today = localdate()

        filtered_trips = Trip.objects.filter(
            is_active=True,
            is_old=False,
            date__gte=today
        ).select_related('bus', 'bus__category').order_by('date', 'start_time', 'trip_name')

        if 'apply' in request.POST:
            form = TripSelectForm(request.POST, trip_queryset=filtered_trips)
            if form.is_valid():
                trip = form.cleaned_data['trip']
                bus = trip.bus

                all_seats = list(Seat.objects.filter(bus=bus).order_by('seat_number'))

                reserved_booking_seats = Booking.objects.filter(Trip=trip).values_list('seats_reserved__id', flat=True)
                reserved_form_seats = FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list('seat__id', flat=True)

                reserved_seat_ids = set(reserved_booking_seats).union(set(reserved_form_seats))
                available_seats = [seat for seat in all_seats if seat.id not in reserved_seat_ids]

                num_passengers = queryset.count()
                if num_passengers > len(available_seats):
                    self.message_user(
                        request,
                        f"❌ عدد الركاب المختارين ({num_passengers}) أكبر من عدد الكراسي المتاحة ({len(available_seats)}) في الرحلة {trip.trip_name}",
                        level='error'
                    )
                    return redirect(request.get_full_path())

                success_count = 0
                for i, reservation in enumerate(queryset):
                    try:
                        reservation.trip = trip
                        reservation.seat = available_seats[i]
                        reservation.save()

                        self.send_confirmation_message(reservation, trip)
                        success_count += 1
                    except Exception as e:
                        self.message_user(request, f"خطأ في الحجز {reservation.id}: {str(e)}", level='error')

                self.message_user(request, f"✅ تم إضافة {success_count} حجز إلى الرحلة {trip.trip_name}")
                return redirect(request.get_full_path())

        else:
            form = TripSelectForm(trip_queryset=filtered_trips)

        return render(request, 'admin/assign_trip.html', {
            'reservations': queryset,
            'form': form,
            'title': 'إضافة رحلة للركاب المختارين'
        })

    def send_confirmation_message(self, reservation, trip):
        passenger = reservation.passenger
        if not passenger:
            raise ValueError("لا يوجد راكب مرتبط بهذا الحجز")

        phone_number = getattr(passenger, 'phone_number', None)
        passenger_name = getattr(passenger, 'name', '') or "الراكب"

        if not phone_number:
            raise ValueError("لا يوجد رقم هاتف مسجل للراكب")

        phone_number = str(phone_number).strip()
        if not phone_number.startswith("+"):
            phone_number = f"+20{phone_number.lstrip('0')}"

        message = (
            f"🚍 تأكيد الحجز\n\n"
            f"مرحبًا {passenger_name},\n"
            f"تم تحديث حجزك في الرحلة '{trip.trip_name}'\n"
            f"📅 التاريخ: {trip.date.strftime('%Y-%m-%d')}\n"
            f"⏰ الوقت: {trip.start_time.strftime('%H:%M')}\n"
            f"📍 مكان الركوب: {reservation.pickup_location}\n\n"
            f"📍 رقم السائق: {trip.bus.driver_number}\n\n"
            f"📍 نمر المركبه : {trip.bus.plate_number}\n\n"
            f"📍 هنا هتلاقي صوره الباص و بياناته:https://allen.allentravels.com/allen/bookings/\n\n"
            "نتمنى لك رحلة سعيدة!"
        )

        if reservation.category and reservation.category.id == 1 and reservation.trip_type == "عودة":
            message += (
                "\n\n📌 ملاحظة مهمة: المعاد اللي هتختاره هو معاد تقريبي للتحرك، "
                "وده علشان راحتك وما تفضلش واقف في الشمس أو الحر لحد ما الباص يكمل. "
                "بعد ما تختار المعاد، هنبعتلك رسالة تانية قبل التحرك على طول علشان تتحرك للبوابة اللي اخترتها، "
                "والباص هيوصلك لحد هناك. هدفنا إن رحلتك معانا تبقى أسهل وأريح 🚍✨"
            )

        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

        payload = {
            "token": API_TOKEN,
            "to": phone_number,
            "body": message
        }
        requests.post(URL, data=payload)



@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'start_time', 'back_time']
    list_filter = ['category']
    filter_horizontal = ['cities']
       
from django.contrib import admin
from .models import City, PickupLocation

from django.contrib import admin
from django.utils.html import format_html
from .models import City, PickupLocation, DropoffLocation, FormReservation


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'pickup_locations_count', 'dropoff_locations_count']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    list_editable = ['is_active']
    
    def pickup_locations_count(self, obj):
        count = obj.pickup_locations.count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{} نقطة ركوب</span>',
                count
            )
        return format_html('<span style="color: red;">لا توجد نقاط ركوب</span>')
    pickup_locations_count.short_description = 'نقاط الركوب'
    
    def dropoff_locations_count(self, obj):
        count = 1
        if count > 0:
            return format_html(
                '<span style="color: blue; font-weight: bold;">{} نقطة نزول</span>',
                count
            )
        return format_html('<span style="color: red;">لا توجد نقاط نزول</span>')
    dropoff_locations_count.short_description = 'نقاط النزول'


@admin.register(PickupLocation)
class PickupLocationAdmin(admin.ModelAdmin):
    list_display = ['city', 'locations_preview', 'is_active']
    list_filter = ['city', 'is_active', 'city__category']
    search_fields = ['city__name', 'name']
    list_editable = ['is_active']
    
    def locations_preview(self, obj):
        lines = obj.name.strip().splitlines()
        preview = lines[0][:50] if lines else "لا توجد نقاط"
        if len(lines) > 1:
            preview += f" ... (+{len(lines)-1} نقطة أخرى)"
        return preview
    locations_preview.short_description = 'معاينة النقاط'
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('city', 'is_active')
        }),
        ('نقاط الركوب', {
            'fields': ('name',),
            'description': 'اكتب كل نقطة ركوب في سطر منفصل'
        }),
    )

@admin.register(DropoffLocation)
class DropoffLocationAdmin(admin.ModelAdmin):
    list_display = ['category', 'trip_type', 'locations_preview', 'is_active']
    list_filter = ['category', 'trip_type', 'is_active']
    search_fields = ['name']
    list_editable = ['is_active']
    
    def locations_preview(self, obj):
        lines = obj.name.strip().splitlines()
        preview = lines[0][:50] if lines else "لا توجد نقاط"
        if len(lines) > 1:
            preview += f" ... (+{len(lines)-1} نقطة أخرى)"
        return preview
    locations_preview.short_description = 'معاينة النقاط'
    
    fieldsets = (
        ('المعلومات الأساسية', {
            'fields': ('category', 'trip_type', 'is_active')
        }),
        ('نقاط النزول', {
            'fields': ('name',),
            'description': 'اكتب كل نقطة نزول في سطر منفصل'
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')

from django.contrib import admin
from .models import BonusPoint

@admin.register(BonusPoint)
class BonusPointAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'value', 'created_at', 'used']
    list_filter = ['used', 'created_at']
    search_fields = ['user__username']


from django.contrib import admin
from .models import InstallmentPlan, Installment

@admin.register(InstallmentPlan)
class InstallmentPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "subscription", "number_of_installments", "interval_days")
    search_fields = ("name", "subscription__name")  # بحث بالاسم أو الاشتراك
    list_filter = ("subscription",)


@admin.register(Installment)
class InstallmentAdmin(admin.ModelAdmin):
    list_display = ("passenger", "plan", "amount", "due_date", "is_paid")
    list_filter = ("is_paid", "due_date", "plan")
    search_fields = ("passenger__name", "plan__name")
    date_hierarchy = "due_date"  # شريط زمني للتواريخ
# في ملف admin.py

from django.contrib import admin
from django.db.models import F
from .models import Trip, PickupLocation, DropoffLocation, LocationLink

# قم بتسجيل النموذج الجديد أولاً
# admin.site.register(LocationLink) # يمكنك استخدام هذا السطر أو الواجهة المخصصة أدناه

@admin.register(LocationLink)
class LocationLinkAdmin(admin.ModelAdmin):
    list_display = ('point_name', 'google_maps_link')
    search_fields = ('point_name',)
    list_editable = ('google_maps_link',) # لتسهيل التعديل السريع
    ordering = ('point_name',)

    def get_queryset(self, request):
        """
        هذه هي الوظيفة السحرية التي ستجمع كل النقاط من كل الأماكن
        وتضيفها إلى النموذج الوهمي LocationLink إذا لم تكن موجودة.
        """
        # 1. جمع النقاط من نموذج Trip (حقل route)
        all_trip_points = set()
        for trip in Trip.objects.exclude(route__isnull=True).exclude(route__exact=''):
            points = [p.strip() for p in trip.route.splitlines() if p.strip()]
            all_trip_points.update(points)

        # 2. جمع النقاط من نموذج PickupLocation (حقل name)
        all_form_pickup_points = set()
        for loc in PickupLocation.objects.exclude(name__isnull=True).exclude(name__exact=''):
            points = [p.strip() for p in loc.name.splitlines() if p.strip()]
            all_form_pickup_points.update(points)

        # 3. جمع النقاط من نموذج DropoffLocation (حقل name)
        all_form_dropoff_points = set()
        for loc in DropoffLocation.objects.exclude(name__isnull=True).exclude(name__exact=''):
            points = [p.strip() for p in loc.name.splitlines() if p.strip()]
            all_form_dropoff_points.update(points)

        # دمج كل النقاط في مجموعة واحدة لمنع التكرار
        all_points = all_trip_points.union(all_form_pickup_points).union(all_form_dropoff_points)

        # التأكد من أن كل نقطة لها سجل في قاعدة بيانات LocationLink
        existing_points = set(LocationLink.objects.values_list('point_name', flat=True))
        
        new_points_to_create = []
        for point_name in all_points:
            if point_name not in existing_points:
                new_points_to_create.append(LocationLink(point_name=point_name))
        
        # إنشاء السجلات الجديدة دفعة واحدة لتحسين الأداء
        if new_points_to_create:
            LocationLink.objects.bulk_create(new_points_to_create)

        # إرجاع كل الروابط الموجودة للعرض في الأدمن
        return super().get_queryset(request)

    def has_add_permission(self, request):
        # تعطيل زر "Add" لأن النقاط تضاف تلقائيًا
        return False
from django.contrib import admin
from .models import Advertisement

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("title",)


# Weekly Booking Admin Interface
@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    """إدارة الجداول الزمنية الأسبوعية"""
    list_display = ('category', 'day_of_week', 'trip_type', 'time', 'is_active')
    list_filter = ('category', 'day_of_week', 'trip_type', 'is_active')
    search_fields = ('category__name', 'day_of_week')
    list_editable = ('is_active',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(WeeklyBooking)
class WeeklyBookingAdmin(admin.ModelAdmin):
    """إدارة الحجوزات الأسبوعية"""
    list_display = (
        'passenger', 'category', 'get_departure_days_display', 
        'get_return_days_display', 'departure_time', 'return_time', 
        'pickup_location', 'is_active', 'created_at'
    )
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('passenger__name', 'passenger__university_code', 'category__name')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('passenger', 'category')
    
    def get_departure_days_display(self, obj):
        return obj.get_departure_days_display()
    get_departure_days_display.short_description = 'أيام الذهاب'
    
    def get_return_days_display(self, obj):
        return obj.get_return_days_display()
    get_return_days_display.short_description = 'أيام العودة'

