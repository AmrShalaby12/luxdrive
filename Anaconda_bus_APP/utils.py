# bus_app/utils.py
from django.conf import settings
import requests
from django.utils.timezone import now
from .models import Installment

INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

def send_whatsapp_message(phone_number, message):
    payload = {
        "token": API_TOKEN,
        "to": phone_number,
        "body": message
    }
    response = requests.post(URL, json=payload)
    return response.json()


def check_and_send_due_installments():
    today = now().date()
    due_installments = Installment.objects.filter(due_date=today, is_paid=False)

    for installment in due_installments:
        passenger = installment.passenger
        phone_number = passenger.phone  # لازم Passenger عنده حقل phone
        message = (
            f"🚨 تنبيه هام\n\n"
            f"عزيزي {passenger.name},\n"
            f"لديك قسط جديد مستحق اليوم بمبلغ {installment.amount} جنيه.\n"
            f"لديك 24 ساعة لإتمام الدفع، وإلا سيتم تطبيق رسوم إضافية أو إلغاء الاشتراك.\n\n"
            f"في حال وجود مشكلة، يرجى التواصل مع إدارة الشركة."
        )
        send_whatsapp_message(phone_number, message)
from datetime import datetime, timedelta
import re
from django.utils import timezone
from .models import Category, FormReservation, City

# تهيئة عميل Google Maps
from datetime import datetime, timedelta
import re
from django.utils import timezone
from .models import Category, FormReservation, City
# Anaconda_bus_APP/utils.py

from datetime import datetime, timedelta
import re
from django.utils import timezone
from .models import Category, FormReservation, City

# تهيئة عميل Google Maps
import secrets
from django.urls import reverse
from Anaconda_bus_APP.models import Booking

def generate_telegram_link(booking_id):
    """
    توليد رابط فريد لكل حجز يمكن للراكب الضغط عليه
    لربط حسابه على Telegram مع الحجز.
    """
    try:
        booking = Booking.objects.get(id=booking_id)

        # إذا لم يكن هناك رمز فريد للحجز مسبقًا، نصنعه
        if not booking.telegram_token:
            booking.telegram_token = secrets.token_urlsafe(32)
            booking.save()

        # إنشاء الرابط الكامل للبوت على شكل deep link
        # عند الضغط، يرسل للراكب /start مع التوكن الفريد
        bot_username = "AllenTravelAi_bot"  # غيّر الاسم حسب بوتك
        link = f"https://t.me/{bot_username}?start={booking.telegram_token}"
        return link
    except Booking.DoesNotExist:
        return None
def get_optimized_route_with_eta(form_data, queryset=None):
    """
    تحسب المسار الأمثل بناءً على بيانات الفورم، أو تجلب النقاط الأولية من الـ queryset.
    """
    # الحالة الأولى: جلب البيانات الأولية لعرضها في الفورم لأول مرة
    if queryset is not None and not form_data:
        points = {}
        for booking in queryset.select_related('passenger'):
            location = booking.going_pickup_location
            if location and location.strip() and location.strip() != "غير محددة":
                if location not in points:
                    points[location] = {'name': location, 'passengers': []}
                
                passenger_name = booking.student_name or (booking.passenger.name if booking.passenger else "---")
                if passenger_name not in points[location]['passengers']:
                    points[location]['passengers'].append(passenger_name)
        
        # تحويل قائمة الركاب إلى نص واحد
        for point in points.values():
            point['passengers'] = ", ".join(point['passengers'])

        return {"points": list(points.values())}

    # الحالة الثانية: حساب المسار بناءً على البيانات المرسلة من الفورم
    origin = form_data.get('origin')
    destination = form_data.get('destination')
    start_time_str = form_data.get('start_time', '06:00')
    
    # جمع كل النقاط الوسيطة من الفورم
    waypoints_names = [val for key, val in form_data.items() if key.startswith('point-') and val.strip()]

    # إعادة إرسال النقاط المدخلة للاحتفاظ بها في الفورم عند حدوث خطأ أو نجاح
    # سنحتاج إلى إعادة جلب الركاب إذا أردنا عرضهم مرة أخرى
    # للتبسيط، سنعيد فقط أسماء النقاط
    points_for_form = [{'name': name} for name in waypoints_names]

    if not origin or not destination:
        return {
            "error": "يجب تحديد نقطة الانطلاق والوجهة النهائية.",
            "points": points_for_form,
            "origin_point": origin,
            "destination_point": destination,
        }

    try:
        directions_result = gmaps.directions(
            origin=origin,
            destination=destination,
            waypoints=waypoints_names,
            optimize_waypoints=True,
            mode="driving",
            departure_time=datetime.now()
        )

        if not directions_result:
            raise ValueError("لم تتمكن Google Maps من حساب المسار. تأكد من صحة أسماء المواقع.")

        # --- بناء النتائج ---
        main_route = directions_result[0]
        encoded_polyline = main_route['overview_polyline']['points']
        
        detailed_steps = []
        current_time = datetime.strptime(start_time_str, "%H:%M")

        # إضافة نقطة البداية
        detailed_steps.append({
            "point_name": main_route['legs'][0]['start_address'].split(',')[0],
            "arrival_time": current_time.strftime('%I:%M %p'),
            "duration_to_next": "---", "distance_to_next": "---", "avg_speed": "---"
        })

        # المرور على كل جزء من الرحلة
        for leg in main_route['legs']:
            duration_sec = leg['duration']['value']
            arrival_at_next_point = current_time + timedelta(seconds=duration_sec)
            avg_speed_kmh = (leg['distance']['value'] / 1000) / (duration_sec / 3600) if duration_sec > 0 else 0
            
            detailed_steps.append({
                "point_name": leg['end_address'].split(',')[0],
                "arrival_time": arrival_at_next_point.strftime('%I:%M %p'),
                "duration_to_next": leg['duration']['text'],
                "distance_to_next": leg['distance']['text'],
                "avg_speed": f"{avg_speed_kmh:.2f}"
            })
            current_time = arrival_at_next_point
        
        return {
            "encoded_polyline": encoded_polyline,
            "details": detailed_steps,
            "points": points_for_form,
            "origin_point": origin,
            "destination_point": destination,
        }

    except Exception as e:
        return {
            "error": f"حدث خطأ: {str(e)}",
            "points": points_for_form,
            "origin_point": origin,
            "destination_point": destination,
        }
# Anaconda_bus_APP/utils.py

# ... (كل الكود السابق في الملف يبقى كما هو) ...

def format_number(number):
    """تنسيق رقم الهاتف لإرساله للواتساب"""
    number = str(number).replace(" ", "").replace("-", "")
    if not number.startswith("+"):
        # لو الرقم مصري ولم يبدأ ب +2
        if number.startswith("0"):
            number = "+2" + number[1:]
    return number

def get_route_plan_for_trip(trip):
    """
    تُنشئ خطة سير مُقترحة لرحلة معينة بناءً على حجوزاتها.
    ترتب النقاط حسب عدد الركاب وتجمعهم حسب المدينة.
    """
    if not trip:
        return {}

    # جلب كل الحجوزات المرتبطة بالرحلة
    form_bookings = FormReservation.objects.filter(trip=trip)
    
    # قاموس لتجميع النقاط والركاب
    # الهيكل: {'اسم المدينة': {'اسم النقطة': عدد الركاب}}
    city_points = {}

    for booking in form_bookings:
        city_name = booking.going_city.name if booking.going_city else "مدينة غير محددة"
        point_name = booking.going_pickup_location
        
        if not point_name or point_name == "غير محددة":
            continue

        # إنشاء القواميس الداخلية إذا لم تكن موجودة
        if city_name not in city_points:
            city_points[city_name] = {}
        
        if point_name not in city_points[city_name]:
            city_points[city_name][point_name] = 0
        
        # زيادة عدد الركاب لهذه النقطة
        city_points[city_name][point_name] += 1

    # تحويل القاموس إلى قائمة مُرتبة للعرض في القالب
    # سيتم ترتيب المدن أبجدياً، والنقاط داخل كل مدينة حسب عدد الركاب (من الأكثر للأقل)
    sorted_route_plan = []
    for city, points in sorted(city_points.items()):
        sorted_points = sorted(points.items(), key=lambda item: item[1], reverse=True)
        sorted_route_plan.append({
            'city': city,
            'points': sorted_points # قائمة من (اسم النقطة, عدد الركاب)
        })

    return sorted_route_plan
# Anaconda_bus_APP/utils.py

import requests
from .models import FormReservation, Booking # تأكد من وجود هذه الاستيرادات

# ... (باقي الدوال في الملف) ...

def send_renewal_notification(passenger, new_trip,  booking_type=None):
    """
    ترسل رسالة واتساب للراكب لإعلامه بتجديد الرحلة وطلب التأكيد.
    """
    if not passenger or not getattr(passenger, 'phone_number', None):
        return False, "الراكب غير موجود أو لا يملك رقم هاتف."

    # --- 1. تجهيز بيانات الرسالة ---
    passenger_name = getattr(passenger, 'name', 'عميلنا العزيز')
    phone_number = str(passenger.phone_number).strip()
    
    # تنظيف رقم الهاتف (نفس المنطق الذي تستخدمه)
    if not phone_number.startswith("+"):
        phone_number = f"+20{phone_number.lstrip('0')}"

    # إنشاء رابط مباشر للرحلة الجديدة
    # تأكد من أن هذا هو نمط الرابط الصحيح في موقعك
    booking_url = f"https://allen.allentravels.com/allen/book/{new_trip.id}/" 

    message_body = (
        f"🚍 تنبيه هام بشأن رحلتك!\n\n"
        f"مرحباً {passenger_name},\n"
        f"تم تجديد رحلتك السابقة وفتح الحجز لرحلة جديدة بتاريخ اليوم: '{new_trip.trip_name}'.\n\n"
        f"⚠️ **لتأكيد مكانك في الرحلة الجديدة، يرجى الدخول على الرابط التالي فوراً:**\n"
        f"🔗 {booking_url}\n\n"
        f"**ملاحظة:** الحجوزات غير المؤكدة قد تعتبر ملغاة لإتاحة الفرصة لركاب آخرين. بادر بالتأكيد الآن!"
     )

    # --- 2. بيانات API الواتساب ---
    INSTANCE_ID = "instance105329"
    API_TOKEN = settings.ULTRAMSG_API_TOKEN
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    payload = {
        "token": API_TOKEN,
        "to": phone_number,
        "body": message_body
    }

    # --- 3. إرسال الطلب ---
    try:
        response = requests.post(URL, data=payload )
        if response.status_code == 200:
            return True, "تم الإرسال بنجاح."
        else:
            return False, f"فشل الإرسال. كود: {response.status_code}, رسالة: {response.text}"
    except Exception as e:
        return False, f"حدث خطأ استثناء أثناء الإرسال: {str(e)}"
