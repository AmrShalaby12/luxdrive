# comm 3 shalabydev
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.utils import timezone
from django.utils.timezone import now, localdate
from datetime import date, datetime, timedelta
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers import serialize
from itertools import groupby
from operator import attrgetter
from PIL import Image
import base64
import numpy as np
import json
import cv2
import logging
from io import BytesIO  # تم إضافة الاستيراد الصحيح هنا
from .models import (
    passenger, 
    Attendance, 
    Trip, 
    Booking, 
    Seat, 
    Route, 
    PaymentAccount, 
    Bus, 
    Category,
    WeeklySchedule,
    WeeklyBooking
)
from .forms import SignupForm, WeeklyBookingForm
import qrcode
from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import CustomUserLoginForm, CustomUserSignupForm

from django.contrib import messages

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib import messages

from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.models import User

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .forms import CustomUserLoginForm, CustomUserSignupForm  # التأكد من استيراد النماذج
import random, string
from .models import DiscountCode

def generate_unique_discount_code(length=10):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not DiscountCode.objects.filter(code=code).exists():
            return code


def _admin_notification_value(obj, field_names):
    for field_name in field_names:
        value = getattr(obj, field_name, None)
        if value not in (None, ""):
            return value
    return None


def _admin_notification_name(value):
    if not value:
        return ""

    get_full_name = getattr(value, "get_full_name", None)
    if callable(get_full_name):
        full_name = get_full_name()
        if full_name:
            return full_name

    for field_name in ("name", "student_name", "customer_name", "full_name", "username", "phone_number", "phone"):
        field_value = getattr(value, field_name, None)
        if field_value:
            return str(field_value)

    return str(value)


def _admin_notification_event(obj, title, kind):
    timestamp = _admin_notification_value(
        obj,
        ("created_at", "booking_date", "created_on", "created", "timestamp", "updated_at"),
    )
    passenger_obj = _admin_notification_value(obj, ("passenger", "user"))
    person_name = _admin_notification_value(
        obj,
        ("student_name", "customer_name", "full_name", "name"),
    ) or _admin_notification_name(passenger_obj)
    phone = _admin_notification_value(obj, ("phone_number", "phone", "mobile_number"))
    trip_obj = _admin_notification_value(obj, ("Trip", "trip", "weekly_schedule", "schedule", "category", "car", "subscription"))
    trip_name = _admin_notification_value(
        trip_obj,
        ("trip_name", "name", "title"),
    ) if trip_obj else ""
    location = _admin_notification_value(
        obj,
        (
            "selected_route",
            "pickup_location",
            "going_pickup_location",
            "return_pickup_location",
            "from_location",
            "to_location",
            "dropoff_location",
        ),
    )
    status = _admin_notification_value(obj, ("status", "trip_type", "payment_method"))

    parts = [person_name, phone, trip_name, location, status]
    body = " | ".join(str(part) for part in parts if part not in (None, ""))
    if not body:
        body = str(obj)

    try:
        admin_url = reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=[obj.pk],
        )
    except Exception:
        admin_url = "/allen/admin/"

    if hasattr(timestamp, "isoformat"):
        timestamp_value = timestamp.isoformat()
    elif timestamp:
        timestamp_value = str(timestamp)
    else:
        timestamp_value = ""

    return {
        "id": f"{obj._meta.label_lower}:{obj.pk}",
        "title": title,
        "body": body[:220],
        "kind": kind,
        "url": admin_url,
        "created_at": timestamp_value,
        "_sort_key": f"{timestamp_value}-{obj.pk:012d}",
    }


@login_required
def admin_booking_notifications(request):
    if not request.user.is_staff:
        return JsonResponse({"detail": "forbidden"}, status=403)

    from django.apps import apps

    model_configs = (
        ("Booking", "حجز رحلة جديد", "trip_booking"),
        ("FormReservation", "حجز فورم جديد", "form_reservation"),
        ("WeeklyBooking", "حجز أسبوعي جديد", "weekly_booking"),
        ("CarBooking", "حجز سيارة جديد", "car_booking"),
        ("SubscriptionBooking", "حجز اشتراك جديد", "subscription_booking"),
        ("FormBooking", "حجز فورم سريع جديد", "form_booking"),
    )
    events = []

    for model_name, title, kind in model_configs:
        try:
            model = apps.get_model("Anaconda_bus_APP", model_name)
        except LookupError:
            continue

        for obj in model.objects.order_by("-pk")[:8]:
            events.append(_admin_notification_event(obj, title, kind))

    events.sort(key=lambda item: item["_sort_key"], reverse=True)
    events = events[:30]
    for event in events:
        event.pop("_sort_key", None)

    return JsonResponse(
        {
            "events": events,
            "server_time": timezone.now().isoformat(),
        },
        json_dumps_params={"ensure_ascii": False},
    )

def new_login_signup_view(request):
    login_form = CustomUserLoginForm(data=request.POST or None)
    signup_form = CustomUserSignupForm(data=request.POST or None)

    if request.method == "POST":
        if "login_submit" in request.POST:
            if login_form.is_valid():
                username = login_form.cleaned_data['username']
                password = login_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user:
                    login(request, user)
                    messages.success(request, "تم تسجيل الدخول بنجاح!")
                    return redirect('my_buses')
                else:
                    messages.error(request, "بيانات تسجيل الدخول غير صحيحة.")
        
        elif "signup_submit" in request.POST:
            if signup_form.is_valid():
                signup_form.save()
                messages.success(request, "تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول.")
                return redirect('new_login')
            else:
                messages.error(request, "تأكد من صحة البيانات. راجع الأخطاء الموضحة بالأسفل.")

    return render(request, 'new_login_signup.html', {
        'login_form': login_form,
        'signup_form': signup_form,
    })


from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import CustomUser

# def custom_login_view(request):
#     if request.method == 'POST':
#         phone_number = request.POST['phone_number']
#         password = request.POST['password']
#         try:
#             user = CustomUser.objects.get(phone_number=phone_number)
#             user = authenticate(request, username=user.username, password=password)
#             if user is not None:
#                 login(request, user)
#                 return redirect('home')
#         except CustomUser.DoesNotExist:
#             pass  # يمكنك إضافة رسالة خطأ هنا

#     return render(request, 'login.html')

# إعداد اللوجر
logger = logging.getLogger(__name__)


# from datetime import date
# def schedule_list(request):
#     trip_id = Trip.objects.all()
#     return render(request, 'index.html', {'schedules': trip_id})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import Trip, Seat, Booking, PaymentAccount, passenger

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from .models import Trip, Seat, passenger, Booking, PaymentAccount  # تعديل الاسم إلى passenger

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from .models import Trip, Seat, passenger, Booking, PaymentAccount  # تعديل الاسم إلى passenger


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from .models import Trip, Seat, Booking, passenger, PaymentAccount
import requests

def send_whatsapp_confirmation(passenger, trip, seats):
    import requests
    INSTANCE_ID = "instance105329"  
    API_TOKEN = settings.ULTRAMSG_API_TOKEN  
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    # رابط صفحة الحجوزات
    bookings_url = "https://allen.allentravels.com/allen/bookings/"

    # استخراج أرقام الكراسي من الكائنات
    seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])

    message = f"""
    🚍 تأكيد الحجز 🚍
    ✅ {passenger.name}، تم تأكيد حجزك بنجاح.
    🚌 الرحلة: {trip.trip_name}
    📅 التاريخ: {trip.date.strftime('%Y-%m-%d')}
    ⏰ الوقت: {trip.start_time.strftime('%I:%M %p')}
    💺 أرقام المقاعد: {seat_numbers}
    🔗 لمزيد من التفاصيل و الحصول علي صوره الباص : {bookings_url}

    نشكرك على استخدام خدماتنا ونتمنى لك رحلة سعيدة!
    Allen_Ai_model
    """

    payload = {
        "token": API_TOKEN,
        "to": passenger.phone_number,
        "body": message.strip(),
    }
    requests.post(URL, data=payload)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from .models import Trip, Seat, Booking, passenger, PaymentAccount
from datetime import timedelta
from django.utils import timezone
from .models import BonusPoint
# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import Trip, Seat, Booking, passenger, BonusPoint, PaymentAccount
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from datetime import timedelta
from django.utils import timezone

# Assuming these models are defined elsewhere in your project
from .models import Trip, Seat, Booking, FormReservation, PaymentAccount, BonusPoint, passenger 
from django.db.models import F

@login_required
def book_seat(request, schedule_id):
    trip = get_object_or_404(Trip, id=schedule_id)

    try:
        student = passenger.objects.get(user=request.user)
    except passenger.DoesNotExist:
        messages.error(request, "بيانات الطالب غير موجودة.")
        return redirect("register_student")

    payment_accounts = PaymentAccount.objects.values(
        "id", "account_name", "account_number", "additional_info"
    )

    valid_points = BonusPoint.objects.filter(
        user=request.user, used=False, created_at__gte=timezone.now() - timedelta(days=7)
    )
    total_discount = sum([p.value for p in valid_points])

    # Check for remaining trips for subscription bypass
    has_subscription = student.remaining_rides > 0

    # Check for existing booking before rendering the page
    if trip.trip_type != "round_differentdays":
        if Booking.objects.filter(Trip=trip, user=request.user).exists():
            messages.info(request, "ℹ️ لقد قمت بالفعل بحجز مقعد في هذه الرحلة.")
            return redirect("user_bookings")
    else:
        # For round trips, check both departure and return trips
        if Booking.objects.filter(Trip=trip.related_departure_trip, user=request.user).exists() or \
           Booking.objects.filter(Trip=trip.related_return_trip, user=request.user).exists():
            messages.info(request, "ℹ️ لقد قمت بالفعل بحجز مقعد في هذه الرحلة (ذهاب أو عودة).")
            return redirect("user_bookings")

    # حالة الرحلة ذهاب وعودة في أيام مختلفة
    if (
        trip.trip_type == "round_differentdays"
        and trip.related_departure_trip
        and trip.related_return_trip
    ):
        departure_trip = trip.related_departure_trip
        return_trip = trip.related_return_trip

        departure_seats = Seat.objects.filter(bus=departure_trip.bus).order_by(
            "seat_number"
        )
        return_seats = Seat.objects.filter(bus=return_trip.bus).order_by(
            "seat_number"
        )

        # اجمع كل الكراسي المحجوزة من Booking و FormReservation
        reserved_departure_booking = Booking.objects.filter(Trip=departure_trip).values_list(
            "seats_reserved__id", flat=True
        )
        reserved_departure_form = FormReservation.objects.filter(
            trip=departure_trip
        ).exclude(seat__isnull=True).values_list("seat__id", flat=True)
        reserved_departure = set(reserved_departure_booking).union(
            set(reserved_departure_form)
        )

        reserved_return_booking = Booking.objects.filter(Trip=return_trip).values_list(
            "seats_reserved__id", flat=True
        )
        reserved_return_form = FormReservation.objects.filter(
            trip=return_trip
        ).exclude(seat__isnull=True).values_list("seat__id", flat=True)
        reserved_return = set(reserved_return_booking).union(
            set(reserved_return_form)
        )

        if request.method == "POST":
            selected_route = request.POST.get("selected_route")
            return_selected_route = request.POST.get("return_selected_route")
            
            # Get seats count from form
            seats_count = int(request.POST.get("seats_count", 1))

            if has_subscription:
                payment_method = "subscription"
                transaction_number = None
                mobile_number = None
                transaction_image = None
            else:
                payment_method = request.POST.get("payment_method")
                transaction_number = (
                    request.POST.get("transaction_number")
                    if payment_method == "online"
                    else None
                )
                mobile_number = (
                    request.POST.get("mobile_number")
                    if payment_method == "online"
                    else None
                )
                transaction_image = (
                    request.FILES.get("transaction_image")
                    if payment_method == "online"
                    else None
                )

            try:
                # Get available seats automatically
                available_departure = [s for s in departure_seats if s.id not in reserved_departure]
                available_return = [s for s in return_seats if s.id not in reserved_return]
                
                # Select random seats based on count
                if len(available_departure) < seats_count or len(available_return) < seats_count:
                    messages.error(request, "❌ عدد المقاعد المطلوبة غير متاح.")
                    return redirect(request.path)
                
                import random
                selected_departure_seats = random.sample(available_departure, seats_count)
                selected_return_seats = random.sample(available_return, seats_count)

                # حجز الذهاب
                booking_departure = Booking.objects.create(
                    Trip=departure_trip,
                    departure_trip=departure_trip,
                    return_trip=return_trip,
                    passenger=student,
                    user=request.user,
                    payment_method=payment_method,
                    trip_type="round_differentdays",
                    selected_route=selected_route,
                    transaction_number=transaction_number,
                    mobile_number=mobile_number,
                    transaction_image=transaction_image,
                )
                for seat in selected_departure_seats:
                    booking_departure.seats_reserved.add(seat)

                # حجز العودة
                booking_return = Booking.objects.create(
                    Trip=return_trip,
                    departure_trip=departure_trip,
                    return_trip=return_trip,
                    passenger=student,
                    user=request.user,
                    payment_method=payment_method,
                    trip_type="round_differentdays",
                    selected_route=selected_route,
                    transaction_number=transaction_number,
                    mobile_number=mobile_number,
                    transaction_image=transaction_image,
                    return_selected_route=return_selected_route,
                )
                for seat in selected_return_seats:
                    booking_return.seats_reserved.add(seat)

                valid_points.update(used=True)
                BonusPoint.objects.create(user=request.user, points=300, value=50.00)

                if has_subscription:
                    # ✅ استخدام F() expression لتجنب مشكلة setter
                    passenger.objects.filter(id=student.id).update(
                        remaining_rides=F('remaining_rides') - 1
                    )
                    messages.success(request, "✅ تم الحجز بنجاح عبر الاشتراك.")
                else:
                    messages.success(
                        request,
                        f"✅ تم الحجز بنجاح لرحلتي الذهاب والعودة. تم خصم {total_discount} جنيه باستخدام النقاط.",
                    )
                return redirect("success_page")

            except Exception as e:
                messages.error(request, f"❌ فشل الحجز: {e}")

        return render(
            request,
            "booking_form.html",
            {
                "trip": trip,
                "departure_trip": departure_trip,
                "return_trip": return_trip,
                "departure_seats": departure_seats,
                "return_seats": return_seats,
                "reserved_departure_seats": reserved_departure,
                "reserved_return_seats": reserved_return,
                "payment_accounts": payment_accounts,
                "discount": total_discount,
                "departure_seat_price": departure_trip.departure_seat_price,
                "return_seat_price": return_trip.return_seat_price,
                "routes": departure_trip.route.splitlines(),
                "return_routes": return_trip.route.splitlines(),
                "has_subscription": has_subscription,
                "category_id": departure_trip.bus.category.id if departure_trip.bus.category else 1,
                "student": student.category.name == "student" if hasattr(student, 'category') else False,
            },
        )

    # الرحلات العادية
    seats = Seat.objects.filter(bus=trip.bus).order_by("seat_number")

    # اجمع كل الكراسي المحجوزة من Booking و FormReservation
    reserved_booking = Booking.objects.filter(Trip=trip).values_list(
        "seats_reserved__id", flat=True
    )
    reserved_form = FormReservation.objects.filter(trip=trip).exclude(
        seat__isnull=True
    ).values_list("seat__id", flat=True)
    reserved_seats = set(reserved_booking).union(set(reserved_form))

    routes = trip.route.splitlines()

    if request.method == "POST":
        trip_type = request.POST.get("trip_type")
        selected_route = request.POST.get("selected_route")
        
        # Get seats count from form
        seats_count = int(request.POST.get("seats_count", 1))

        if has_subscription:
            payment_method = "subscription"
            transaction_number = None
            mobile_number = None
            transaction_image = None
        else:
            payment_method = request.POST.get("payment_method")
            transaction_number = (
                request.POST.get("transaction_number")
                if payment_method == "online"
                else None
            )
            mobile_number = (
                request.POST.get("mobile_number")
                if payment_method == "online"
                else None
            )
            transaction_image = (
                request.FILES.get("transaction_image")
                if payment_method == "online"
                else None
            )

        # Check for cash payment for students
        if student and payment_method == "cash" and seats_count > 1:
            # Check if student category
            is_student = hasattr(student, 'category') and student.category.name == "student"
            if is_student:
                messages.error(request, "❌ لا يمكنك حجز أكثر من مقعد واحد عند الدفع نقداً.")
                return redirect(request.path)

        try:
            # Get available seats automatically
            available_seats = [s for s in seats if s.id not in reserved_seats]
            
            # Select random seats based on count
            if len(available_seats) < seats_count:
                messages.error(request, "❌ عدد المقاعد المطلوبة غير متاح.")
                return redirect(request.path)
            
            import random
            selected_seats_obj = random.sample(available_seats, seats_count)

            booking = Booking.objects.create(
                Trip=trip,
                passenger=student,
                user=request.user,
                payment_method=payment_method,
                trip_type=trip_type,
                selected_route=selected_route,
                transaction_number=transaction_number,
                mobile_number=mobile_number,
                transaction_image=transaction_image,
            )
            for seat in selected_seats_obj:
                booking.seats_reserved.add(seat)
            
            send_whatsapp_confirmation(student, trip, booking.seats_reserved.all())

            valid_points.update(used=True)
            BonusPoint.objects.create(user=request.user, points=300, value=50.00)

            if has_subscription:
                # ✅ استخدام F() expression لتجنب مشكلة setter
                passenger.objects.filter(id=student.id).update(
                    remaining_rides=F('remaining_rides') - 1
                )
                messages.success(request, "✅ تم الحجز بنجاح عبر الاشتراك.")
            else:
                messages.success(
                    request,
                    f"✅ تم الحجز. تم خصم {total_discount} جنيه باستخدام النقاط.",
                )
            return redirect("success_page")

        except Exception as e:
            messages.error(request, f"❌ فشل الحجز: {e}")

    return render(
        request,
        "booking_form.html",
        {
            "trip": trip,
            "seats": seats,
            "routes": routes,
            "reserved_seats": reserved_seats,
            "payment_accounts": payment_accounts,
            "discount": total_discount,
            "category_id": trip.bus.category.id if trip.bus.category else 1,
            "has_subscription": has_subscription,
            "student": student.category.name == "student" if hasattr(student, 'category') else False,
        },
    )

@login_required
def select_seat(request, reservation_id):
    reservation = get_object_or_404(FormReservation, id=reservation_id, user=request.user)

    if reservation.seat:
        messages.info(request, "لقد قمت باختيار مقعد بالفعل.")
        return redirect('home')  # غيرها للمكان المناسب

    trip = reservation.trip
    seats = Seat.objects.filter(bus=trip.bus).order_by('seat_number')

    # الكراسي المحجوزة
    reserved_from_booking = Booking.objects.filter(Trip=trip).values_list('seats_reserved__id', flat=True)
    reserved_from_form = FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list('seat_id', flat=True)
    reserved_seats = set(reserved_from_booking).union(set(reserved_from_form))

    if request.method == "POST":
        selected_seat_id = request.POST.get("selected_seat")
        if selected_seat_id:
            seat = Seat.objects.get(id=selected_seat_id)
            if seat.id in reserved_seats:
                messages.error(request, "هذا المقعد تم حجزه بالفعل.")
            else:
                reservation.seat = seat
                reservation.save()
                messages.success(request, "✅ تم حجز المقعد بنجاح.")
                return redirect("home")  # غيره حسب ما تحب

    return render(request, "select_seat.html", {
        "reservation": reservation,
        "trip": trip,
        "seats": seats,
        "reserved_seats": reserved_seats,
    })

def register_student(request):
    universities = Category.objects.all()  # استخراج الجامعات المسجلة

    if request.method == 'POST':
        university_code = request.POST.get('university_code')
        name = request.POST.get('name')
        university_name = request.POST.get('university')  # اسم الجامعة من المستخدم

        # التحقق من صحة الجامعة المختارة
        try:
            university = Category.objects.get(name=university_name)
        except Category.DoesNotExist:
            messages.error(request, "الجامعة المختارة غير موجودة.")
            return redirect('register_student')

        # التحقق من أن الكود الجامعي غير مسجل مسبقًا
        if passenger.objects.filter(university_code=university_code).exists():
            messages.error(request, "الكود الجامعي موجود بالفعل.")
            return redirect('register_student')

        # إنشاء الطالب الجديد
        passenger.objects.create(
            university_code=university_code,
            name=name,
            category=university,  # تمرير الكائن بدلاً من النص
            subscription_duration=0  # القيمة الافتراضية
        )
        messages.success(request, "تم تسجيل الطالب بنجاح!")
        return redirect('register_student')  # إعادة التوجيه إلى نفس الصفحة

    return render(request, 'register_student.html', {'universities': universities})
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render
from datetime import datetime
from .models import FormReservation  # تأكد من استيراد الموديل الصحيح

@login_required
def user_bookings(request):
    """
    عرض جميع حجوزات المستخدم (الرحلات والفورم)، مع تقسيمها إلى فئات واضحة.
    """
    # أولاً، التأكد من أن المستخدم لديه ملف "passenger" مرتبط به
    passenger = getattr(request.user, 'passenger', None)
    if not passenger:
        # إذا لم يكن المستخدم راكباً، نعرض صفحة فارغة مع رسالة توضيحية
        return render(request, 'user_bookings.html', {
            'active_bookings': [],
            'pending_form_bookings': [],
            'completed_form_bookings': [],
            'completed_bookings': [],
        })

    today = timezone.now().date()

    # تحديث حالة الحجوزات القديمة تلقائياً (للحجوزات العادية)
    Booking.objects.filter(
        passenger=passenger,
        status='active',
        Trip__date__lt=today
    ).update(status='completed')

    # 1. حجوزات الرحلات النشطة (الحجوزات العادية التي لم تنتهِ بعد)
    active_bookings = Booking.objects.filter(
        passenger=passenger,
        status='active'
    ).select_related('Trip', 'Trip__bus').prefetch_related('seats_reserved').order_by('Trip__date', 'Trip__start_time')

    # 2. حجوزات الفورم المعلقة (التي لم يتم ربطها برحلة بعد)
    # تظهر فقط الحجوزات المؤكدة (مدفوعة أو كاش أو اشتراك) وتاريخها اليوم أو في المستقبل
    pending_form_bookings = FormReservation.objects.filter(
        passenger=passenger,
        trip__isnull=True,  # الشرط الأساسي: لم تُربط برحلة
        trip_date__gte=today,
        status__in=['confirmed', 'cash', 'subscription']
    ).select_related('category').order_by('trip_date')

    # 3. حجوزات الفورم المكتملة (التي تم ربطها برحلة)
    # تظهر الحجوزات التي رُبطت برحلة وتاريخها اليوم أو في المستقبل
    completed_form_bookings = FormReservation.objects.filter(
        passenger=passenger,
        trip__isnull=False, # الشرط الأساسي: رُبطت برحلة
        trip__date__gte=today
    ).select_related('trip', 'trip__bus', 'seat', 'category').order_by('trip__date', 'trip__start_time')
    
    # 4. الحجوزات المنتهية (اختياري: يمكنك عرضها في قسم منفصل إذا أردت)
    completed_bookings = Booking.objects.filter(
        passenger=passenger,
        status='completed'
    ).order_by('-Trip__date')

    context = {
        'active_bookings': active_bookings,
        'pending_form_bookings': pending_form_bookings,
        'completed_form_bookings': completed_form_bookings,
        'completed_bookings': completed_bookings, # قسم الحجوزات المنتهية
        'passenger': passenger,
    }
    return render(request, 'user_bookings.html', context)



from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Booking

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Booking
def send_whatsapp_cancilng(passenger, trip, seat):
    INSTANCE_ID = "instance105329"  
    API_TOKEN = settings.ULTRAMSG_API_TOKEN  
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    message = f"""
    🚍 الغاء الحجز 🚍
      {passenger.name}، تم الغاء حجزك بنجاح.
    هل عندك اي مشكله ؟ نحن هنا بالخدمه!  
    Allen_Ai_model
    """

    payload = {
        "token": API_TOKEN,
        "to": passenger.phone_number,
        "body": message.strip(),
    }
    requests.post(URL, data=payload)

# @login_required
# def cancel_booking(request, booking_id):
#     booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
#     if booking.status == 'completed':
#         messages.error(request, "لا يمكن إلغاء الحجز بعد إتمام المعاملة.")
#         return redirect('user_bookings')
    
#     # حذف جميع البيانات المرتبطة بالحجز
#     booking.seats_reserved.all().delete()  # حذف المقاعد المحجوزة
#     booking.delete()  # حذف الحجز بالكامل
    
#     messages.success(request, "✅ تم إلغاء الحجز نهائيًا وحذف جميع البيانات المرتبطة به.")
#     return redirect('user_bookings')

from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

from django.http import HttpResponseRedirect
# views.py

from django.shortcuts import get_object_or_404, redirect # استبدل HttpResponseRedirect بـ redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Booking, Seat # تأكد من استيراد Seat

@login_required
def cancel_booking(request, booking_id):
    # استخدم get_object_or_404 ليكون الكود أنظف وأكثر أماناً
    # يتحقق تلقائياً من وجود الحجز ومن أن المستخدم الحالي هو صاحب الحجز
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status == 'completed':
        messages.error(request, "لا يمكن إلغاء الحجز بعد إتمام المعاملة.")
        return redirect('user_bookings') # استخدام redirect أفضل

    # --- الخطوة الأهم: تحرير المقاعد ---
    # نقوم بتحديث حالة كل المقاعد المرتبطة بهذا الحجز إلى "غير محجوزة"
    booking.seats_reserved.all().update(is_reserved=False)

    # --- الخطوة الثانية: حذف الحجز ---
    # الآن بعد أن تم تحرير المقاعد، يمكننا حذف الحجز بأمان
    booking_passenger = booking.passenger # نحتفظ بالبيانات قبل الحذف لإرسال الرسالة
    booking_trip = booking.Trip
    booking.delete()

    # --- الخطوة الثالثة: إرسال الإشعار ---
    # إرسال إشعار واتساب (اختياري)
    send_whatsapp_cancilng(booking_passenger, booking_trip, None)

    messages.success(request, "✅ تم إلغاء الحجز بنجاح وتحرير المقاعد.")
    
    # استخدام redirect أفضل لأنه يعتمد على اسم الـ URL وهو أكثر مرونة
    return redirect('user_bookings')
def search_routes(request):
    if request.method == "GET":
        from_location = request.GET.get('from_location')
        to_location = request.GET.get('to_location')
        date = request.GET.get('date')

        
        routes = Route.objects.filter(
            from_location__icontains=from_location,
            to_location__icontains=to_location,
            date=date
        )

        return render(request, 'search_results.html', {'routes': routes})
from django.shortcuts import render
from django.utils.timezone import now
from datetime import datetime
from django.core.exceptions import ValidationError
from .models import Trip, Bus, Category
from .models import passenger


from django.db.models import Case, When, Value, IntegerField
# @login_required
# login req in index 
from django.shortcuts import render
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Value, IntegerField
from django.utils.timezone import now
from datetime import datetime
from .models import Trip, Bus, Category, passenger
from django.shortcuts import render
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Value, IntegerField
from datetime import datetime
from .models import Trip, Bus, Category, destination  # ← تأكد أن الوجهة مستوردة
from .models import passenger  # ← حسب مكان موديل الراكب في مشروعك

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from django.db.models import Case, When, Value, IntegerField
from datetime import datetime
from .models import Trip, Bus, Category, destination, passenger

from django.contrib.auth.decorators import login_required
from .models import Advertisement
# لا تنس إضافة هذه الاستيرادات في أعلى ملف views.py إذا لم تكن موجودة
from django.db.models import Q, Case, When, Value, IntegerField
from django.utils.timezone import now
from datetime import datetime
from django.core.exceptions import ValidationError
# تأكد من استيراد الموديلات الخاصة بك بشكل صحيح
# from .models import Trip, Advertisement, passenger, Category, Bus, destination

def index(request):
    user_category_id = None
    user_type = None
    last_selected_route = None
    form_support_enabled = False
    user_passenger = None
    ads = Advertisement.objects.filter(is_active=True).order_by("-created_at")

    # قائمة الفئات التي ستعرض رحلات مجمعة
    target_categories = [2, 3, 6, 7]
    is_user_in_target_group = False

    # 1. التحقق من المستخدم وفئته
    if request.user.is_authenticated:
        try:
            user_passenger = request.user.passenger
            if user_passenger.category:
                user_category_id = user_passenger.category.id
            
            user_type = user_passenger.user_type
            remaining_rides = user_passenger.remaining_rides
            last_selected_route = user_passenger.last_selected_route

            if user_passenger.category and user_passenger.category.Form_support:
                form_support_enabled = True
            
            # التحقق إذا كانت فئة المستخدم ضمن المجموعة المستهدفة
            if user_category_id in target_categories:
                is_user_in_target_group = True

        except passenger.DoesNotExist:
            user_category_id = None
            user_type = None
            remaining_rides = 0
    else:
        remaining_rides = 0

    # --- استلام الفلاتر من طلب GET ---
    category_from_filter = request.GET.get('Category')
    selected_departure_date = request.GET.get('departure_date', None)
    selected_return_date = request.GET.get('return_date', None)
    trip_type = request.GET.get('trip_type', None)
    start_time = request.GET.get('start_time', None)
    route = request.GET.get('route', None)
    selected_trip_name = request.GET.get('trip_name', None)
    selected_destination = request.GET.get('destination', None)
    arrival_time = request.GET.get('arrival_time', None)

    # --- بناء الاستعلام ---
    schedules = Trip.objects.select_related('bus', 'bus__category').filter(
        bus__is_active=True,
        is_active=True,
        date__gte=now().date()
    )

    # بناء قاموس الفلاتر
    filters = {}

    # 2. تطبيق منطق الفلترة الجديد للفئات (Categories)
    if is_user_in_target_group:
        # إذا كان المستخدم ينتمي للمجموعة، أظهر دائمًا رحلات كل الفئات في المجموعة
        filters['bus__category__id__in'] = target_categories
    elif category_from_filter:
        # إذا كان المستخدم عاديًا واختار فلترًا، استخدم الفلتر
        try:
            filters['bus__category__id'] = int(category_from_filter)
        except (ValueError, TypeError):
            pass # تجاهل الفلتر إذا كانت القيمة غير صالحة
    elif user_category_id:
        # إذا كان المستخدم عاديًا ولم يختر فلترًا، استخدم فئته الافتراضية
        filters['bus__category__id'] = user_category_id

    # (باقي الفلاتر تبقى كما هي)
    if arrival_time:
        try:
            arrival_time_obj = datetime.strptime(arrival_time, '%I:%M %p').time()
            filters['start_time__hour'] = arrival_time_obj.hour
            filters['start_time__minute'] = arrival_time_obj.minute
        except ValueError:
            pass

    if trip_type:
        filters['trip_type'] = trip_type
        # ... (باقي الشروط الخاصة بنوع الرحلة والتاريخ)

    if start_time:
        try:
            start_time_obj = datetime.strptime(start_time, '%I:%M %p').time()
            filters['start_time__hour'] = start_time_obj.hour
            filters['start_time__minute'] = start_time_obj.minute
        except ValueError:
            pass

    if route:
        filters['route__icontains'] = route

    if selected_destination:
        filters['end_destination__id'] = selected_destination

    # تطبيق الفلاتر على الاستعلام
    if filters:
        schedules = schedules.filter(**filters)

    # ترتيب حسب آخر مسار استخدمه المستخدم
    if last_selected_route:
        schedules = schedules.annotate(
            priority=Case(
                When(route__icontains=last_selected_route, then=Value(1)),
                default=Value(2),
                output_field=IntegerField()
            )
        ).order_by('priority', 'end_time')
    else:
        schedules = schedules.order_by('end_time')

    # --- البيانات للقوائم المنسدلة في القالب ---
    all_universities = Category.objects.all()
    # ... (باقي الكود الخاص بإعداد بيانات القالب يبقى كما هو)
    all_trip_types = [
        ('one_way', 'ذهاب فقط'),
        ('return', 'عودة فقط'),
        ('round_trip', 'ذهاب وعودة (في نفس اليوم)'),
        ('round_differentdays', 'ذهاب وعودة (في أيام مختلفة)'),
    ]
    all_arrival_times_qs = Trip.objects.filter(
        is_active=True, 
        date__gte=now().date()
    ).values_list('start_time', flat=True).distinct().order_by('start_time')
    formatted_arrival_times = sorted(list(set([time.strftime('%I:%M %p') for time in all_arrival_times_qs])))
    all_routes = Trip.objects.filter(is_active=True, date__gte=now().date()).values_list('route', flat=True).distinct()
    all_trip_names = Trip.objects.filter(is_active=True, date__gte=now().date()).values_list('trip_name', flat=True).distinct()
    all_destinations = destination.objects.all()
    buses_with_locations = Bus.objects.filter(location_url__isnull=False, is_active=True)

    # --- إرسال البيانات إلى القالب ---
    # تحديد القيمة التي ستظهر في حقل الفلتر
    display_category = category_from_filter if category_from_filter else user_category_id

    context = {
        'schedules': schedules,
        'ads': ads,
        'buses_with_locations': buses_with_locations,
        'all_universities': all_universities,
        'all_trip_types': all_trip_types,
        'all_arrival_times': formatted_arrival_times,
        'all_routes': all_routes,
        'all_trip_names': all_trip_names,
        'destinations': all_destinations,
        
        'selected_category': display_category,
        'selected_departure_date': selected_departure_date,
        'selected_return_date': selected_return_date,
        'trip_type': trip_type,
        'start_time': start_time,
        'arrival_time': arrival_time,
        'route': route,
        'selected_trip_name': selected_trip_name,
        'selected_destination': selected_destination,
        
        'user_type': user_type,
        'remaining_rides': remaining_rides,
        'form_support_enabled': form_support_enabled,
        'passenger': user_passenger,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY,
    }

    return render(request, 'index.html', context)


from .models import Category, FormReservation, City, User, PickupLocation, DropoffLocation, Round

from .forms import FormReservationForm
from .models import Category, FormReservation

from .models import FormReservation, Category
from .forms import FormReservationForm
from .models import FormReservation, Category, passenger  # استيراد الموديل بشكل صحيح

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Category, FormReservation
from .forms import FormReservationForm

from .models import City
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Category, City, PickupLocation
from .forms import FormReservationForm

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Category, Round, City, PickupLocation, FormReservation
from .forms import FormReservationForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import FormReservation, Round, City, PickupLocation, passenger, Trip
from .forms import FormReservationForm
from django.utils.timezone import now
from django import forms

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Category, City, PickupLocation, Round, FormReservation
from .forms import FormReservationForm
import datetime
# views.py (محدث: ربط الحجز بالدفع باستخدام توليد هاش يدوي)
import uuid
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, ROUND_HALF_UP
from django.http import JsonResponse
from urllib.parse import urlencode
from .models import FormReservation, City, Category
from .forms import FormReservationForm
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
# views.py (محدث: دعم الدفع النقدي أو الإلكتروني)
import uuid
import hmac
import hashlib
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, ROUND_HALF_UP
from django.http import JsonResponse
from urllib.parse import urlencode
from .models import FormReservation, City, Category
from .forms import FormReservationForm
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth.models import User
# views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP
import uuid
import hmac
import hashlib
from urllib.parse import urlencode

# تأكد من أن هذه الاستيرادات صحيحة في مشروعك
from .models import Category, FormReservation, City, User
from .forms import FormReservationForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal, ROUND_HALF_UP
import uuid
import hmac
import hashlib
from urllib.parse import urlencode

# تأكد من استيراد النماذج والفورمز الخاصة بك
from .models import Category, FormReservation, City
from .forms import FormReservationForm

# تأكد من أن هذه الاستيرادات صحيحة في مشروعك
from .models import Category, FormReservation, City, User, PickupLocation, DropoffLocation, Round
from .forms import FormReservationForm


@login_required
def form_reservation(request, category_id):
    category = get_object_or_404(Category, id=category_id, Form_support=True)
    if not category.Form_active:
        messages.error(request, "❌ هذا النموذج لا يقبل الحجوزات حالياً.")
        return redirect("index")

    if request.method == "POST":
        form = FormReservationForm(request.POST, user=request.user, category=category)

        if form.is_valid():
            try:
                trip_type = form.cleaned_data["trip_type"]
                reservation_data = {
                    'category_id': category.id,
                    'user_id': request.user.id,
                    'trip_date': str(form.cleaned_data['trip_date']),
                    'phone_number': form.cleaned_data.get('phone_number'),
                    'university_code': form.cleaned_data.get('university_code'),
                }

                if hasattr(request.user, "passenger"):
                    p = request.user.passenger
                    reservation_data.update({
                        'passenger_id': p.id,
                        'student_name': p.name,
                        'phone_number': p.phone_number,
                        'university_code': p.university_code,
                    })

                reservations = []

                if trip_type == "ذهاب":
                    reservations.append({
                        **reservation_data,
                        'trip_type': "ذهاب",
                        'arrival_time': str(form.cleaned_data['arrival_time']),
                        'going_city_id': request.POST.get("going_city_id"),
                        'going_pickup_location': request.POST.get("going_pickup_location"),
                        'going_dropoff_location': request.POST.get("going_dropoff_location"),
                        'pickup_location': request.POST.get("going_pickup_location"), # إضافة الحقل القديم
                    })

                elif trip_type == "عودة":
                    reservations.append({
                        **reservation_data,
                        'trip_type': "عودة",
                        'back_time': str(form.cleaned_data['back_time']),
                        'return_city_id': request.POST.get("return_city_id"),
                        'return_pickup_location': request.POST.get("return_pickup_location"),
                        'return_dropoff_location': request.POST.get("return_dropoff_location"),
                        'pickup_location': request.POST.get("return_pickup_location"), # إضافة الحقل القديم
                    })

                elif trip_type == "ذهاب وعودة":
                    reservations.append({
                        **reservation_data,
                        'trip_type': "ذهاب",
                        'arrival_time': str(form.cleaned_data['arrival_time']),
                        'going_city_id': request.POST.get("going_city_id"),
                        'going_pickup_location': request.POST.get("going_pickup_location"),
                        'going_dropoff_location': request.POST.get("going_dropoff_location"),
                        'pickup_location': request.POST.get("going_pickup_location"), # إضافة الحقل القديم
                    })
                    reservations.append({
                        **reservation_data,
                        'trip_type': "عودة",
                        'back_time': str(form.cleaned_data['back_time']),
                        'return_city_id': request.POST.get("return_city_id"),
                        'return_pickup_location': request.POST.get("return_pickup_location"),
                        'return_dropoff_location': request.POST.get("return_dropoff_location"),
                        'pickup_location': request.POST.get("return_pickup_location"), # إضافة الحقل القديم
                    })

                # --- السعر الأساسي ---
                # تحديد السعر من الكاتيجوري حسب نوع الرحلة
                trip_type = form.cleaned_data.get("trip_type")
                if trip_type == "ذهاب" or trip_type == "عودة":
                    base_price = category.one_way_price
                elif trip_type == "ذهاب وعودة":
                    base_price = category.round_trip_price
                else:
                    base_price = Decimal('0.00')
                final_price = (base_price * Decimal('1.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                # ========== حجز بالاشتراك ==========
                if "subscription_booking" in request.POST:
                    if hasattr(request.user, "passenger") and request.user.passenger.remaining_rides > 0:
                        passenger_instance = request.user.passenger
                        needed_rides = len(reservations)

                        if passenger_instance.remaining_rides >= needed_rides:
                            # passenger_instance.rides_used += needed_rides
                            # passenger_instance.save()

                            for res in reservations:
                                form_reservation = FormReservation.objects.create(
                                    category=Category.objects.get(id=res["category_id"]),
                                    user=User.objects.get(id=res["user_id"]),
                                    passenger_id=res.get("passenger_id"),
                                    student_name=res.get("student_name"),
                                    trip_date=res["trip_date"],
                                    trip_type=res["trip_type"],
                                    going_city_id=res.get("going_city_id"),
                                    return_city_id=res.get("return_city_id"),
                                    arrival_time=res.get("arrival_time"),
                                    back_time=res.get("back_time"),
                                    phone_number=res.get("phone_number"),
                                    university_code=res.get("university_code"),
                                    total_price=Decimal('0.00'),
                                    paid_amount=Decimal('0.00'),
                                    status="subscription",
                                    going_pickup_location=res.get('going_pickup_location'),
                                    going_dropoff_location=res.get('going_dropoff_location'),
                                    return_pickup_location=res.get('return_pickup_location'),
                                    return_dropoff_location=res.get('return_dropoff_location'),
                                    pickup_location=res.get('pickup_location'), # إضافة الحقل القديم
                                )
                                
                                # إرسال رسالة للبوت بحفظ الـ user_id
                                try:
                                    from telegram_bot.utils import send_telegram_user_notification
                                    send_telegram_user_notification(
                                        user_id=res["user_id"],
                                        reservation_id=form_reservation.id,
                                        student_name=res.get("student_name", "Unknown"),
                                        trip_type=res["trip_type"],
                                        trip_date=res["trip_date"]
                                    )
                                except Exception as e:
                                    print(f"Error sending Telegram notification: {e}")
                            
                            messages.success(request, "✅ تم الحجز باستخدام رصيد اشتراكك.")
                            return redirect("index")
                        else:
                            messages.error(request, "❌ رصيد الاشتراك غير كافي لهذه الرحلة.")
                            return redirect("index")
                    else:
                        messages.error(request, "❌ لا يوجد رصيد اشتراك لديك.")
                        return redirect("index")

                # ========== حجز كاش ==========
                if "cash_booking" in request.POST:
                    if not category.allow_cash_payment:
                        messages.error(request, "❌ هذه الجامعة لا تدعم الدفع نقداً.")
                        return redirect("index")

                    for res in reservations:
                        form_reservation = FormReservation.objects.create(
                            category=Category.objects.get(id=res["category_id"]),
                            user=User.objects.get(id=res["user_id"]),
                            passenger_id=res.get("passenger_id"),
                            student_name=res.get("student_name"),
                            trip_date=res["trip_date"],
                            trip_type=res["trip_type"],
                            going_city_id=res.get("going_city_id"),
                            return_city_id=res.get("return_city_id"),
                            arrival_time=res.get("arrival_time"),
                            back_time=res.get("back_time"),
                            phone_number=res.get("phone_number"),
                            university_code=res.get("university_code"),
                            total_price=final_price,
                            paid_amount=Decimal('0.00'),
                            status="cash",
                            going_pickup_location=res.get('going_pickup_location'),
                            going_dropoff_location=res.get('going_dropoff_location'),
                            return_pickup_location=res.get('return_pickup_location'),
                            return_dropoff_location=res.get('return_dropoff_location'),
                            pickup_location=res.get('pickup_location'), # إضافة الحقل القديم
                        )
                        
                        # إرسال رسالة للبوت بحفظ الـ user_id
                        try:
                            from telegram_bot.utils import send_telegram_user_notification
                            send_telegram_user_notification(
                                user_id=res["user_id"],
                                reservation_id=form_reservation.id,
                                student_name=res.get("student_name", "Unknown"),
                                trip_type=res["trip_type"],
                                trip_date=res["trip_date"]
                            )
                        except Exception as e:
                            print(f"Error sending Telegram notification: {e}")
                    messages.success(request, "✅ تم الحجز بنجاح كـنقداً")
                    return redirect("index")

                # ========== حجز أونلاين ==========
                merchant_order_id = str(uuid.uuid4())

                # نحجز في الداتابيز كـ pending على طول
                for res in reservations:
                    form_reservation = FormReservation.objects.create(
                        category=Category.objects.get(id=res["category_id"]),
                        user=User.objects.get(id=res["user_id"]),
                        passenger_id=res.get("passenger_id"),
                        student_name=res.get("student_name"),
                        trip_date=res["trip_date"],
                        trip_type=res["trip_type"],
                        going_city_id=res.get("going_city_id"),
                        return_city_id=res.get("return_city_id"),
                        arrival_time=res.get("arrival_time"),
                        back_time=res.get("back_time"),
                        phone_number=res.get("phone_number"),
                        university_code=res.get("university_code"),
                        total_price=final_price,
                        paid_amount=Decimal('0.00'),
                        status="pending",
                        merchant_order_id=merchant_order_id,
                        going_pickup_location=res.get('going_pickup_location'),
                        going_dropoff_location=res.get('going_dropoff_location'),
                        return_pickup_location=res.get('return_pickup_location'),
                        return_dropoff_location=res.get('return_dropoff_location'),
                        pickup_location=res.get('pickup_location'), # إضافة الحقل القديم
                    )
                    
                    # إرسال رسالة للبوت بحفظ الـ user_id
                    try:
                        from telegram_bot.utils import send_telegram_user_notification
                        send_telegram_user_notification(
                            user_id=res["user_id"],
                            reservation_id=form_reservation.id,
                            student_name=res.get("student_name", "Unknown"),
                            trip_type=res["trip_type"],
                            trip_date=res["trip_date"]
                        )
                    except Exception as e:
                        print(f"Error sending Telegram notification: {e}")

                # === Kashier Integration ===
                merchant_id = settings.KASHIER_ACCOUNT_KEY
                mode = settings.KASHIER_MODE
                amount_str = str(int(final_price))
                currency = 'EGP'

                def generateKashierOrderHash(order):
                    mid = merchant_id
                    amount = order['amount']
                    currency = order['currency']
                    orderId = order['merchantOrderId']
                    full_secret = settings.KASHIER_API_KEY
                    secret = full_secret.split('$')[-1]
                    path = f"/?payment={mid}.{orderId}.{amount}.{currency}"
                    return hmac.new(secret.encode('utf-8'), path.encode('utf-8'), hashlib.sha256).hexdigest()

                order_data = {
                    'amount': amount_str,
                    'currency': currency,
                    'merchantOrderId': merchant_order_id,
                }

                hash_signature = generateKashierOrderHash(order_data)

                params = {
                    'merchantId': merchant_id,
                    'orderId': merchant_order_id,
                    'amount': amount_str,
                    'currency': currency,
                    'allowedMethods': 'card,wallet,bank_installments',
                    'merchantRedirect': request.build_absolute_uri(reverse('form_payment_success')),
                    'failureRedirect': request.build_absolute_uri(reverse('form_payment_failed')),
                    'redirectMethod': 'get',
                    'hash': hash_signature,
                    'mode': mode,
                    'display': 'ar',
                }

                checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"
                return redirect(checkout_url)

            except Exception as e:
                messages.error(request, f"حدث خطأ أثناء الحجز: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = FormReservationForm(user=request.user, category=category)

    return render(request, "form_reservation.html", {
        "form": form,
        "category": category,
        "category_id": category.id,
        "passenger": getattr(request.user, 'passenger', None),
        "cities": City.objects.filter(is_active=True, category=category).distinct()
    })


# ✅ عند نجاح الدفع
@csrf_exempt
def form_payment_success(request):
    status = request.GET.get('paymentStatus')
    order_id = request.GET.get('merchantOrderId')
    amount = request.GET.get('amount')

    if status and status.upper() == "SUCCESS" and order_id:
        updated = FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(
            status='confirmed',
            paid_amount=Decimal(amount)
        )
        if updated > 0:
            return render(request, "success.html", {
                "message": "✅ تم الدفع وتأكيد الحجز بنجاح.",
                "order_id": order_id
            })
        else:
            return render(request, "success.html", {
                "message": "تم الدفع بنجاح، لكن لم يتم العثور على الحجز.",
                "order_id": order_id
            })

    # لو فشل
    FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(status='failed')

    return render(request, "success.html", {
        "message": "❌ فشل الدفع أو تم إلغاؤه.",
        "order_id": order_id
    })


def form_payment_failed(request):
    order_id = request.GET.get('merchantOrderId')
    FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(status='failed')
    return render(request, "success.html", {"message": "❌ فشل الدفع أو تم إلغاؤه.", "order_id": order_id})


# ========== AJAX Views الجديدة ==========

@login_required
def load_cities_by_round(request):
    """تحميل المدن حسب الوقت ونوع الرحلة"""
    time = request.GET.get("time")
    trip_type = request.GET.get("trip_type")
    category_id = request.GET.get("category_id")
    data = []
    
    if time and trip_type and category_id:
        rounds = Round.objects.filter(category_id=category_id, trip_type=trip_type)
        if trip_type == "ذهاب":
            rounds = rounds.filter(start_time=time)
        elif trip_type == "عودة":
            rounds = rounds.filter(back_time=time)
        
        cities = City.objects.filter(round__in=rounds, is_active=True).distinct()
        data = [{"id": city.id, "name": city.name} for city in cities]
    
    return JsonResponse(data, safe=False)


def load_pickup_locations_filtered(request):
    """تحميل نقاط الركوب المفلترة (نشطة فقط)"""
    city_id = request.GET.get("city_id")
    data = []
    
    if city_id:
        for loc in PickupLocation.objects.filter(city_id=city_id, is_active=True):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})
    
    return JsonResponse(data, safe=False)

def load_dropoff_locations(request):
    """تحميل نقاط النزول حسب الجامعة ونوع الرحلة"""
    category_id = request.GET.get("category_id")
    trip_type = request.GET.get("trip_type")
    data = []

    if category_id and trip_type:
        for loc in DropoffLocation.objects.filter(
            category_id=category_id,
            trip_type=trip_type,
            is_active=True
        ):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})

    return JsonResponse(data, safe=False)

def ajax_load_cities_by_round(request):
    """للتوافق مع الكود القديم"""
    time = request.GET.get("time")
    cities = City.objects.filter(round__start_time=time, is_active=True).distinct()
    data = [{"id": c.id, "name": c.name} for c in cities]
    return JsonResponse(data, safe=False)


def load_pickup_locations(request):
    """للتوافق مع الكود القديم"""
    city_id = request.GET.get("city_id")
    data = []
    if city_id:
        for loc in PickupLocation.objects.filter(city_id=city_id):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})
    return JsonResponse(data, safe=False)

from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

# @csrf_exempt
# def mark_attendance(request):
#     if request.method == 'POST':
#         source = request.POST.get('source')
#         booking_id = request.POST.get('id')

#         try:
#             # استخدام database transaction لضمان سلامة البيانات
#             with transaction.atomic():
#                 if source == 'form':
#                     reservation = FormReservation.objects.get(id=booking_id)
                    
#                     # التحقق من أن الحضور لم يسجل مسبقاً
#                     if reservation.attendance_status == 'present':
#                         return JsonResponse({
#                             'success': False, 
#                             'error': 'تم تسجيل حضور هذا الراكب مسبقاً'
#                         }, status=400)
                    
#                     # تسجيل الحضور
#                     reservation.attendance_status = 'present'
#                     reservation.save()
                    
#                     # تحديث عدد الرحلات للراكب
#                     passenger_obj = reservation.passenger
#                     if passenger_obj:
#                         # زيادة عدد الرحلات المستخدمة
#                         passenger_obj.rides_used += 1
#                         passenger_obj.save()
                        
#                         return JsonResponse({
#                             'success': True,
#                             'message': f'تم تسجيل حضور {passenger_obj.name} بنجاح',
#                             'passenger_name': passenger_obj.name,
#                             'rides_used': passenger_obj.rides_used,
#                             'remaining_rides': passenger_obj.remaining_rides
#                         })
#                     else:
#                         return JsonResponse({
#                             'success': False, 
#                             'error': 'لا يوجد راكب مرتبط بهذا الحجز'
#                         }, status=400)
                        
#                 elif source == 'booking':
#                     booking = Booking.objects.get(id=booking_id)
                    
#                     # التحقق من أن الحضور لم يسجل مسبقاً
#                     if booking.attendance_status == 'present':
#                         return JsonResponse({
#                             'success': False, 
#                             'error': 'تم تسجيل حضور هذا الراكب مسبقاً'
#                         }, status=400)
                    
#                     # تسجيل الحضور
#                     booking.attendance_status = 'present'
#                     booking.save()
                    
#                     # تحديث عدد الرحلات للراكب
#                     passenger_obj = booking.passenger
#                     if passenger_obj:
#                         # زيادة عدد الرحلات المستخدمة
#                         passenger_obj.rides_used += 1
#                         passenger_obj.save()
                        
#                         return JsonResponse({
#                             'success': True,
#                             'message': f'تم تسجيل حضور {passenger_obj.name} بنجاح',
#                             'passenger_name': passenger_obj.name,
#                             'rides_used': passenger_obj.rides_used,
#                             'remaining_rides': passenger_obj.remaining_rides
#                         })
#                     else:
#                         return JsonResponse({
#                             'success': False, 
#                             'error': 'لا يوجد راكب مرتبط بهذا الحجز'
#                         }, status=400)
#                 else:
#                     return JsonResponse({'success': False, 'error': 'مصدر غير صالح'}, status=400)
                    
#         except (FormReservation.DoesNotExist, Booking.DoesNotExist):
#             return JsonResponse({'success': False, 'error': 'الحجز غير موجود'}, status=404)
#         except Exception as e:
#             return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'}, status=500)
            
#     return JsonResponse({'success': False, 'error': 'طريقة غير مسموح بها'}, status=405)

# دالة لتحديث حالة الدفع (للسائق)
@csrf_exempt
def update_payment_status(request, booking_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status')
            
            booking = Booking.objects.get(id=booking_id)
            booking.status = new_status
            booking.save()
            return JsonResponse({'success': True})
        except Booking.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'الحجز غير موجود'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'طريقة غير مسموح بها'}, status=405)


# ✅ عند نجاح الدفع
@csrf_exempt
def form_payment_success(request):
    status = request.GET.get('paymentStatus')
    order_id = request.GET.get('merchantOrderId')
    amount = request.GET.get('amount')

    if status and status.upper() == "SUCCESS" and order_id:
        updated = FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(
            status='confirmed',
            paid_amount=Decimal(amount)
        )
        if updated > 0:
            return render(request, "success.html", {
                "message": "✅ تم الدفع وتأكيد الحجز بنجاح.",
                "order_id": order_id
            })
        else:
            return render(request, "success.html", {
                "message": "تم الدفع بنجاح، لكن لم يتم العثور على الحجز.",
                "order_id": order_id
            })

    # لو فشل
    FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(status='failed')

    return render(request, "success.html", {
        "message": "❌ فشل الدفع أو تم إلغاؤه.",
        "order_id": order_id
    })


def form_payment_failed(request):
    order_id = request.GET.get('merchantOrderId')
    FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(status='failed')
    return render(request, "success.html", {"message": "❌ فشل الدفع أو تم إلغاؤه.", "order_id": order_id})


@csrf_exempt
def form_payment_success(request):
    status = request.GET.get('paymentStatus')
    order_id = request.GET.get('merchantOrderId')
    amount = request.GET.get('amount')

    if status and status.upper() == "SUCCESS" and order_id:
        updated = FormReservation.objects.filter(merchant_order_id=order_id, status='pending').update(
            status='confirmed',
            paid_amount=Decimal(amount)
        )
        if updated > 0:
            return render(request, "success.html", {
                "message": "✅ تم الدفع وتأكيد الحجز بنجاح.",
                "order_id": order_id
            })
        else:
            return render(request, "success.html", {
                "message": "تم الدفع بنجاح، لكن لم يتم العثور على الحجز.",
                "order_id": order_id
            })

    return render(request, "success.html", {
        "message": "❌ فشل الدفع أو تم إلغاؤه.",
        "order_id": order_id
    })


def form_payment_failed(request):
    return render(request, "success.html", {"message": "❌ فشل الدفع أو تم إلغاؤه."})

def load_pickup_locations(request):
    """للتوافق مع الكود القديم"""
    city_id = request.GET.get("city_id")
    data = []
    
    if city_id:
        for loc in PickupLocation.objects.filter(city_id=city_id):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})
    
    return JsonResponse(data, safe=False)

@login_required
def load_cities_by_round(request):
    """تحميل المدن حسب الوقت ونوع الرحلة"""
    time = request.GET.get("time")
    trip_type = request.GET.get("trip_type")
    category_id = request.GET.get("category_id")
    data = []
    
    if time and trip_type and category_id:
        rounds = Round.objects.filter(category_id=category_id, trip_type=trip_type)
        if trip_type == "ذهاب":
            rounds = rounds.filter(start_time=time)
        elif trip_type == "عودة":
            rounds = rounds.filter(back_time=time)
        
        cities = City.objects.filter(round__in=rounds, is_active=True).distinct()
        data = [{"id": city.id, "name": city.name} for city in cities]
    
    return JsonResponse(data, safe=False)
def ajax_load_cities_by_round(request):
    """للتوافق مع الكود القديم"""
    time = request.GET.get("time")
    cities = City.objects.filter(round__start_time=time, is_active=True).distinct()
    data = [{"id": c.id, "name": c.name} for c in cities]
    return JsonResponse(data, safe=False)

# Original load_pickup_locations - keep unchanged for general use
def load_pickup_locations(request):
    city_id = request.GET.get("city_id")
    data = []
    if city_id:
        # NO FILTERING - keep original behavior
        for loc in PickupLocation.objects.filter(city_id=city_id):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})
    return JsonResponse(data, safe=False)

def load_pickup_locations_filtered(request):
    """تحميل نقاط الركوب المفلترة (نشطة فقط)"""
    city_id = request.GET.get("city_id")
    data = []
    
    if city_id:
        for loc in PickupLocation.objects.filter(city_id=city_id, is_active=True):
            for line in loc.name.strip().splitlines():
                txt = line.strip()
                if txt:
                    data.append({"id": txt, "text": txt})
    
    return JsonResponse(data, safe=False)
# NEW FUNCTION: Filtered cities for specific use cases

@login_required
def load_cities_by_round_filtered(request):
    """
    This function is specifically for going_pickup_location and return_dropoff_location
    It filters by is_active=True
    """
    time = request.GET.get("time")
    trip_type = request.GET.get("trip_type")
    category_id = request.GET.get("category_id")
    data = []
    if time and trip_type and category_id:
        rounds = Round.objects.filter(category_id=category_id, trip_type=trip_type)
        if trip_type == "ذهاب":
            rounds = rounds.filter(start_time=time)
        elif trip_type == "عودة":
            rounds = rounds.filter(back_time=time)
        # APPLY FILTERING - only for specific fields
        cities = City.objects.filter(round__in=rounds, is_active=True).distinct()
        data = [{"id": city.id, "name": city.name} for city in cities]
    return JsonResponse(data, safe=False)

@login_required
def ajax_load_round_times(request):
    trip_type = request.GET.get('trip_type')
    if not trip_type:
        return JsonResponse([], safe=False)

    times = Round.objects.filter(
        trip_type=trip_type
    ).exclude(time__isnull=True).exclude(time__exact="").values_list('time', flat=True).distinct()

    return JsonResponse(list(times), safe=False)
@login_required
def confirm_reservation(request):
    if request.method == 'POST':
        form = FormReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.user = request.user
            reservation.save()

            if reservation.trip_type == "ذهاب وعودة":
                # احجز حجز تاني للعودة
                return_city = City.objects.get(id=request.POST.get('return_city_id'))
                back_reservation = FormReservation.objects.create(
                    category=reservation.category,
                    seat=None,
                    passenger=reservation.passenger,
                    student_name=reservation.student_name,
                    trip_date=reservation.trip_date,
                    trip_type="عودة",
                    arrival_time=None,
                    back_time=reservation.back_time,
                    round=None, # لو فيه راوند للعودة ممكن تضيفه هنا
                    city=return_city,
                    user=request.user
                )
            return redirect('success_page')
    else:
        form = FormReservationForm()

    cities = City.objects.all()
    return render(request, 'reservation.html', {'form': form, 'cities': cities})

@login_required
def choose_trip(request, passenger_ids):
    passenger_ids = list(map(int, passenger_ids.split(',')))
    passengers = passenger.objects.filter(id__in=passenger_ids)
    trips = Trip.objects.filter(is_active=True, date__gte=now().date())
    if request.method == 'POST':
        selected_trip_id = request.POST.get('trip_id')
        selected_trip = Trip.objects.get(id=selected_trip_id)
        for p in passengers:
            p.selected_trip = selected_trip
        return redirect('success_page')
    return render(request, 'choose_trip.html', {'passengers': passengers, 'trips': trips})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import logging
from .models import Bus

logger = logging.getLogger(__name__)
# your_app/views.py

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
import json
from .models import Bus # تأكد من استيراد موديل Bus

# ... (احتفظ بباقي دوالك مثل my_buses, updatePaymentStatus, إلخ ) ...


# =================================================================
#  ✅✅✅  المنطق الموحد والنهائي لمشاركة الموقع ✅✅✅
# =================================================================

@require_POST
@csrf_exempt
def start_location_session(request, bus_id):
    """
    (للسائق) يبدأ جلسة مشاركة الموقع لمدة ساعة.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    bus.location_sharing_is_active = True
    bus.location_sharing_expires_at = timezone.now() + timedelta(hours=1)
    bus.save()
    return JsonResponse({'status': 'success', 'message': 'Location sharing started.'})

@require_POST
@csrf_exempt
def stop_location_session(request, bus_id):
    """
    (للسائق) يوقف جلسة مشاركة الموقع ويمسح البيانات.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    bus.location_sharing_is_active = False
    bus.location_sharing_expires_at = None
    bus.latitude = None
    bus.longitude = None
    bus.location_url = None
    bus.save()
    return JsonResponse({'status': 'success', 'message': 'Location sharing stopped.'})

@require_POST
@csrf_exempt
def update_bus_location(request, bus_id):
    """
    (للسائق) يستقبل تحديثات الموقع ويحفظها.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    
    is_expired = bus.location_sharing_expires_at and timezone.now() < bus.location_sharing_expires_at
    if not bus.location_sharing_is_active or not is_expired:
        bus.location_sharing_is_active = False
        bus.save()
        return JsonResponse({'status': 'error', 'message': 'Session expired or inactive.'}, status=403)

    try:
        data = json.loads(request.body)
        lat, lon = data.get('latitude'), data.get('longitude')
        if lat is not None and lon is not None:
            bus.latitude, bus.longitude = lat, lon
            bus.location_url = f"https://www.google.com/maps?q={lat},{lon}"
            bus.save( )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid coordinates.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)


def track_bus_view(request, bus_id):
    """
    (للراكب) تعرض صفحة الخريطة.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    context = {'bus_id': bus.id, 'bus_name': bus.name}
    return render(request, 'bus_location.html', context)

# your_app/views.py

def get_live_location_data(request, bus_id):
    """
    (للراكب) API لإرسال بيانات الموقع الحالية بصيغة JSON.
    (النسخة النهائية المتوافقة مع كود الخريطة الجديد)
    """
    bus = get_object_or_404(Bus, id=bus_id)
    
    is_expired = bus.location_sharing_expires_at and timezone.now() < bus.location_sharing_expires_at
    
    if bus.location_sharing_is_active and is_expired and bus.latitude is not None:
        # ✅ تعديل: تم تغيير 'status' من 'active' إلى 'success' ليتوافق مع الفرونت إند
        return JsonResponse({
            'status': 'success', 
            'latitude': bus.latitude,
            'longitude': bus.longitude,
            'location_url': bus.location_url,
        })
    else:
        # ✅ تعديل: تم تغيير 'status' وإضافة رسالة خطأ واضحة
        return JsonResponse({
            'status': 'error',
            'message': 'مشاركة الموقع غير نشطة حالياً.'
        })

# def update_driver_status(request,  trip_id):
#     trip = get_object_or_404(trip, id= trip_id)

#     if request.method == "POST":
#         new_status = request.POST.get("driver_status")
#         if new_status in dict(trip.DRIVER_STATUS_CHOICES):
#             trip.driver_status = new_status
#             trip.save()
#             messages.success(request, "تم تحديث حالة السائق بنجاح.")
#         else:
#             messages.error(request, "حالة غير صالحة.")
#         return redirect('update_driver_status',  trip_id=trip.id)

#     return render(request, 'update_driver_status.html', {'trip': trip})

from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User

from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import passenger

from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.http import JsonResponse
from .models import passenger

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import passenger

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import passenger

def get_client_ip(request):
    """استخراج عنوان IP الحقيقي للمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]  # استخراج أول عنوان IP (الحقيقي)
    else:
        ip = request.META.get('REMOTE_ADDR')  # إذا لم يكن هناك Forwarding، نأخذ الـ IP مباشرة
    return ip

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from .models import passenger

def login_view(request):
    if request.method == "POST":
        username_or_code = request.POST.get("username", "").strip().lower()
        password = request.POST.get("password", "").strip()
        client_ip = get_client_ip(request)   
        print(client_ip)


        user = authenticate(request, username=username_or_code, password=password)

        if user is None:
            try:
                passenger_obj = passenger.objects.get(university_code=username_or_code)
                if passenger_obj.user:

                    user = passenger_obj.user
                    login(request, user)

                    if not passenger_obj.fixed_ip:
                        passenger_obj.fixed_ip = client_ip
                        passenger_obj.save()

                    return redirect("index")

            except passenger.DoesNotExist:
                pass

        if user is not None:
            login(request, user)
            return redirect("index")

        return render(request, "login.html", {"message": "❌ بيانات تسجيل الدخول غير صحيحة!"})

    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("login")
def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # تسجيل الدخول تلقائيًا بعد التسجيل
            return redirect('index')  # إعادة التوجيه إلى الصفحة الرئيسية
    else:
        form = SignupForm()
    
    return render(request, 'signup.html', {'form': form})

def booking_list(request):
    items = passenger.objects.all()
    for item in items:
        if item.qr_code:
            # إذا كان qr_code بيانات ثنائية، تحويلها إلى Base64
            if isinstance(item.qr_code, bytes):
                item.qr_code_base64 = base64.b64encode(item.qr_code).decode('utf-8')
            else:
                # إذا كان qr_code سلسلة Base64، استخدمه كما هو
                item.qr_code_base64 = item.qr_code
        else:
            item.qr_code_base64 = None
    return render(request, 'user_data.html', {'items': items})


from django.utils.timezone import localdate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Bus, Trip

from django.utils.timezone import localdate
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Bus, Trip

from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from .models import Bus, Trip, Booking
from django.shortcuts import render
from datetime import date, timedelta
from django.db.models import Q
from .models import Bus, Trip, Booking  # تأكد من استيراد Booking إن ما كنت عامل related_name
from collections import defaultdict
from collections import defaultdict
from datetime import date, timedelta
from django.db.models import Q
from django.shortcuts import render
from .models import Bus, Trip, Booking, FormReservation

# Anaconda_bus_APP/views.py

from django.shortcuts import render
from django.db.models import Q
from collections import defaultdict
from datetime import date, timedelta
from .models import Bus, Trip, Booking, FormReservation # تأكد من استيراد المودلز الخاصة بك
# views.py

import re
from datetime import datetime, date, timedelta
from django.shortcuts import render
from django.db.models import Q
from .models import Bus, Trip, Booking, FormReservation

def extract_time_from_string(text):
    """يستخرج الوقت من النص ويحوله إلى كائن time للمقارنة والترتيب."""
    match = re.search(r'(\d{1,2}):(\d{2})\s*(ص|م)?', text)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    period = match.group(3)
    if (period == 'م') and hour != 12:
        hour += 12
    elif (period == 'ص') and hour == 12:
        hour = 0
    try:
        return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
    except ValueError:
        return None

def normalize_text(text):
    """ينظف النص للمقارنة (يزيل الوقت، الأقواس، والمسافات الزائدة)."""
    if not text: return ""
    text = text.strip().lstrip('-').strip()
    text = re.sub(r'\d{1,2}:\d{2}\s*(ص|م)?', '', text)
    text = re.sub(r'\(.*\)', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def find_best_match(area_name, route_list):
    """
    يبحث عن أفضل تطابق لاسم منطقة داخل قائمة الـ route.
    الآن يقوم بمطابقة جزئية إذا فشلت المطابقة الكاملة.
    """
    if not area_name or area_name == 'غير محدد':
        return None # لا تحاول مطابقة المناطق غير المحددة

    normalized_area = normalize_text(area_name)
    
    # 1. محاولة المطابقة الكاملة (الأكثر دقة)
    for route_item in route_list:
        if normalized_area == normalize_text(route_item):
            return route_item

    # 2. محاولة المطابقة الجزئية (إذا فشلت الأولى)
    # يبحث عن أول كلمة مشتركة
    area_words = set(normalized_area.split())
    if not area_words: return None

    for route_item in route_list:
        route_words = set(normalize_text(route_item).split())
        if area_words.intersection(route_words):
            return route_item # إرجاع أول تطابق جزئي يتم العثور عليه

    return None # إذا فشلت كل المحاولات، لا ترجع شيئاً
# Anaconda_bus_APP/views.py

from django.shortcuts import render
from django.db.models import Q
from datetime import date, timedelta
from .models import Bus, Trip, Booking, FormReservation
# Anaconda_bus_APP/views.py

# ... (كل أكواد الاستيراد في بداية الملف كما هي) ...
from .models import Bus, Trip, Booking, FormReservation, LocationLink # ✨ تم إضافة LocationLink هنا
def my_buses(request):
    if not request.user.is_authenticated:
        return render(request, 'my_buses.html', {'buses_data': []})
    
    # Get passenger object for weekly booking
    passenger_obj = None
    try:
        passenger_obj = passenger.objects.get(user=request.user)
    except passenger.DoesNotExist:
        pass
    
    location_links = {link.point_name: link.google_maps_link for link in LocationLink.objects.all()}
    buses = Bus.objects.filter(Bus_driver=request.user)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    buses_data = []

    for bus in buses:
        trips = Trip.objects.filter(
            Q(bus=bus) | Q(related_return_trip__bus=bus) | Q(related_departure_trip__bus=bus),
            is_active=True,
            date__range=[today, tomorrow]
        ).distinct().select_related('start_destination', 'end_destination')

        trips_data = []
        for trip in trips:
            # استخراج نقاط التوقف مع الوقت
            stops_with_time = []
            raw_stops = [stop.strip() for stop in trip.route.split('\n') if stop.strip()]
            
            for stop_text in raw_stops:
                time_obj = extract_time_from_string(stop_text)
                if time_obj:
                    stops_with_time.append({'text': stop_text, 'time': time_obj})
                else:
                    # إذا لم يتم العثور على وقت، نستخدم وقتًا افتراضيًا (مثل 00:00)
                    stops_with_time.append({'text': stop_text, 'time': datetime.strptime("00:00", "%H:%M").time()})
            
            # ترتيب النقاط حسب الوقت
            sorted_stops = sorted(stops_with_time, key=lambda x: x['time'])
            ordered_stops = [item['text'] for item in sorted_stops]

            # تجميع الحجوزات حسب المنطقة
            bookings_by_area = {stop: [] for stop in ordered_stops}
            total_passengers_count = 0
            all_reservations = []
            
            # حجوزات Booking
            bookings = Booking.objects.filter(Trip=trip).select_related('passenger', 'user').prefetch_related('seats_reserved')
            total_passengers_count += bookings.count()
            for b in bookings:
                all_reservations.append({
                    'area': b.selected_route, 
                    'details': {
                        'source': 'booking', 
                        'id': b.id,
                        'name': b.passenger.name if b.passenger else 'غير معروف',
                        'phone': b.passenger.phone_number if b.passenger else '---', 
                        'status': b.status,
                        'attendance_status': b.attendance_status,
                        'seats_reserved_list': ", ".join([str(s.seat_number) for s in b.seats_reserved.all()]),
                        'face_thumbnail': b.passenger.face_thumbnail.url if (b.passenger and b.passenger.face_thumbnail) else None,
                    }
                })

            # حجوزات FormReservation
            form_reservations = FormReservation.objects.filter(
                trip=trip
            ).exclude(
                status='pending'  # استبعاد الحجوزات قيد الانتظار
            ).select_related('user', 'seat', 'passenger')

            total_passengers_count += form_reservations.count()
            for res in form_reservations:
                # تحديد نقطة الانطلاق بناءً على نوع الرحلة
                pickup_point = res.pickup_location if res.trip_type == 'ذهاب' else res.return_pickup_location
                
                all_reservations.append({
                    'area': pickup_point, 
                    'details': {
                        'source': 'form', 
                        'id': res.id,
                        'name': res.student_name or (res.passenger.name if res.passenger else 'غير معروف'),
                        'phone': res.phone_number or (res.passenger.phone_number if res.passenger else '---'), 
                        'status': res.status,
                        'attendance_status': res.attendance_status,
                        'seat_number': str(res.seat.seat_number if res.seat else res.seat_number or "---"),
                        'going_pickup': res.pickup_location,
                        'going_dropoff': res.going_dropoff_location,
                        'return_pickup': res.return_pickup_location,
                        'return_dropoff': res.return_dropoff_location,
                        'trip_type': res.trip_type,
                        'face_thumbnail': res.passenger.face_thumbnail.url if (res.passenger and res.passenger.face_thumbnail) else None,
                    }
                })

            # تجميع الحجوزات حسب النقاط المطابقة
            for res in all_reservations:
                area_name = res['area']
                # البحث عن أفضل تطابق مع النقاط المرتبة
                matched_stop = find_best_match(area_name, ordered_stops)
                if matched_stop and matched_stop in bookings_by_area:
                    bookings_by_area[matched_stop].append(res['details'])

            # بناء القائمة النهائية للعرض مع دمج رابط الموقع
            final_ordered_bookings = []
            
            # إضافة النقاط المرتبة حسب الوقت مع حجوزاتها
            for stop_name in ordered_stops:
                stop_data = {
                    'name': stop_name,
                    'link': location_links.get(stop_name)  # قد يكون None إذا لم يوجد رابط
                }
                final_ordered_bookings.append((stop_data, bookings_by_area.get(stop_name, [])))
            
            # حساب إجمالي عدد الركاب
            total_passengers_count = sum(len(bookings) for _, bookings in final_ordered_bookings)

            # إضافة بيانات الرحلة
            trips_data.append({
                'trip': trip,
                'bookings_by_area': final_ordered_bookings,
                'total_passengers': total_passengers_count,
            })

        buses_data.append({'bus': bus, 'trips': trips_data})

    return render(request, 'my_buses.html', {
        'buses_data': buses_data,
        'passenger_obj': passenger_obj
    })


from django.shortcuts import redirect, get_object_or_404
import requests

def notify_trip_departure(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    # نتأكد إن الكاتيجوري = 1
    if trip.bus.category.id != 1:
        return redirect('my_buses')

    # الرسالة الملهمة
    message = (
        " يلا الباص اكتمل \n\n"
        "يلا اتحرك على البوابة.. رحلتك هتبدأ خلاص، "
        "بتمنالك رحله سعيده❤✌🏻"
    )

    # الحجوزات (من Booking + FormReservation)
    reservations = list(Booking.objects.filter(Trip=trip).select_related("passenger"))
    reservations += list(FormReservation.objects.filter(trip=trip).select_related("passenger"))

    # إرسال لكل راكب
    for res in reservations:
        if hasattr(res, "passenger") and res.passenger and res.passenger.phone_number:
            phone = str(res.passenger.phone_number).strip()
            if not phone.startswith("+"):
                phone = f"+20{phone.lstrip('0')}"

            INSTANCE_ID = "instance105329"
            API_TOKEN = settings.ULTRAMSG_API_TOKEN
            URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

            payload = {
                "token": API_TOKEN,
                "to": phone,
                "body": message
            }
            requests.post(URL, data=payload)

    return redirect('my_buses')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .models import Bus, BusLocation # تأكد من استيراد BusLocation
import json

# ... (باقي دوال الـ view الموجودة مثل my_buses ) ...

# Anaconda_bus_APP/views.py
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
# ... (باقي imports )

# 1. دالة لبدء جلسة المشاركة (يستدعيها السائق)
# your_app/views.py

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt # تأكد من وجود هذا السطر
from django.utils import timezone
from datetime import timedelta
import json
from .models import Bus # استيراد موديل Bus

# ... باقي دوال الـ views الخاصة بك ...

# =================================================================
#           دوال مشاركة الموقع المباشر (النسخة المصححة )
# =================================================================

@require_POST
@csrf_exempt # استخدم csrf_exempt إذا كنت تواجه مشاكل مع CSRF من JavaScript
def start_location_session(request, bus_id):
    """
    يبدأ جلسة مشاركة الموقع لمدة ساعة عن طريق تحديث موديل Bus.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    bus.location_sharing_is_active = True
    bus.location_sharing_expires_at = timezone.now() + timedelta(hours=1)
    bus.save()
    return JsonResponse({'status': 'success', 'message': 'Location sharing started.'})

@require_POST
@csrf_exempt
def stop_location_session(request, bus_id):
    """
    يوقف جلسة مشاركة الموقع ويمسح البيانات من موديل Bus.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    bus.location_sharing_is_active = False
    bus.location_sharing_expires_at = None
    bus.latitude = None
    bus.longitude = None
    bus.location_url = None
    bus.save()
    return JsonResponse({'status': 'success', 'message': 'Location sharing stopped and all location data cleared.'})

@require_POST
@csrf_exempt
def update_bus_location(request, bus_id):
    """
    يستقبل تحديثات الموقع من السائق ويحفظها في موديل Bus.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    
    # التحقق من أن الجلسة لا تزال نشطة ولم تنتهِ صلاحيتها
    is_expired = bus.location_sharing_expires_at and timezone.now() > bus.location_sharing_expires_at
    if not bus.location_sharing_is_active or is_expired:
        # إذا انتهت، قم بإيقافها رسمياً لضمان نظافة البيانات
        bus.location_sharing_is_active = False
        bus.save()
        return JsonResponse({'status': 'error', 'message': 'Session expired or inactive.'}, status=403)

    try:
        data = json.loads(request.body)
        lat = data.get('latitude')
        lon = data.get('longitude')

        if lat is not None and lon is not None:
            bus.latitude = lat
            bus.longitude = lon
            # إنشاء رابط خرائط جوجل وتخزينه
            bus.location_url = f"https://www.google.com/maps?q={lat},{lon}"
            bus.save( )
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'message': 'Invalid coordinates.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)


# 4. دالة جلب الموقع (يستدعيها الطالب) - معدلة
def get_live_tracking_data(request, bus_id):
    try:
        location = BusLocation.objects.get(bus_id=bus_id)
        # التحقق من أن الجلسة صالحة وأن هناك بيانات موقع
        if location.is_session_valid() and location.latitude is not None:
            # هنا يمكننا إضافة منطق إرسال Web Push للسائق
            # (هذا الجزء معقد ويتطلب مكتبات مثل web-push)
            # For now, we assume the service worker polls.
            
            return JsonResponse({
                'status': 'success',
                'latitude': location.latitude,
                'longitude': location.longitude,
            })
        else:
            # إذا انتهت الجلسة، قم بمسح البيانات
            location.latitude = None
            location.longitude = None
            location.is_active = False
            location.save()
            return JsonResponse({'status': 'error', 'message': 'Location sharing is not active or has expired.'}, status=404)
    except BusLocation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Bus has never shared its location.'}, status=404)

# your_app/views.py

def track_bus_view(request, bus_id):
    """
    (للراكب) تعرض صفحة الخريطة وتمرر مفتاح جوجل.
    """
    bus = get_object_or_404(Bus, id=bus_id)
    context = {
        'bus_id': bus.id,
        'bus_name': bus.name,
        # تأكد من أن هذا المفتاح موجود في ملف settings.py الخاص بك
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY 
    }
    return render(request, 'track_bus.html', context)


def bus_status(request):
    buses = Bus.objects.all()
    return render(request, 'bus_status.html', {'buses': buses})


def attendance_view(request):
    if request.method == 'POST':
        attendance_data = request.POST.get('attendance_data', None)
        attendance_status = request.POST.get('attendance_status', None)

        if attendance_data:
            try:
                data = json.loads(attendance_data)
                existing_record = Attendance.objects.filter(
                    user_id=data['id'], attendance_date=date.today()
                ).first()

                student = passenger.objects.filter(id=data['id']).first()

                if not student:
                    messages.error(request, "Student not found!")
                    return render(request, 'scan_qr.html')

                if existing_record:
                    # تحقق إذا كان الحضور أو الانصراف مسجل مسبقًا
                    if attendance_status == 'حضور':
                        if existing_record.attendance_status == 'حضور':
                            messages.error(request, f"{data['name']} has already been marked as present today!")
                        else:
                            existing_record.attendance_status = 'حضور'
                            existing_record.save()
                            messages.success(request, f"{data['name']} marked as present successfully!")

                    elif attendance_status == 'انصراف':
                        if existing_record.departure_status == 'انصراف':
                            messages.error(request, f"{data['name']} has already been marked as departed today!")
                        else:
                            existing_record.departure_status = 'انصراف'
                            existing_record.save()
                            messages.success(request, f"{data['name']} marked as departed successfully!")

                    # خصم رحلة إذا لم يتم الخصم مسبقًا
                    if not existing_record.ride_deducted:
                        if student.remaining_rides > 0:
                            student.rides_used += 1
                            student.save()
                            existing_record.ride_deducted = True
                            existing_record.save()
                        else:
                            messages.error(request, f"{data['name']} has no remaining rides!")
                else:
                    # إذا لم يكن هناك سجل، قم بإنشائه وخصم الرحلة
                    ride_deducted = False
                    if student.remaining_rides > 0:
                        student.rides_used += 1
                        student.save()
                        ride_deducted = True
                    else:
                        messages.error(request, f"{data['name']} has no remaining rides!")

                    Attendance.objects.create(
                        user_id=data['id'],
                        name=data['name'],
                        category=data['category'],
                        subscription_start_date=data['subscription_start_date'],
                        subscription_end_date=data['subscription_end_date'],
                        attendance_status='حضور' if attendance_status == 'حضور' else 'غياب',
                        departure_status='انصراف' if attendance_status == 'انصراف' else 'غياب',
                        attendance_date=date.today(),
                        ride_deducted=ride_deducted,
                    )
                    messages.success(request, f"{data['name']} Attendance ({attendance_status}) recorded successfully!")

            except Exception as e:
                messages.error(request, f"Error: {e}")
    
    return render(request, 'scan_qr.html')

def attendance_reset_view(request):
    today = timezone.now().date()
    last_recorded_date = Attendance.objects.latest('attendance_date').attendance_date if Attendance.objects.exists() else None
    
    if not last_recorded_date or last_recorded_date < today:
        for item in passenger.objects.all():
            Attendance.objects.create(
                user_id=item.id,
                name=item.name,
                category=item.category.name,
                subscription_start_date=item.subscription_start_date,
                subscription_end_date=item.subscription_end_date,
                attendance_status='غياب',
                attendance_date=today
            )
    return render(request, 'attendance_page.html', {'attendance_list': Attendance.objects.filter(attendance_date=today)})



def get_qr_code_as_base64(item):
    if item.qr_code:
        return base64.b64encode(item.qr_code).decode('utf-8')
    return None

@login_required
def user_profile(request):
    try:
        current_passenger = passenger.objects.get(user=request.user)
        user_type = current_passenger.user_type  # ✅ استخراج نوع المستخدم
    except passenger.DoesNotExist:
        current_passenger = None
        user_type = None  # في حالة عدم وجود حساب راكاب

    return render(request, 'user_data.html', {
        'items': [current_passenger] if current_passenger else [],
        'user_type': user_type,  # ✅ تمرير نوع المستخدم إلى القالب
    })


def generate_qr(request, item_id):
    item = get_object_or_404(passenger, id=item_id)
    qr_data = f"Student Code: {item.student_code}\nStudent Name: {item.student_name}\nUniversity: {item.university}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return HttpResponse(buffer, content_type="image/png")



@csrf_exempt
def end_trip(request, trip_id):
    if request.method == "POST":
        try:
            logger.info(f"Received request to end trip with ID: {trip_id}")

            trip = get_object_or_404(Trip, id=trip_id)
            logger.info(f"Trip found: {trip}")

            trip.date += timedelta(days=1)
            trip.save()
            logger.info(f"Trip date updated to: {trip.date}")

            seats = trip.bus.seats.all()
            seats.update(is_reserved=False)
            logger.info(f"Seats reset for bus: {trip.bus.name}")

            bookings = Booking.objects.filter(Trip=trip)
            bookings.update(status="completed")
            logger.info(f"Bookings updated to 'completed' for trip: {trip.id}")

            return JsonResponse({"message": "تم إنهاء الرحلة وتحديثها لليوم التالي بنجاح."})
        except Http404:
            logger.error(f"Trip with ID {trip_id} not found.")
            return JsonResponse({"error": "الرحلة غير موجودة."}, status=404)
        except Exception as e:
            logger.error(f"Unexpected error ending trip: {e}")
            return JsonResponse({"error": f"حدث خطأ غير متوقع: {e}"}, status=500)
    return JsonResponse({"error": "طريقة الطلب غير صحيحة."}, status=400)



def update_rides(request):
    item_id = request.POST.get('item_id')
    try:
        subscription = passenger.objects.get(id=item_id)
        if subscription.remaining_rides > 0:
            subscription.remaining_rides -= 1
            subscription.save()
            return JsonResponse({'success': 'Ride updated successfully'})
        else:
            return JsonResponse({'error': 'No remaining rides'}, status=400)
    except passenger.DoesNotExist:
        return JsonResponse({'error': 'Subscription not found'}, status=404)




@login_required
def check_trip_code(request):
    bookings = None
    student_bookings = None

    if request.method == 'POST':
        trip_code = request.POST.get('trip_code', None)
        university_code = request.POST.get('university_code', None)
        mark_paid = request.POST.get('mark_paid', None)  # للتحقق إذا تم اختيار "حجز كمدفوع مسبقًا"
        mark_attendance = request.POST.get('mark_attendance', None)  # للتحقق من زر تسجيل الحضور
        today = date.today()  # الحصول على تاريخ اليوم الحالي

        # البحث باستخدام كود الرحلة
        if trip_code:
            bookings = Booking.objects.filter(serial_code=trip_code, Trip__date=today)  # تصفية حجوزات اليوم الحالي
            if bookings.exists():
                messages.success(request, f"تم العثور على {bookings.count()} حجز مرتبط بكود الرحلة.")
            else:
                messages.error(request, "كود الرحلة غير صحيح أو لا توجد حجوزات لليوم الحالي. يرجى التحقق.")

        # البحث باستخدام كود الجامعة
        elif university_code:
            student = passenger.objects.filter(university_code=university_code).first()
            
            if student:
                # تصفية حجوزات اليوم الحالي فقط
                student_bookings = Booking.objects.filter(
                    passenger=student,
                    # status="active",  # الحجز يجب أن يكون نشطًا فقط
                    Trip__date=today
                ).select_related('passenger', 'payment')  # تحسين الأداء باستخدام select_related

                if student_bookings.exists():
                    if mark_paid:  # إذا تم اختيار الزر "حجز كمدفوع مسبقًا"
                        for booking in student_bookings:
                            if booking.attendance_status != "present":  # فقط الحجوزات التي لم تسجل حضورًا مسبقًا
                                booking.status = "prepaid"  # تحديث حالة الدفع كمدفوعة مسبقًا
                                booking.attendance_status = "present"  # تسجيل الحضور كحاضر
                                booking.save()  # حفظ التغييرات
                        messages.success(request, "تم تسجيل الحجز كمدفوع مسبقًا بنجاح.")

                    elif mark_attendance:  # إذا تم اختيار زر تسجيل الحضور
                        for booking in student_bookings:
                            if booking.attendance_status != "present":  # فقط الحجوزات التي لم تسجل حضورًا مسبقًا
                                booking.attendance_status = "present"  # تسجيل الحضور كحاضر
                                booking.status = "completed"  # تحديث الحالة إلى مكتملة
                                booking.save()  # حفظ التغييرات
                        messages.success(request, "تم تسجيل حضور الطالب للرحلة بنجاح.")
                else:
                    messages.info(request, "لا توجد رحلات محجوزة حالياً لهذا الطالب لليوم الحالي لم يتم تسجيل الحضور لها.")
            else:
                messages.error(request, "كود الجامعة غير صحيح. يرجى التحقق.")

    return render(request, 'check_trip_code.html', {
        'bookings': bookings,
        'student_bookings': student_bookings,
    })

@login_required
def mark_attendance(request, booking_id):
    try:
        # جلب الحجز
        booking = Booking.objects.get(id=booking_id)

        # التحقق من نوع الزر المضغوط
        mark_paid = request.POST.get('mark_paid', None)  # إذا كان الزر "حجز كمدفوع مسبقًا"
        mark_attendance = request.POST.get('mark_attendance', None)  # إذا كان الزر "تسجيل الحضور"

        if mark_paid:  # إذا كان المستخدم ضغط على "حجز كمدفوع مسبقًا"
            if booking.status == 'completed':  # التأكد أن الحجز ليس مكتملًا
                messages.warning(request, "هذا الحجز مكتمل بالفعل.")
                return redirect('check_trip_code')

            if booking.attendance_status == 'prepaid':  # التأكد أن الحجز ليس مدفوعًا مسبقًا
                messages.info(request, "تم تسجيل هذا الحجز كمدفوع مسبقًا بالفعل.")
                return redirect('check_trip_code')

            # تحديث حالة الدفع كمدفوع مسبقًا
            booking.attendance_status = 'present'
            booking.status = 'prepaid'
            booking.save()
            messages.success(request, f"تم تسجيل الحجز كمدفوع مسبقًا: {booking.serial_code}.")
            return redirect('check_trip_code')

        elif mark_attendance:  # إذا كان المستخدم ضغط على "تسجيل الحضور"
            if booking.status != 'active':  # التحقق أن الحجز نشط
                messages.warning(request, "هذا الحجز غير صالح لتسجيل الحضور.")
                return redirect('check_trip_code')

            if booking.attendance_status == 'present':  # التحقق من عدم تسجيل الحضور مسبقًا
                messages.info(request, "تم تسجيل الحضور مسبقًا لهذه الرحلة.")
                return redirect('check_trip_code')

            passenger_instance = booking.passenger  # جلب بيانات الراكب المرتبطة بالحجز

        with transaction.atomic():
            # إذا كانت الرحلات المتبقية <= 0
            if passenger_instance.remaining_rides <= 0:
                # تحديث حالة الحجز
                booking.attendance_status = 'present'
                booking.status = 'completed'

                # تسجيل رسالة نجاح
                messages.success(request, "تم تسجيل الحضور بنجاح. تم اعتبار الطالب مشتركًا ب الأيام.")
            else:
                # خصم رحلة واحدة من الرحلات المتبقية
                passenger_instance.remaining_rides -= 1
                passenger_instance.rides_used += 1

                # تحديث حالة الحجز
                booking.attendance_status = 'present'
                booking.status = 'completed'

                # تسجيل رسالة نجاح
                messages.success(request, "تم تسجيل الحضور بنجاح.")

            # حفظ التعديلات
            passenger_instance.save()  # تحديث بيانات الراكب
            booking.save()  # تحديث بيانات الحجز

            messages.success(request, f"تم تسجيل حضور الطالب للرحلة: {booking.serial_code}")
            return redirect('check_trip_code')

        # إذا لم يتم اختيار أي زر
        messages.error(request, "يرجى اختيار زر صالح.")
        return redirect('check_trip_code')

    except Exception as e:
        messages.error(request, f"حدث خطأ أثناء معالجة الطلب: {str(e)}")
        return redirect('check_trip_code')

def success_page(request):
    return render(request, 'success.html')
from django.shortcuts import render
from django.db.models import Count, F, Case, When, Value
from django.db.models.functions import Coalesce

# Anaconda_bus_APP/views.py

# ... (كل أكواد الاستيراد في بداية الملف كما هي) ...
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from datetime import date, datetime, timedelta
from .models import Trip, Booking, FormReservation, Category, passenger
import json

# ... (كل الدوال الأخرى تبقى كما هي) ...

# Anaconda_bus_APP/views.py
# Anaconda_bus_APP/views.py

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import Trip, FormReservation, Booking, Category
from datetime import datetime, date
import json
from .utils import get_route_plan_for_trip # ✅ --- تأكد من وجود هذا الاستيراد --- ✅

@staff_member_required
def bus_report_view(request):
    """
    يعرض لوحة تحكم تحليلية متكاملة للرحلات والحضور.
    """
    
    # --- 1. جلب الفلاتر من الطلب ---
    selected_date_str = request.GET.get('trip_date')
    selected_category_id = request.GET.get('category')
    search_passenger_name = request.GET.get('passenger_name', '').strip()

    # --- 2. بناء الاستعلام الأساسي للرحلات ---
    trips_queryset = Trip.objects.all().order_by('-date', '-start_time')

    # --- 3. تطبيق الفلاتر على الاستعلام ---
    selected_date = None # تعريف المتغير بقيمة ابتدائية
    if selected_date_str:
        # إذا قام المستخدم بتحديد تاريخ، استخدمه
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
            trips_queryset = trips_queryset.filter(date=selected_date)
        except (ValueError, TypeError):
            selected_date_str = None # تجاهل القيمة الخاطئة
            pass
    elif not request.GET:
        # إذا لم يتم تقديم أي فلاتر (فتح الصفحة لأول مرة)،
        # قم بالفلترة برحلات اليوم فقط.
        selected_date = date.today()
        selected_date_str = selected_date.strftime('%Y-%m-%d')
        trips_queryset = trips_queryset.filter(date=selected_date)

    if selected_category_id:
        trips_queryset = trips_queryset.filter(bus__category__id=selected_category_id)

    # --- 4. تجهيز بيانات التقرير المفصل والبيانات الإحصائية ---
    report_data = []
    total_passengers = 0
    total_attended = 0
    attendance_by_category = {}

    passenger_bookings = []
    if search_passenger_name:
        form_res = FormReservation.objects.filter(student_name__icontains=search_passenger_name).select_related('trip')
        booking_res = Booking.objects.filter(passenger__name__icontains=search_passenger_name).select_related('Trip', 'passenger')
        for b in form_res:
            if b.trip:
                passenger_bookings.append({'trip_name': b.trip.trip_name, 'trip_date': b.trip.date, 'attended': b.attendance_status == 'present'})
        for b in booking_res:
            if b.Trip:
                 passenger_bookings.append({'trip_name': b.Trip.trip_name, 'trip_date': b.Trip.date, 'attended': b.attendance_status == 'present'})

    for trip in trips_queryset:
        form_bookings = FormReservation.objects.filter(trip=trip).select_related('passenger', 'category')
        regular_bookings = Booking.objects.filter(Trip=trip).select_related('passenger', 'Trip__bus__category')
        
        all_passengers_details = []
        trip_attended_count = 0
        
        for b in form_bookings:
            is_attended = b.attendance_status == 'present'
            all_passengers_details.append({'name': b.student_name or (b.passenger.name if b.passenger else 'غير معروف'), 'type': 'فورم', 'attended': is_attended})
            if is_attended:
                trip_attended_count += 1
                if b.category:
                    cat_name = b.category.name
                    attendance_by_category[cat_name] = attendance_by_category.get(cat_name, 0) + 1

        for b in regular_bookings:
            is_attended = b.attendance_status == 'present'
            all_passengers_details.append({'name': b.passenger.name if b.passenger else 'غير معروف', 'type': 'حجز عادي', 'attended': is_attended})
            if is_attended and b.Trip.bus and b.Trip.bus.category:
                trip_attended_count += 1
                cat_name = b.Trip.bus.category.name
                attendance_by_category[cat_name] = attendance_by_category.get(cat_name, 0) + 1
        
        # =================================================================
        # ✅ --- بداية الإضافة الجديدة --- ✅
        # =================================================================
        # استدعاء الدالة المساعدة لجلب خطة السير لهذه الرحلة
        route_plan = get_route_plan_for_trip(trip)
        # =================================================================
        # ✅ --- نهاية الإضافة الجديدة --- ✅
        # =================================================================

        report_data.append({
            'trip': trip,
            'passengers': all_passengers_details,
            'attended_count': trip_attended_count,
            'total_count': len(all_passengers_details),
            'route_plan': route_plan, # <-- إضافة خطة السير هنا
        })
        
        total_passengers += len(all_passengers_details)
        total_attended += trip_attended_count

    # --- 5. تجهيز بيانات الجرافات ---
    overall_attendance_data = {'labels': ['حضر', 'غاب'], 'data': [total_attended, total_passengers - total_attended]}
    category_attendance_data = {'labels': list(attendance_by_category.keys()), 'data': list(attendance_by_category.values())}

    # --- 6. تجهيز البيانات النهائية للقالب ---
    context = {
        'title': "لوحة تحكم وتقارير الحضور",
        'report_data': report_data, # الآن هذه القائمة تحتوي على كل البيانات المطلوبة
        'categories': Category.objects.all(),
        'selected_date': selected_date_str,
        'selected_category_id': selected_category_id,
        'search_passenger_name': search_passenger_name,
        'passenger_bookings': passenger_bookings,
        'overall_attendance_json': json.dumps(overall_attendance_data),
        'category_attendance_json': json.dumps(category_attendance_data),
        'total_trips': trips_queryset.count(),
        'total_passengers': total_passengers,
        'total_attended': total_attended,
        'attendance_percentage': round((total_attended / total_passengers * 100) if total_passengers > 0 else 0, 2)
    }
    return render(request, 'admin/bus_report.html', context)

def mark_attendance_university_code(request):
    if request.method == 'POST':
        university_code = request.POST.get('university_code', None)  # كود الجامعة
        serial_code = request.POST.get('serial_code', None)  # كود الحجز (serial_code)

        if university_code and serial_code:
            # البحث عن الطالب باستخدام كود الجامعة
            student = passenger.objects.filter(university_code=university_code).first()
            if student:
                # البحث عن الحجز باستخدام serial_code
                booking = Booking.objects.filter(
                    passenger=student,
                    serial_code=serial_code,  # الحجز بناءً على كود الحجز الفريد
                    attendance_status="absent"  # الحجوزات التي لم يتم تسجيل حضورها
                ).first()

                if booking:
                    # تسجيل الحضور للحجز
                    booking.attendance_status = "present"
                    booking.status = "active"
                    booking.save()

                    # تحديث بيانات الطالب
                    if student.remaining_rides > 0:
                        student.rides_used += 1
                        student.save()

                    messages.success(request, f"تم تسجيل الحضور بنجاح للرحلة بكود الحجز: {serial_code}")
                else:
                    messages.info(request, "لا يوجد حجز مرتبط بكود الرحلة المدخل أو الحجز مسجل حضور مسبقًا.")
            else:
                messages.error(request, "كود الجامعة غير صحيح.")
        else:
            messages.error(request, "يرجى إدخال كود الجامعة وكود الحجز.")

    return render(request, 'check_university_code.html')
from django.shortcuts import render, redirect
from django.contrib import messages

# # ✅ 3. تأكد من وجود دالة mark_attendance الموحدة
# @csrf_exempt
# @require_POST
# def mark_attendance(request):
#     try:
#         booking_source = request.POST.get('source')
#         booking_id = int(request.POST.get('id'))

#         if booking_source == 'form':
#             reservation = FormReservation.objects.get(id=booking_id)
#             reservation.attendance_status = 'present'
#             reservation.save()
#         elif booking_source == 'booking':
#             booking = Booking.objects.get(id=booking_id)
#             booking.attendance_status = 'present'
#             booking.save()
#         else:
#             return JsonResponse({'success': False, 'error': 'مصدر الحجز غير معروف.'}, status=400)

#         return JsonResponse({'success': True, 'message': 'تم تسجيل الحضور بنجاح.'})
#     except Exception as e:
#         return JsonResponse({'success': False, 'error': str(e)}, status=400)

from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Booking

# def mark_attendance_qr(request):
#     if request.method == 'POST':
#         qr_data = request.POST.get('qr_data', None)  # البيانات المستخرجة من QR

#         if qr_data:
#             # تقسيم البيانات للحصول على university_code و serial_code
#             try:
#                 university_code, serial_code = qr_data.split('|')  # مثال: "123456|ABC123"
#             except ValueError:
#                 messages.error(request, "❌ بيانات QR غير صالحة.")
#                 return redirect('scan_qr')

#             # البحث عن الطالب باستخدام كود الجامعة
#             student = passenger.objects.filter(university_code=university_code).first()
#             if student:
#                 # البحث عن الحجز باستخدام serial_code
#                 booking = Booking.objects.filter(
#                     passenger=student,
#                     serial_code=serial_code,
#                     attendance_status="absent"  # الحجز لم يسجل حضوره مسبقًا
#                 ).first()

#                 if booking:
#                     # تحديث حالة الحضور
#                     booking.attendance_status = "present"
#                     booking.status = "active"
#                     booking.save()

#                     # تحديث عدد الرحلات المستخدمة
#                     if student.remaining_rides > 0:
#                         student.rides_used += 1
#                         student.save()

#                     messages.success(request, f"✅ تم تسجيل الحضور بنجاح للحجز: {serial_code}")
#                 else:
#                     messages.warning(request, "⚠️ لا يوجد حجز مرتبط بهذا الكود أو تم تسجيل الحضور مسبقًا.")
#             else:
#                 messages.error(request, "❌ كود الجامعة غير صحيح.")
#         else:
#             messages.error(request, "❌ يرجى مسح كود QR.")

#     return render(request, 'scan_qr.html')

import qrcode
from django.http import HttpResponse
from django.shortcuts import render
from .models import Booking

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import Booking, passenger

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import date
from django.contrib.auth.decorators import login_required
from .models import Booking, passenger

from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Booking, passenger

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import json
from django.utils import timezone

import qrcode
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Booking, passenger

@login_required
def generate_general_qr(request):
    scan_url = request.build_absolute_uri(reverse('scan_qr'))
    qr = qrcode.make(scan_url)
    response = HttpResponse(content_type="image/png")
    qr.save(response, "PNG")
    return response
@login_required
def scan_qr(request):
    # البحث عن الراكب باستخدام المستخدم الحالي
    student = passenger.objects.filter(user=request.user).first()
    
    if student:
        booking = Booking.objects.filter(passenger=student, attendance_status="absent").first()
        
        if booking:
            messages.success(request, "تم  التعرف علي الراكب و تلك بياناته")
        else:
            messages.warning(request, "⚠️ لا يوجد حجز نشط مسجل باسمك.")

    return render(request, 'scan_qr.html')
@csrf_exempt
@login_required
def scan_qr_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            trip_code = data.get("trip_code")
            university_code = data.get("university_code")
            qr_data = data.get("qr_data")

            if not trip_code or not university_code:
                return JsonResponse({"success": False, "message": "⚠️ بيانات الرحلة غير صحيحة."})

            # ✅ البحث عن الحجز
            booking = Booking.objects.filter(
                Trip__id=trip_code, 
                serial_code=university_code, 
                attendance_status="absent", 
                passenger__user=request.user
            ).first()

            if not booking:
                return JsonResponse({"success": False, "message": "⚠️ لا يوجد حجز مطابق لهذا المستخدم."})

            # ✅ الحصول على بيانات الراكب
            passenger_instance = booking.passenger

            # ✅ حساب عدد الرحلات المتبقية
            remaining_rides = passenger_instance.remaining_rides

            # ✅ التأكد من وجود رحلات كافية
            if remaining_rides >= 0:
                passenger_instance.rides_used += 1 
                passenger_instance.save()
            
            else:
                return JsonResponse({"success": False, "message": "⚠️ ليس لديك رحلات متبقية في اشتراكك!"})

            # ✅ تسجيل الحضور
            booking.attendance_status = "present"
            booking.save()

            return JsonResponse({
                "success": True,
                "message": f"✅ تم تسجيل الحضور للرحلة {booking.Trip.trip_name} بتاريخ {booking.Trip.date}.\n📉 انت دلوقتي في امان."
            })

        except Exception as e:
            return JsonResponse({"success": False, "message": f"⚠️ خطأ غير متوقع: {str(e)}"})

@csrf_exempt
def confirm_attendance(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            booking_id = data.get("booking_id", None)

            if booking_id:
                booking = Booking.objects.filter(id=booking_id, attendance_status="absent", passenger__user=request.user).first()
                
                if booking:
                    # تحديث الحضور فقط دون تغيير الرحلة أو أي بيانات أخرى
                    booking.attendance_status = "present"
                    booking.save()

                    if booking.passenger.remaining_rides > 0:
                        booking.passenger.rides_used += 1
                        booking.passenger.save()

                    return JsonResponse({"success": True, "message": "✅ تم تسجيل الحضور بنجاح."})

                return JsonResponse({"success": False, "message": "⚠️ لم يتم العثور على الحجز المحدد."})

            return JsonResponse({"success": False, "message": "⚠️ لم يتم إرسال معرف الحجز."})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "message": "⚠️ طلب غير صالح."})

    return JsonResponse({"success": False, "message": "⚠️ يجب إرسال الطلب بطريقة POST."})

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

def update_payment_status(request, booking_id):
    if request.method == "POST":
        try:
            if request.headers.get('Content-Type') == 'application/json':
                # معالجة البيانات كـ JSON
                data = json.loads(request.body)
                status = data.get('status')
            else:
                # معالجة البيانات كـ Form Data
                status = request.POST.get('status')

            if not status or status not in ['completed', 'prepaid']:
                return JsonResponse({"success": False, "error": "حالة غير صالحة."})

            booking = get_object_or_404(Booking, id=booking_id)
            booking.status = status
            booking.save()

            return JsonResponse({"success": True, "message": f"تم تحديث حالة الدفع إلى {status}"})

        except Booking.DoesNotExist:
            return JsonResponse({"success": False, "error": "الحجز غير موجود."})

    return JsonResponse({"success": False, "error": "طلب غير صالح."})




# from django.shortcuts import render, redirect
# from django.contrib.auth.decorators import login_required
# from django.utils.crypto import get_random_string
# from .models import passenger, SubscriptionTransaction
# # views.py

# def calculate_subscription_amount(subscription_type):
#     price_per_ride = {
#         12: 120,   # 12 رحلة
#         16: 160,   # 16 رحلة
#         22: 200,   # 22 رحلة
#         48: 400,   # ترم دراسي
#         96: 700    # سنة دراسية
#     }
#     return price_per_ride.get(subscription_type, 0)
# from django.db import IntegrityError

# from django.db import IntegrityError
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect
# from .models import SubscriptionTransaction, passenger, SubscriptionType

# # تعريف الدالة خارج العرض
# from decimal import Decimal

# def calculate_subscription_amount(subscription_type):
#     try:
#         subscription = SubscriptionType.objects.get(duration=subscription_type)
#         total_amount = subscription.included_trips * subscription.price_per_trip
#         fee_percentage = Decimal('1.02')  # استخدام Decimal للرسوم
#         total_amount_with_fee = round(total_amount * fee_percentage, 2)
#         return total_amount_with_fee
#     except SubscriptionType.DoesNotExist:
#         return Decimal('0.00')  # إعادة 0 كـ Decimal بدلاً من float

# from .models import SubscriptionType

# from django.shortcuts import render, redirect
# from django.db import IntegrityError
# from .models import SubscriptionType, SubscriptionTransaction

# @login_required
# def subscriptions_view(request):
#     student = passenger.objects.get(user=request.user)
#     subscriptions = SubscriptionType.objects.all()

#     # إضافة المبلغ الإجمالي لكل اشتراك
#     for subscription in subscriptions:
#         subscription.total_amount = calculate_subscription_amount(subscription.duration)

#     if request.method == 'POST':
#         subscription_type = int(request.POST.get('subscription_type'))
#         amount = calculate_subscription_amount(subscription_type)
#         transaction_number = request.POST.get('transaction_number')
#         transferred_from_number = request.POST.get('transferred_from_number')

#         if not transaction_number:
#             error_message = "رقم المعاملة غير صالح. الرجاء إدخال رقم معاملة صحيح."
#             return render(request, 'subscriptions.html', {
#                 'student': student,
#                 'subscriptions': subscriptions,
#                 'error_message': error_message
#             })

#         if SubscriptionTransaction.objects.filter(transaction_number=transaction_number).exists():
#             error_message = "رقم المعاملة مستخدم مسبقاً. الرجاء استخدام رقم آخر."
#             return render(request, 'subscriptions.html', {
#                 'student': student,
#                 'subscriptions': subscriptions,
#                 'error_message': error_message
#             })

#         try:
#             transaction = SubscriptionTransaction.objects.create(
#                 student=student,
#                 subscription_type=subscription_type,
#                 amount=amount,
#                 transaction_number=transaction_number,
#                 transferred_from_number=transferred_from_number,
#                 transfer_message=request.POST.get('transfer_message', '')
#             )
#             return redirect('subscription_success', transaction.id)
#         except IntegrityError:
#             error_message = "حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."
#             return render(request, 'subscriptions.html', {
#                 'student': student,
#                 'subscriptions': subscriptions,
#                 'error_message': error_message
#             })

#     return render(request, 'subscriptions.html', {'student': student, 'subscriptions': subscriptions})

# def subscription_success(request, transaction_id):
#     return render(request, 'subscription_success.html', {'transaction_id': transaction_id})

# def subscription_success(request, transaction_id):
#     return render(request, 'subscription_success.html', {'transaction_id': transaction_id})
from django.shortcuts import render, get_object_or_404
from .models import Subscription, passenger
from django.http import JsonResponse



from django.shortcuts import render, get_object_or_404
from django.shortcuts import render, get_object_or_404
from .models import Subscription, passenger

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from .models import passenger, Subscription

@login_required
def subscriptions_view(request, passenger_id=None):
    try:
        passenger_instance = None

        # جلب الراكب الحالي المرتبط باليوزر
        if passenger_id:
            passenger_instance = get_object_or_404(passenger, id=passenger_id)

        # عرض الاشتراكات حسب الفئة فقط إن وُجد راكب
        if passenger_instance:
            subscriptions = Subscription.objects.filter(category=passenger_instance.category)
        else:
            subscriptions = Subscription.objects.none()  # لا تعرض أي اشتراكات

    except passenger.DoesNotExist:
        passenger_instance = None
        subscriptions = Subscription.objects.none()

    context = {
        'passenger': passenger_instance,
        'subscriptions': subscriptions,
    }
    return render(request, 'subscriptions.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Subscription, SubscriptionBooking
from decimal import Decimal
import uuid
from .models import passenger  # إذا كان نموذجك في نفس ملف التطبيق
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal, ROUND_HALF_UP
from .models import InstallmentPlan, Subscription, Installment
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta
import uuid
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.conf import settings
from decimal import Decimal
from datetime import timedelta
import uuid, hmac, hashlib
from urllib.parse import urlencode

# استيراد المودلز
from .models import Subscription, passenger, InstallmentPlan, Installment, SubscriptionBooking

@login_required
def subscription_detail(request, subscription_id, passenger_id):
    subscription = get_object_or_404(Subscription, id=subscription_id)
    passenger_instance = get_object_or_404(passenger, id=passenger_id)
    installment_plans = subscription.installment_plans.all()

    base_price = subscription.price  # السعر الأساسي

    if request.method == "POST":
        payment_type = request.POST.get("payment_type")
        selected_plan_id = request.POST.get("installment_plan")
        merchant_order_id = str(uuid.uuid4())

        if 'pending_payment' in request.session:
            del request.session['pending_payment']

        if payment_type == "installment" and selected_plan_id:
            plan = get_object_or_404(InstallmentPlan, id=selected_plan_id)

            # السعر بعد الزيادة
            total_price = (base_price * (1 + plan.increase_percentage / 100)).quantize(Decimal("0.01"))

            percentages = plan.installment_percentages
            installment_amounts = [
                (total_price * (p / 100)).quantize(Decimal("0.01"))
                for p in percentages
            ]

            request.session['pending_payment'] = {
                'type': 'installment',
                'subscription_id': subscription.id,
                'passenger_id': passenger_instance.id,
                'plan_id': plan.id,
                'installment_amounts': [str(x) for x in installment_amounts],
                'first_payment': str(installment_amounts[0]),
                'merchant_order_id': merchant_order_id,
            }
            final_payment_amount = installment_amounts[0]  # أول قسط فقط

        else:  # دفع كامل
            total_price = (base_price * Decimal("1.02")).quantize(Decimal("0.01"))
            request.session['pending_payment'] = {
                'type': 'full',
                'subscription_id': subscription.id,
                'passenger_id': passenger_instance.id,
                'payment_amount': str(total_price),
                'merchant_order_id': merchant_order_id,
            }
            final_payment_amount = total_price

        # ✅ إنشاء الحجز كـ pending أول ما يبدأ الدفع
        SubscriptionBooking.objects.create(
            subscription=subscription,
            passenger=passenger_instance,
            transaction_code=merchant_order_id,
            payment_amount=Decimal(final_payment_amount),
            status="pending"
        )

        # --- منطق كاشير ---
        merchant_id = settings.KASHIER_ACCOUNT_KEY
        mode = settings.KASHIER_MODE
        amount_str = str(int(final_payment_amount))
        currency = 'EGP'

        def generate_kashier_hash(order):
            mid = merchant_id
            amount = order['amount']
            currency = order['currency']
            order_id = order['merchantOrderId']
            secret = settings.KASHIER_API_KEY  # ⚠️ خليها في settings
            path = f"/?payment={mid}.{order_id}.{amount}.{currency}"
            return hmac.new(secret.encode('utf-8'), path.encode('utf-8'), hashlib.sha256).hexdigest()

        order_data = {
            'amount': amount_str,
            'currency': currency,
            'merchantOrderId': merchant_order_id,
        }
        hash_signature = generate_kashier_hash(order_data)

        params = {
            'merchantId': merchant_id,
            'orderId': merchant_order_id,
            'amount': amount_str,
            'currency': currency,
            'allowedMethods': 'card,wallet',
            'merchantRedirect': request.build_absolute_uri(reverse('subscription_payment_success')),
            'failureRedirect': request.build_absolute_uri(reverse('subscription_payment_failed')),
            'redirectMethod': 'get',
            'hash': hash_signature,
            'mode': mode,
            'display': 'ar',
        }
        checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"
        return redirect(checkout_url)

    context = {
        'subscription': subscription,
        'passenger': passenger_instance,
        'installment_plans': installment_plans,
    }
    return render(request, 'subscription_detail.html', context)

@login_required
def pay_installment(request, installment_id ):
    """
    هذه الدالة تبدأ عملية الدفع لقسط فردي مستحق.
    """
    installment = get_object_or_404(Installment, id=installment_id)
    
    # التحقق من الصلاحية (أن المستخدم هو صاحب القسط)
    is_owner = hasattr(request.user, 'passenger') and request.user.passenger.id == installment.passenger.id
    if not (request.user.is_staff or is_owner):
        messages.error(request, "ليس لديك الصلاحية لدفع هذا القسط.")
        return redirect('index')

    # التحقق من أن القسط لم يتم دفعه بالفعل
    if installment.is_paid:
        messages.error(request, "هذا القسط تم دفعه بالفعل.")
        return redirect('installments_list', passenger_id=installment.passenger.id)

    # --- منطق كاشير (مُعاد استخدامه) ---
    merchant_order_id = f"INST-{installment.id}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    final_payment_amount = installment.amount

    # تخزين بيانات القسط في الـ session للتحقق منها بعد الدفع
    request.session['pending_installment_payment'] = {
        'installment_id': installment.id,
        'merchant_order_id': merchant_order_id,
    }

    merchant_id = settings.KASHIER_ACCOUNT_KEY
    mode = settings.KASHIER_MODE
    amount_str = str(int(final_payment_amount))
    currency = 'EGP'

    def generate_kashier_hash(order):
        mid = merchant_id
        amount = order['amount']
        currency = order['currency']
        order_id = order['merchantOrderId']
        secret = settings.KASHIER_API_KEY
        path = f"/?payment={mid}.{order_id}.{amount}.{currency}"
        return hmac.new(secret.encode('utf-8'), path.encode('utf-8'), hashlib.sha256).hexdigest()

    order_data = {
        'amount': amount_str,
        'currency': currency,
        'merchantOrderId': merchant_order_id,
    }
    hash_signature = generate_kashier_hash(order_data)

    # هنا، سنستخدم نفس صفحة النجاح والفشل الخاصة بالاشتراك،
    # ولكن الـ view الخاص بالنجاح سيحتاج إلى تعديل ليتعامل مع كلا الحالتين.
    params = {
        'merchantId': merchant_id,
        'orderId': merchant_order_id,
        'amount': amount_str,
        'currency': currency,
        'allowedMethods': 'card,wallet',
        'merchantRedirect': request.build_absolute_uri(reverse('subscription_payment_success')),
        'failureRedirect': request.build_absolute_uri(reverse('subscription_payment_failed')),
        'redirectMethod': 'get',
        'hash': hash_signature,
        'mode': mode,
        'display': 'ar',
    }
    checkout_url = f"https://payments.kashier.io/?{urlencode(params )}"
    return redirect(checkout_url)
# Anaconda_bus_APP/views.py

from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal

# تأكد من استيراد كل المودلز التي تحتاجها
from .models import Subscription, passenger, InstallmentPlan, Installment, SubscriptionBooking

@csrf_exempt
def subscription_payment_success(request):
    """
    يعالج عمليات الدفع الناجحة لكل من الاشتراكات الجديدة والأقساط الحالية.
    """
    order_id = request.GET.get("merchantOrderId")
    status = request.GET.get("paymentStatus")

    if status and status.upper() == "SUCCESS":
        
        # =================================================================
        # الحالة الأولى: التحقق من دفع اشتراك جديد
        # =================================================================
        subscription_data = request.session.get("pending_payment")
        if subscription_data and subscription_data["merchant_order_id"] == order_id:
            try:
                subscription = Subscription.objects.get(id=subscription_data['subscription_id'])
                passenger_instance = passenger.objects.get(id=subscription_data['passenger_id'])
                booking = SubscriptionBooking.objects.get(transaction_code=order_id)

                # إذا كان الاشتراك بنظام الأقساط
                if subscription_data['type'] == 'installment':
                    plan = InstallmentPlan.objects.get(id=subscription_data['plan_id'])
                    installment_amounts = [Decimal(x) for x in subscription_data['installment_amounts']]
                    start_date = timezone.now().date()

                    # إنشاء جميع الأقساط المستقبلية
                    for i, amount in enumerate(installment_amounts):
                        due_date = start_date + timedelta(days=plan.interval_days * i)
                        is_paid_status = (i == 0)  # القسط الأول فقط هو الذي تم دفعه الآن
                        Installment.objects.create(
                            plan=plan,
                            passenger=passenger_instance,
                            due_date=due_date,
                            amount=amount,
                            is_paid=is_paid_status
                        )

                    # تحديث حالة حجز الاشتراك
                    booking.status = "completed"
                    booking.payment_amount = Decimal(subscription_data['first_payment'])
                    booking.save()

                    # تحديث عدد الرحلات المتبقية للراكب
                    passenger_instance.subscription_duration += subscription.number_of_trips
                    passenger_instance.save()

                    messages.success(request, "تم دفع القسط الأول بنجاح! وتم تسجيل باقي الأقساط في حسابك.")
                    
                    # حذف بيانات الجلسة بعد الانتهاء
                    del request.session["pending_payment"]
                    # توجيه المستخدم إلى صفحة الأقساط ليرى النتيجة
                    return redirect("installments_list", passenger_id=passenger_instance.id)

                # إذا كان الاشتراك بالدفع الكامل
                else:
                    booking.status = "completed"
                    booking.payment_amount = Decimal(subscription_data["payment_amount"])
                    booking.save()

                    passenger_instance.subscription_duration += subscription.number_of_trips
                    passenger_instance.save()
                    messages.success(request, "✅ تم دفع الاشتراك بنجاح!")
                    
                    # حذف بيانات الجلسة بعد الانتهاء
                    del request.session["pending_payment"]
                    # توجيه المستخدم إلى صفحة النجاح العامة
                    return render(request, "success.html")

            except Exception as e:
                # في حالة حدوث أي خطأ أثناء معالجة البيانات
                return render(request, "failed.html", {"message": f"❌ خطأ أثناء حفظ الاشتراك: {str(e)}"})

        # =================================================================
        # الحالة الثانية: التحقق من دفع قسط حالي
        # =================================================================
        installment_data = request.session.get("pending_installment_payment")
        if installment_data and installment_data["merchant_order_id"] == order_id:
            try:
                installment = Installment.objects.get(id=installment_data['installment_id'])
                
                # تحديث حالة القسط إلى "مدفوع"
                installment.is_paid = True
                installment.payment_date = timezone.now()
                installment.save()

                messages.success(request, f"تم دفع القسط المستحق بتاريخ {installment.due_date.strftime('%d-%m-%Y')} بنجاح!")
                
                # حذف بيانات الجلسة بعد الانتهاء
                del request.session["pending_installment_payment"]
                # توجيه المستخدم إلى صفحة الأقساط ليرى التحديث
                return redirect("installments_list", passenger_id=installment.passenger.id)

            except Exception as e:
                # في حالة حدوث أي خطأ أثناء تحديث القسط
                return render(request, "failed.html", {"message": f"❌ خطأ أثناء تحديث القسط: {str(e)}"})

    # =================================================================
    # في حالة فشل الدفع أو عدم وجود بيانات مطابقة في الجلسة
    # =================================================================
    try:
        # محاولة تحديث حالة حجز الاشتراك إلى "ملغي" إذا كان موجوداً
        booking = SubscriptionBooking.objects.get(transaction_code=order_id)
        booking.status = "canceled"
        booking.save()
    except SubscriptionBooking.DoesNotExist:
        # لا يوجد حجز اشتراك بهذا الكود، وهذا طبيعي عند دفع قسط فردي
        pass

    return render(request, "failed.html", {"message": "❌ فشل الدفع أو تم إلغاؤه."})


def subscription_payment_failed(request):
    order_id = request.GET.get("merchantOrderId")
    try:
        booking = SubscriptionBooking.objects.get(transaction_code=order_id)
        booking.status = "canceled"
        booking.save()
    except SubscriptionBooking.DoesNotExist:
        pass

    return render(request, "failed.html", {"message": "❌ فشل الدفع أو تم إلغاؤه."})


@login_required
def installments_list(request, passenger_id):
    """
    عرض صفحة متابعة الأقساط الخاصة بالراكب مع ملخص للحالة المالية.
    """
    passenger_instance = get_object_or_404(passenger, id=passenger_id)
    
    # التحقق من الصلاحية: إما أن يكون المستخدم هو صاحب الحساب أو مشرفاً
    # نفترض أن لديك علاقة one-to-one بين User و passenger
    is_owner = hasattr(request.user, 'passenger') and request.user.passenger.id == passenger_instance.id
    if not (request.user.is_staff or is_owner):
        messages.error(request, "ليس لديك الصلاحية لعرض هذه الصفحة.")
        return redirect('index') # أو صفحة تسجيل الدخول

    # جلب جميع الأقساط المرتبطة بالراكب وترتيبها حسب تاريخ الاستحقاق
    installments = passenger_instance.installments.all().order_by("due_date")
    
    # ⭐ [تعديل رئيسي] حساب القيم الإجمالية والملخص
    if installments.exists():
        # حساب المبالغ باستخدام list comprehension لضمان الدقة مع Decimal
        paid_installments = installments.filter(is_paid=True)
        total_paid = sum(inst.amount for inst in paid_installments)
        total_amount = sum(inst.amount for inst in installments)
        remaining_amount = total_amount - total_paid
        
        # حساب عدد الأقساط
        paid_count = paid_installments.count()
        total_count = installments.count()
        
        # حساب نسبة التقدم المئوية مع تجنب القسمة على صفر
        progress_percentage = (paid_count / total_count * 100) if total_count > 0 else 0
        
        # جلب اسم الخطة من أول قسط (نفترض أن كل الأقساط تتبع نفس الخطة)
        plan_name = installments.first().plan.name
    else:
        # قيم افتراضية في حالة عدم وجود أي أقساط
        total_paid = Decimal('0.00')
        total_amount = Decimal('0.00')
        remaining_amount = Decimal('0.00')
        paid_count = 0
        total_count = 0
        progress_percentage = 0
        plan_name = "لا يوجد"

    # تجميع كل البيانات في الـ context لتمريرها إلى القالب
    context = {
        "passenger": passenger_instance,
        "installments": installments,
        "total_paid": total_paid,
        "total_amount": total_amount,
        "remaining_amount": remaining_amount,
        "paid_count": paid_count,
        "total_count": total_count,
        "progress_percentage": progress_percentage,
        "plan_name": plan_name,
    }
    
    return render(request, "installments_list.html", context)
# /your_app/views.py

from django.http import JsonResponse
from decimal import Decimal

# ... (باقي الـ imports والدوال الأخرى )
from django.http import JsonResponse

# /your_app/views.py

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from decimal import Decimal

# استيراد المودلز الخاصة بك
from .models import InstallmentPlan 

# ... (باقي الـ imports والدوال الأخرى )
from django.http import JsonResponse
from django.utils.timezone import now, timedelta

@login_required
def get_installment_plan_details(request, plan_id):
    try:
        plan = InstallmentPlan.objects.get(id=plan_id)
        subscription = plan.subscription

        # السعر بعد الزيادة
        total_price = (subscription.price * (1 + plan.increase_percentage / 100)).quantize(Decimal("0.01"))

        # حساب الأقساط بناءً على النسب
        percentages = plan.installment_percentages
        installment_amounts = [
            (total_price * (p / 100)).quantize(Decimal("0.01")) for p in percentages
        ]

        # مواعيد الاستحقاق
        due_dates = [
            (now().date() + timedelta(days=plan.interval_days * i)).strftime("%Y-%m-%d")
            for i in range(plan.number_of_installments)
        ]

        return JsonResponse({
            "total_subscription_price": float(total_price),
            "number_of_installments": plan.number_of_installments,
            "interval_days": plan.interval_days,
            "installments": [
                {
                    "percentage": float(percentages[i]),
                    "amount": float(installment_amounts[i]),
                    "due_date": due_dates[i],
                }
                for i in range(plan.number_of_installments)
            ]
        })
    except InstallmentPlan.DoesNotExist:
        return JsonResponse({"error": "الخطة غير موجودة"}, status=404)

from django.shortcuts import render, redirect, get_object_or_404
from .models import Car
from .forms import CarBookingForm

import requests
from django.shortcuts import render, get_object_or_404, redirect
from .forms import CarBookingForm
from .models import Car

# # وظيفة إرسال رسالة WhatsApp
# def send_whatsapp_message(user_phone, car_name):
#     url = "https://graph.facebook.com/v16.0/539635585902816/messages"  # استبدل بـ معرف رقم الهاتف الخاص بك
#     headers = {
#         "Authorization": "Bearer EACCJbxPGkPwBO7wRZAImvkwvMtvvnanV8PoQ3YS8EAPezP3NHn2iZBUnR3M2T22YyWeZAIzvsEFWFlDpuluXCsj6eZBlDw9OlsolZCAGRWF1H0niK5pVbz2QRgGGFpoxRhdxJRcIXRDZACKgU8XamJ3QywgIVqK72kyoRVCLBfICdmD7dXjZBDzk7soZBYIAzWpCWtfbpfhodiYeG6AZAOOZAJ1v26MkZBqmQZDZD",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": user_phone,  # رقم الهاتف بصيغة دولية
#         "type": "text",
#         "text": {
#             "body": f"تم تأكيد حجز السيارة: {car_name}\nشكراً لاستخدام خدماتنا! 🚗"
#         }
#     }

#     response = requests.post(url, headers=headers, json=payload)
#     if response.status_code == 200:
#         print("تم إرسال الرسالة بنجاح!")
#     else:
#         print("خطأ في إرسال الرسالة:", response.json())

# # دالة حجز السيارة
# from django.core.exceptions import ValidationError

# def send_confirmation_message(phone_number, car_name, start_date, end_date):
#     # في التطوير، طباعة الرسالة بدل الإرسال
#     print(f"تم تأكيد الحجز للسيارة {car_name} من {start_date} إلى {end_date} لرقم الهاتف: {phone_number}")

# def book_car(request):
#     if request.method == "POST":
#         form = CarBookingForm(request.POST)
#         car_id = request.POST.get("car_id")
#         car = get_object_or_404(Car, id=car_id)

#         if form.is_valid():
#             booking = form.save(commit=False)
#             booking.car = car
#             booking.save()

#             # إرسال رسالة تأكيد
#             send_confirmation_message(
#                 booking.phone_number,
#                 booking.car.name,
#                 booking.start_date,
#                 booking.end_date
#             )

#             return redirect('booking_success')
#         else:
#             print("Form Errors:", form.errors)

#     else:
#         form = CarBookingForm()

#     cars = Car.objects.filter(is_available=True)
#     return render(request, 'car_booking.html', {'form': form, 'cars': cars})

# def booking_success(request):
#     return render(request, 'success.html')
from django.shortcuts import render
from .models import Car

from django.shortcuts import render, get_object_or_404
from .models import Car
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Car, CarBooking
from .forms import CarBookingForm
from django.core.exceptions import ValidationError
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Car
from .forms import CarBookingForm
import time
import hmac
import hashlib
from urllib.parse import urlencode
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.timezone import now
from datetime import datetime
from .models import Car, CarBooking
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Car, CarBooking
from .forms import CarBookingForm
from django.utils.timezone import now


# 🔍 **View: عرض قائمة السيارات**
def car_list(request):
    unique_models = Car.objects.values_list('model', flat=True).distinct()
    category = request.GET.get('category', '')
    search_query = request.GET.get('q', '').strip()

    cars = Car.objects.filter(model=category) if category else Car.objects.all()

    # البحث عن السيارات بالاسم أو الماركة أو الموديل
    if search_query:
        cars = cars.filter(
            Q(name__icontains=search_query) |
            Q(brand__icontains=search_query) |
            Q(model__icontains=search_query)
        )

    context = {
        'unique_models': unique_models,
        'cars': cars,
        'category': category,
        'search_query': search_query,
        'cars_count': cars.count(),
        'models_count': unique_models.count() if hasattr(unique_models, 'count') else len(unique_models),
    }
    return render(request, 'car_list.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Car, CarBooking  # تأكد أن CarBooking هو اسم الموديل
from .forms import CarBookingForm

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Car, CarBooking
from .forms import CarBookingForm
from datetime import datetime
from django.db.models import Q
from datetime import datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q
from .models import Car, CarBooking
from .forms import CarBookingForm

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Car, CarBooking
from .forms import CarBookingForm
from datetime import datetime
from django.db.models import Q
import requests

# تنسيق رقم الهاتف
def format_number(number):
    number = number.strip()
    if not number.startswith("+20"):
        number = "+20" + number.lstrip("0")
    return number

# بيانات API للواتساب
INSTANCE_ID = "instance105329"
API_TOKEN = settings.ULTRAMSG_API_TOKEN
URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

def telegram_success_page(request):
    """Custom success page for Telegram bot connection"""
    return render(request, 'telegram_success.html')

def send_whatsapp_message(phone_number, message):
    payload = {
        "token": API_TOKEN,
        "to": phone_number,
        "body": message
    }
    response = requests.post(URL, json=payload)
    return response.json()


EGYPT_BBOX = "24.696775,22.0,36.895,31.667"
MAP_HTTP_HEADERS = {
    "User-Agent": "AllenBus/1.0 (maps@allen.allentravels.com)",
}


def _map_service_url(setting_name):
    return getattr(settings, setting_name, "").strip().rstrip("/")


def _map_service_urls(*setting_names):
    urls = []
    for setting_name in setting_names:
        value = _map_service_url(setting_name)
        if value and value not in urls:
            urls.append(value)
    return urls


def _map_error_response(message, status=503):
    return JsonResponse({"error": message}, status=status)


def _join_map_parts(parts):
    unique_parts = []
    for part in parts:
        value = str(part).strip() if part is not None else ""
        if value and value not in unique_parts:
            unique_parts.append(value)
    return ", ".join(unique_parts)


def _serialize_map_result(label, lat, lng, display_name, governorate="", source=""):
    return {
        "label": label,
        "lat": lat,
        "lng": lng,
        "display_name": display_name,
        "governorate": governorate,
        "source": source,
        "country_code": "",
    }


def _photon_feature_to_result(feature):
    geometry = feature.get("geometry", {})
    coordinates = geometry.get("coordinates") or []
    if len(coordinates) < 2:
        return None

    props = feature.get("properties", {})
    lat = float(coordinates[1])
    lng = float(coordinates[0])
    governorate = props.get("state") or props.get("county") or props.get("city") or ""
    label = (
        props.get("name")
        or props.get("street")
        or props.get("city")
        or props.get("county")
        or props.get("state")
        or "موقع"
    )
    display_name = _join_map_parts([
        props.get("name"),
        props.get("street"),
        props.get("district"),
        props.get("suburb"),
        props.get("city"),
        props.get("county"),
        props.get("state"),
        props.get("country"),
    ])
    return _serialize_map_result(
        label=label,
        lat=lat,
        lng=lng,
        display_name=display_name or label,
        governorate=governorate,
        source="photon",
    ) | {"country_code": (props.get("countrycode") or "").upper()}


def _nominatim_entry_to_result(entry):
    address = entry.get("address", {})
    lat = float(entry["lat"])
    lng = float(entry["lon"])
    governorate = (
        address.get("state")
        or address.get("province")
        or address.get("county")
        or address.get("city")
        or ""
    )
    label = (
        address.get("road")
        or address.get("neighbourhood")
        or address.get("suburb")
        or address.get("city")
        or address.get("town")
        or address.get("village")
        or entry.get("display_name")
        or "موقع"
    )
    return _serialize_map_result(
        label=label,
        lat=lat,
        lng=lng,
        display_name=entry.get("display_name") or label,
        governorate=governorate,
        source="nominatim",
    ) | {"country_code": (address.get("country_code") or "").upper()}


def _serialize_car_for_client(car):
    fuel_type = getattr(car, "fuel_type", "") or "غير محدد"
    return {
        "id": car.id,
        "title": f"{car.brand} {car.name}".strip(),
        "brand": car.brand,
        "name": car.name,
        "model": car.model,
        "description": car.description or "",
        "seats": car.seats,
        "transmission": car.transmission,
        "fuel_type": fuel_type,
        "image_url": car.image.url if car.image else "",
        "panorama_url": car.panorama_image.url if car.panorama_image else "",
        "pricing": {
            "price_per_km_0_100": float(car.price_per_km_0_100 or 0),
            "price_per_km_101_200": float(car.price_per_km_101_200 or 0),
            "price_per_km_201_300": float(car.price_per_km_201_300 or 0),
            "price_per_km_301_400": float(car.price_per_km_301_400 or 0),
            "price_per_km_401_500": float(car.price_per_km_401_500 or 0),
            "price_per_km_501_600": float(car.price_per_km_501_600 or 0),
            "price_per_km_601_700": float(car.price_per_km_601_700 or 0),
            "price_per_km_701_800": float(car.price_per_km_701_800 or 0),
            "price_per_km_801_900": float(car.price_per_km_801_900 or 0),
            "price_per_km_901_1000": float(car.price_per_km_901_1000 or 0),
            "price_per_km_above_1000": float(car.price_per_km_above_1000 or 0),
            "DAY_USE": float(car.DAY_USE or 0),
            "day_use_12_price": float(car.day_use_12_price or 0),
            "day_use_10_price": float(car.day_use_10_price or 0),
            "day_use_8_price": float(car.day_use_8_price or 0),
            "airport_pickup_price": float(car.airport_pickup_price or 0),
        },
    }


def map_search(request):
    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    try:
        limit = min(max(int(request.GET.get("limit", 6)), 1), 10)
    except (TypeError, ValueError):
        limit = 6
    lat = request.GET.get("lat", "").strip()
    lng = request.GET.get("lng", "").strip()
    photon_urls = _map_service_urls("SELF_HOSTED_PHOTON_URL", "PUBLIC_PHOTON_URL")
    nominatim_urls = _map_service_urls("SELF_HOSTED_NOMINATIM_URL")

    for photon_url in photon_urls:
        try:
            params = {
                "q": query,
                "limit": limit,
                "bbox": EGYPT_BBOX,
            }
            if lat and lng:
                params["lat"] = lat
                params["lon"] = lng

            response = requests.get(
                f"{photon_url}/api",
                params=params,
                timeout=8,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            features = response.json().get("features", [])
            results = [
                item for item in (_photon_feature_to_result(feature) for feature in features)
                if item and item.get("country_code") in ("", "EG")
            ]
            return JsonResponse({"results": results})
        except (ValueError, requests.RequestException):
            continue

    for nominatim_url in nominatim_urls:
        try:
            response = requests.get(
                f"{nominatim_url}/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "countrycodes": "eg",
                    "accept-language": "ar",
                    "limit": limit,
                },
                timeout=8,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            entries = response.json()
            results = [
                item for item in (_nominatim_entry_to_result(entry) for entry in entries)
                if item.get("country_code") in ("", "EG")
            ]
            return JsonResponse({"results": results})
        except (ValueError, requests.RequestException):
            continue

    return _map_error_response("خدمة البحث غير متاحة حاليًا", 502)


def map_reverse(request):
    try:
        lat = float(request.GET.get("lat", ""))
        lng = float(request.GET.get("lng", ""))
    except (TypeError, ValueError):
        return _map_error_response("إحداثيات غير صالحة", 400)

    photon_urls = _map_service_urls("SELF_HOSTED_PHOTON_URL", "PUBLIC_PHOTON_URL")
    nominatim_urls = _map_service_urls("SELF_HOSTED_NOMINATIM_URL")

    for photon_url in photon_urls:
        try:
            response = requests.get(
                f"{photon_url}/reverse",
                params={"lat": lat, "lon": lng},
                timeout=8,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            features = response.json().get("features", [])
            if not features:
                return _map_error_response("لم يتم العثور على عنوان لهذه النقطة", 404)

            result = _photon_feature_to_result(features[0])
            if not result:
                return _map_error_response("تعذر قراءة نتيجة العنوان من Photon", 502)
            return JsonResponse(result)
        except (ValueError, requests.RequestException, KeyError):
            continue

    for nominatim_url in nominatim_urls:
        try:
            response = requests.get(
                f"{nominatim_url}/reverse",
                params={
                    "lat": lat,
                    "lon": lng,
                    "format": "jsonv2",
                    "addressdetails": 1,
                    "accept-language": "ar",
                },
                timeout=8,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            payload = response.json()
            return JsonResponse(_nominatim_entry_to_result(payload))
        except (ValueError, requests.RequestException, KeyError):
            continue

    return _map_error_response("خدمة العنوان غير متاحة حاليًا", 502)


def map_route(request):
    try:
        from_lat = float(request.GET.get("from_lat", ""))
        from_lng = float(request.GET.get("from_lng", ""))
        to_lat = float(request.GET.get("to_lat", ""))
        to_lng = float(request.GET.get("to_lng", ""))
    except (TypeError, ValueError):
        return _map_error_response("إحداثيات المسار غير صالحة", 400)

    osrm_urls = _map_service_urls("SELF_HOSTED_OSRM_URL", "PUBLIC_OSRM_URL")
    valhalla_urls = _map_service_urls("SELF_HOSTED_VALHALLA_URL")

    for osrm_url in osrm_urls:
        try:
            response = requests.get(
                f"{osrm_url}/route/v1/driving/{from_lng},{from_lat};{to_lng},{to_lat}",
                params={"overview": "full", "geometries": "geojson"},
                timeout=15,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            payload = response.json()
            routes = payload.get("routes", [])
            if not routes:
                return _map_error_response("خدمة المسارات لم ترجع أي طريق", 404)

            route = routes[0]
            points = [[point[1], point[0]] for point in route["geometry"]["coordinates"]]
            return JsonResponse({
                "distance_km": round(float(route.get("distance", 0)) / 1000, 2),
                "duration_min": round(float(route.get("duration", 0)) / 60, 1),
                "geometry": points,
                "provider": "osrm",
            })
        except (ValueError, requests.RequestException, KeyError):
            continue

    for valhalla_url in valhalla_urls:
        try:
            payload = {
                "locations": [
                    {"lat": from_lat, "lon": from_lng},
                    {"lat": to_lat, "lon": to_lng},
                ],
                "costing": "auto",
                "format": "osrm",
                "shape_format": "geojson",
                "language": "en-US",
            }
            response = requests.get(
                f"{valhalla_url}/route",
                params={"json": json.dumps(payload)},
                timeout=15,
                headers=MAP_HTTP_HEADERS,
            )
            response.raise_for_status()
            route_data = response.json().get("routes", [])
            if not route_data:
                return _map_error_response("خدمة المسارات لم ترجع أي طريق", 404)

            route = route_data[0]
            geometry = route.get("geometry", {})
            coordinates = geometry.get("coordinates") or []
            points = [[point[1], point[0]] for point in coordinates if len(point) >= 2]
            distance_meters = float(route.get("distance", 0))

            return JsonResponse({
                "distance_km": round(distance_meters / 1000, 2),
                "duration_min": round(float(route.get("time", 0)) / 60, 1),
                "geometry": points,
                "provider": "valhalla",
            })
        except (ValueError, requests.RequestException, KeyError):
            continue

    return _map_error_response("خدمة حساب المسار غير متاحة حاليًا", 502)


def car_detail(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    comparison_cars = [
        _serialize_car_for_client(item)
        for item in Car.objects.filter(Q(is_available=True) | Q(id=car.id)).distinct().order_by('seats', 'brand', 'name')
    ]

    if request.method == "POST":
        form = CarBookingForm(request.POST)
        if form.is_valid():
            trip_type = request.POST.get('trip_type')
            go_date_str = request.POST.get("go_date")
            return_date_str = request.POST.get("return_date")

            go_date = datetime.strptime(go_date_str, '%Y-%m-%d').date() if go_date_str else None
            return_date = datetime.strptime(return_date_str, '%Y-%m-%d').date() if return_date_str else None

            # بيانات الحجز
            booking_data = form.cleaned_data
            booking_data['car_id'] = car.id
            booking_data['trip_type'] = trip_type
            booking_data['go_date'] = go_date
            booking_data['return_date'] = return_date

            # تخزين بيانات الحجز مؤقتًا في الجلسة
            request.session['pending_booking'] = booking_data

            return redirect('booking_success')  # هنا نوجه المستخدم لصفحة الدفع (success)

        else:
            messages.error(request, "❌ هناك خطأ في البيانات!")

    else:
        form = CarBookingForm()

    return render(request, 'car_detail.html', {
        'car': car,
        'form': form,
        'car_fuel_type': getattr(car, 'fuel_type', '') or 'غير محدد',
        'car_image_url': car.image.url if car.image else '',
        'car_panorama_url': car.panorama_image.url if car.panorama_image else '',
        'comparison_cars': comparison_cars,
        'map_style_url': settings.SELF_HOSTED_MAP_DARK_STYLE_URL or settings.SELF_HOSTED_MAP_STYLE_URL,
        'map_tile_url': settings.SELF_HOSTED_TILE_URL,
        'map_tile_attribution': settings.SELF_HOSTED_TILE_ATTRIBUTION,
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Car, CarBooking, Booking  # عدّل المسار حسب مشروعك
from .utils import format_number, send_whatsapp_message

def booking_success(request):
    # جلب بيانات الحجز المؤقتة من الجلسة
    booking_data = request.session.get('pending_booking')
    if not booking_data:
        messages.error(request, "❌ لا توجد عملية حجز قيد التنفيذ.")
        return redirect('home')  # أو أي صفحة مناسبة

    car = get_object_or_404(Car, id=booking_data['car_id'])

    # التحقق من التعارض مع حجوزات أخرى مؤكدة
    conflicting = CarBooking.objects.filter(
        car=car,
        status='confirmed'
    ).filter(
        Q(go_date__lte=booking_data['return_date'] or booking_data['go_date'],
          return_date__gte=booking_data['go_date'] or booking_data['return_date'])
    )

    if conflicting.exists():
        messages.error(request, "❌ لا يمكن الحجز في هذه التواريخ، السيارة محجوزة بالفعل.")
        return redirect('car_detail', car_id=car.id)

    # حفظ الحجز بعد التأكيد
    booking = CarBooking(
        car=car,
        name=booking_data['name'],
        phone_number=format_number(booking_data['phone_number']),
        go_date=booking_data['go_date'],
        return_date=booking_data['return_date'],
        status='confirmed'
    )
    booking.save()

    # إرسال رسالة واتساب لتأكيد الحجز
    send_whatsapp_message(booking.phone_number, f"✅ تم تأكيد حجزك للسيارة {car}.")

    # حذف البيانات المؤقتة من الجلسة
    del request.session['pending_booking']

    # توليد رابط Telegram فريد للحجز
    telegram_link = None
    try:
        from Anaconda_bus_APP.bot.utils import generate_telegram_link

        if hasattr(request.user, 'passenger'):
            # إنشاء حجز Booking عادي مرتبط بالراكب
            main_booking = Booking.objects.create(
                passenger=request.user.passenger,
                user=request.user,
                status='confirmed',
                payment_method='cash',
                transaction_number=f"CAR-{booking.id}",
                serial_code=f"CAR-{booking.id}"
            )
            # توليد الرابط الفريد للبوت
            telegram_link = generate_telegram_link(main_booking.id)

    except Exception as e:
        print(f"Error generating Telegram link: {e}")

    # عرض صفحة النجاح مع رابط Telegram الفريد
    return render(request, 'success.html', {
        'booking': booking, 
        'telegram_link': telegram_link,
        'telegram_bot_username': '@AllenTravelAi_bot'
    })
from .models import CarBooking
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_time
from urllib.parse import urlencode
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import quote
import uuid
import json
import hmac
import hashlib
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
import uuid
import hmac
import hashlib
import json
from urllib.parse import urlencode
import uuid
import hmac
import hashlib
import json
import random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.conf import settings
import json, random, hmac, hashlib
from urllib.parse import urlencode
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import hmac, hashlib, json, random
from urllib.parse import urlencode
from django.conf import settings

import json
import random
import hmac
import hashlib
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import random
import logging
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import random
import logging
import hmac
import hashlib
from urllib.parse import urlencode
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import hmac
import hashlib
# views.py

import hmac
import hashlib
import json
import logging
import random
from urllib.parse import urlencode
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import random
import hmac
import hashlib
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from urllib.parse import urlencode

#Copy and paste this code in your Backend
import hmac
import hashlib
import hmac
import hashlib


@csrf_exempt
@require_POST
def create_car_payment(request):
    try:
        data = json.loads(request.body)

        total_amount = Decimal(str(data.get('total_price', 0))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        payment_percentage = int(data.get('payment_percentage', 100))
        paid_amount = (total_amount * Decimal(payment_percentage) / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        customer_name = (data.get('customer_name') or '').strip()
        phone_number = (data.get('phone_number') or '').strip()
        trip_type = (data.get('trip_type') or '').strip()
        go_date_str = (data.get('go_date') or '').strip()
        return_date_str = (data.get('return_date') or '').strip()
        go_time_str = (data.get('go_time') or '').strip()
        back_time_str = (data.get('back_time') or '').strip()
        car_id = data.get('car_id')
        from_location = (data.get('from') or '').strip()
        to_location = (data.get('to') or '').strip()
        distance_km = data.get('distance_km')

        if total_amount <= 0:
            return JsonResponse({'error': 'المبلغ غير صالح'}, status=400)

        if payment_percentage not in (50, 100):
            return JsonResponse({'error': 'نسبة الدفع غير صالحة'}, status=400)

        if not customer_name or not phone_number:
            return JsonResponse({'error': 'الاسم ورقم الهاتف مطلوبان لإكمال الحجز'}, status=400)

        if not trip_type:
            return JsonResponse({'error': 'نوع الرحلة مطلوب'}, status=400)

        if not from_location or not to_location:
            return JsonResponse({'error': 'نقطتا الانطلاق والوصول مطلوبتان'}, status=400)

        go_date = parse_date(go_date_str)
        return_date = parse_date(return_date_str) if return_date_str else None
        go_time = parse_time(go_time_str) if go_time_str else None
        back_time = parse_time(back_time_str) if back_time_str else None

        if not go_date:
            return JsonResponse({'error': 'تاريخ الذهاب مطلوب لهذا النوع من الرحلات'}, status=400)

        if trip_type == 'round_trip' and not return_date:
            return JsonResponse({'error': 'تاريخ العودة مطلوب لهذا النوع من الرحلات'}, status=400)

        if return_date and return_date < go_date:
            return JsonResponse({'error': 'تاريخ العودة يجب أن يكون بعد أو مساويًا لتاريخ الذهاب'}, status=400)

        car = Car.objects.filter(id=car_id).first()
        if not car:
            return JsonResponse({'error': 'السيارة غير موجودة'}, status=404)

        booking_start = go_date
        booking_end = return_date or go_date

        overlapping = CarBooking.objects.filter(
            car_id=car_id,
            status__in=['pending', 'confirmed']
        ).filter(
            go_date__isnull=False,
            go_date__lte=booking_end
        ).filter(
            Q(return_date__isnull=True, go_date__gte=booking_start) |
            Q(return_date__gte=booking_start)
        )

        if overlapping.exists():
            return JsonResponse({'error': 'السيارة محجوزة بالفعل في هذه الفترة. الرجاء اختيار تاريخ آخر.'}, status=400)

        booking = CarBooking.objects.create(
            car=car,
            customer_name=customer_name,
            phone_number=phone_number,
            trip_type=trip_type,
            go_date=go_date,
            return_date=return_date,
            go_time=go_time,
            back_time=back_time,
            status='pending',
            payment_percentage=payment_percentage,
            from_location=from_location,
            to_location=to_location,
            distance_km=Decimal(str(distance_km)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if distance_km not in (None, '') else None,
            total_price=total_amount,
            paid_amount=paid_amount
        )

       
        merchant_order_id = f"car-{booking.id}"
        booking.merchant_order_id = merchant_order_id
        booking.save()

        merchant_id = settings.KASHIER_ACCOUNT_KEY
        mode = settings.KASHIER_MODE
        currency = 'EGP'
        amount_str = str(int(paid_amount))

        order_data = {
            'amount': amount_str,
            'currency': currency,
            'merchantOrderId': merchant_order_id,
        }

        hash_signature = generateKashierOrderHash(order_data)

        params = {
            'merchantId': merchant_id,
            'orderId': merchant_order_id,
            'amount': amount_str,
            'currency': currency,
            'allowedMethods': 'card,wallet,bank_installments',
            'merchantRedirect': 'https://allen.allentravels.com/allen/car/payment/success/',
            'failureRedirect': 'https://allen.allentravels.com/allen/car/payment/failed/',
            'redirectMethod': 'get',
            'brandColor': '#ff0000',
            'display': 'ar',
            'hash': hash_signature,
            'mode': mode,
        }

        checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"

        return JsonResponse({
            'checkout_url': checkout_url,
            'order_id': merchant_order_id
        })

    except Exception as e:
        logging.getLogger(__name__).exception("Kashier Payment Error")
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


def car_payment_success(request):
    status = request.GET.get("paymentStatus")
    merchant_order_id = request.GET.get("merchantOrderId")

    try:
        booking = CarBooking.objects.get(merchant_order_id=merchant_order_id)
    except CarBooking.DoesNotExist:
        return render(request, "success.html", {
            "message": "❌ لم يتم العثور على الحجز.",
            "order_id": merchant_order_id
        })

    if status == "SUCCESS":
        booking.status = 'confirmed'
        booking.save()

        formatted_customer_number = format_number(booking.phone_number)
        customer_message = (
            f"🚗 مرحبًا {booking.customer_name}!\n\n"
            f"✅ تم تأكيد حجز سيارتك {booking.car.name}\n"
            f"نوع الرحلة: {booking.get_trip_type_display()}\n"
        )

        if booking.trip_type in ['one_way_go', 'round_trip'] and booking.go_date:
            customer_message += f"تاريخ الذهاب: {booking.go_date.strftime('%Y-%m-%d')}\n"
        if booking.trip_type in ['one_way_return'] and booking.return_date:
            customer_message += f"تاريخ العودة: {booking.return_date.strftime('%Y-%m-%d')}\n"
        if booking.trip_type == 'round_trip' and booking.return_date:
            customer_message += f"تاريخ العودة: {booking.return_date.strftime('%Y-%m-%d')}\n"

        customer_message += "\nشكراً لاستخدامك خدمتنا!"
        send_whatsapp_message(formatted_customer_number, customer_message)

        if booking.car.car_driver_number:
            formatted_driver_number = format_number(booking.car.car_driver_number)
            driver_message = (
                f"📢 تنبيه حجز جديد:\n"
                f"----------------------\n"
                f"🚗 السيارة: {booking.car.name}\n"
                f"👤 العميل: {booking.customer_name}\n"
                f"📞 الهاتف: {booking.phone_number}\n"
                f"🔄 نوع الرحلة: {booking.get_trip_type_display()}\n"
            )

            if booking.trip_type in ['one_way_go', 'round_trip', 'day_use_12', 'day_use_10', 'day_use_8', 'airport_pickup'] and booking.go_date:
                driver_message += f"📅 تاريخ الذهاب: {booking.go_date.strftime('%Y-%m-%d')}\n"
            if booking.trip_type in ['one_way_return'] and booking.return_date:
                driver_message += f"📅 تاريخ العودة: {booking.return_date.strftime('%Y-%m-%d')}\n"
            if booking.trip_type == 'round_trip' and booking.return_date:
                driver_message += f"📅 تاريخ العودة: {booking.return_date.strftime('%Y-%m-%d')}\n"

            if booking.from_location and booking.to_location:
                google_maps_link = f"https://www.google.com/maps/dir/{quote(booking.from_location)}/{quote(booking.to_location)}"
                driver_message += (
                    f"\n📍 مسار الرحلة:\n"
                    f"----------------------\n"
                    f"🏁 نقطة البداية: {booking.from_location}\n"
                    f"🏁 نقطة النهاية: {booking.to_location}\n"
                    f"🗺️ رابط المسار: {google_maps_link}\n"
                )

            driver_message += (
                f"\n💵 معلومات الدفع:\n"
                f"----------------------\n"
                f"💰 نسبة الدفع: {booking.get_payment_percentage_display()}\n"
                f"💲 المبلغ الإجمالي: {booking.total_price:.2f} جنيه\n"
                f"💳 المبلغ المدفوع: {booking.paid_amount:.2f} جنيه\n"
            )

            if booking.payment_percentage == 50:
                remaining_amount = booking.total_price - booking.paid_amount
                driver_message += f"🔄 المبلغ المتبقي: {remaining_amount:.2f} جنيه\n"

            send_whatsapp_message(formatted_driver_number, driver_message)

        return render(request, "success.html", {
            "message": "✅ تم الدفع بنجاح!",
            "order_id": merchant_order_id,
            "booking": booking
        })

    return render(request, "success.html", {
        "message": "❌ فشل الدفع أو تم إلغاؤه.",
        "order_id": merchant_order_id
    })


def payment_verify(request):
    status = request.GET.get("status")
    order_id = request.GET.get("orderId")

    if status == "PAID":
        return JsonResponse({"message": "تم الدفع بنجاح!"})
    return JsonResponse({"message": "فشل في الدفع أو تم إلغاؤه."})


def generateKashierOrderHash(order):
    mid = settings.KASHIER_ACCOUNT_KEY
    amount = order['amount']
    currency = order['currency']
    orderId = order['merchantOrderId']

    full_secret = settings.KASHIER_API_KEY
    secret = full_secret.split('$')[-1]

    path = f"/?payment={mid}.{orderId}.{amount}.{currency}"
    return hmac.new(secret.encode('utf-8'), path.encode('utf-8'), hashlib.sha256).hexdigest()
@csrf_exempt
@require_POST
def trip_paymentgateway(request):
    try:
        data = request.POST
        total_amount = float(data.get('total_amount', 0))
        trip_id = data.get('trip_id')
        selected_seats_raw = data.get('selected_seats', '[]')

        try:
            selected_seats = json.loads(selected_seats_raw)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'تنسيق المقاعد غير صحيح'}, status=400)

        if not selected_seats or not trip_id or total_amount <= 0:
            return JsonResponse({'error': 'البيانات غير مكتملة أو المبلغ غير صحيح'}, status=400)

        # ✅ إعدادات كاشير
        order_id = str(random.randint(100000, 999999))
        merchant_id = settings.KASHIER_ACCOUNT_KEY
        mode = settings.KASHIER_MODE
        currency = 'EGP'
        amount_str = str(int(total_amount))  # ✔️ بدون فواصل عشرية

        # ✅ تجهيز بيانات التوقيع
        order_data = {
            'amount': amount_str,
            'currency': currency,
            'merchantOrderId': order_id,
        }

        # ✅ توليد التوقيع
        hash_signature = generateKashierOrderHash(order_data)

        # ✅ إعداد كل المعلمات
        params = {
            'merchantId': merchant_id,
            'orderId': order_id,
            'amount': amount_str,
            'currency': currency,
            'allowedMethods': 'card,wallet,bank_installments',
            'merchantRedirect': 'https://allen.allentravels.com/allen/payment/success/',
            'failureRedirect': 'https://your-domain.com/payment/failed/',
            'redirectMethod': 'get',
            'brandColor': '#ff0000',
            'display': 'ar',
            'hash': hash_signature,
            'mode': mode,
        }

        # ✅ تكوين رابط الدفع
        checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"

        return JsonResponse({
            'checkout_url': checkout_url,
            'order_id': order_id
        })

    except Exception as e:
        logging.getLogger(__name__).exception("Kashier Payment Error")  # ⬅️ أفضل من error
        return JsonResponse({'error': 'حدث خطأ في الخادم'}, status=500)

# Copy and paste this code into your backend
import hmac
import hashlib

def validateSignature(params, secret):
    queryString = ""
    for key in sorted(params):
        if key == "signature" or key == "mode":
            continue
        queryString += "&" + f"{key}=" + params[key]

    queryString = queryString[1:]
    secret_bytes = bytes(secret, 'utf-8')
    message = queryString.encode()
    signature = hmac.new(secret_bytes, message, hashlib.sha256).hexdigest()

    return "success" if signature == params.get("signature") else "failure"
@csrf_exempt
def kashier_payment_success(request):
    order_id = request.GET.get('orderId')

    trip_id = request.session.get('trip_id')
    selected_seats = request.session.get('selected_seats')
    student_id = request.session.get('student_id')
    trip_type = request.session.get('trip_type')
    selected_route = request.session.get('selected_route')

    if not all([trip_id, selected_seats, student_id, trip_type, selected_route]):
        messages.error(request, "حدث خطأ في البيانات المؤقتة. حاول الحجز من جديد.")
        return redirect('index')

    try:
        trip = Trip.objects.get(id=trip_id)
        student = passenger.objects.get(id=student_id)
        reserved_from_booking = Booking.objects.filter(Trip=trip).values_list('seats_reserved__id', flat=True)
        reserved_from_form = FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list('seat__id', flat=True)
        reserved_seats = set(reserved_from_booking).union(set(reserved_from_form))

        booking = Booking.objects.create(
            Trip=trip,
            passenger=student,
            user=student.user,
            payment_method='online',
            trip_type=trip_type,
            selected_route=selected_route,
            transaction_number=order_id
        )

        for seat_id in selected_seats:
            seat = Seat.objects.get(id=seat_id)
            if seat.id in reserved_seats:
                continue
            booking.seats_reserved.add(seat)

        # ✅ توليد كود خصم بعد الدفع
        discount_code = DiscountCode.objects.create(
            user=student.user,
            code=generate_unique_discount_code(),
            value=50.00
        )

        # ✅ إرسال رسالة
        send_whatsapp_confirmation(student, trip, booking.seats_reserved.all())

        student.last_selected_route = selected_route
        student.save()

        # ✅ حذف البيانات المؤقتة
        request.session.pop('trip_id', None)
        request.session.pop('selected_seats', None)
        request.session.pop('student_id', None)
        request.session.pop('trip_type', None)
        request.session.pop('selected_route', None)

        return render(request, 'success.html', {
            'discount_code': discount_code.code,
            'discount_value': discount_code.value
        })

    except Exception as e:
        print("خطأ أثناء الحجز بعد الدفع:", e)
        messages.error(request, "❌ حدث خطأ أثناء الحجز بعد الدفع.")
        return redirect('index')



@csrf_exempt
@require_POST
def store_booking_session(request):
    request.session['trip_id'] = request.POST.get('trip_id')
    request.session['selected_seats'] = json.loads(request.POST.get('selected_seats'))
    request.session['student_id'] = passenger.objects.get(user=request.user).id
    request.session['trip_type'] = request.POST.get('trip_type')
    request.session['selected_route'] = request.POST.get('selected_route')
    return JsonResponse({'status': 'ok'})

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def create_round_trip_view(request):
    departure_id = request.GET.get('departure_id')
    if request.method == 'POST':
        departure_trip_id = request.POST.get('departure_trip')
        return_trip_ids = request.POST.getlist('return_trips')

        try:
            departure_trip = Trip.objects.get(id=departure_trip_id)
            return_trips = Trip.objects.filter(id__in=return_trip_ids)
            departure_trip.trip_type = 'round_differentdays'
            departure_trip.save()
            departure_trip.related_return_trips.set(return_trips)

            for r in return_trips:
                r.related_departure_trip = departure_trip
                r.save()

            messages.success(request, 'تم ربط رحلة الذهاب بعدة رحلات عودة.')
            return redirect('/admin/Anaconda_bus_APP/trip/')

        except Trip.DoesNotExist:
            messages.error(request, 'خطأ في الرحلات.')

    available_trips = Trip.objects.filter(is_old=False).order_by('-date')
    return render(request, 'admin/create_round_trip.html', {
        'departure_id': departure_id,
        'available_trips': available_trips,
    })

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Trip, Seat, Booking, passenger
from django.utils.http import urlencode
import json, random, hmac, hashlib
from django.conf import settings
import uuid

@login_required
def round_trip_booking(request):
    selected_destination_id = request.GET.get('destination')
    destinations = destination.objects.all()

    if selected_destination_id:
        departure_trips = Trip.objects.filter(
            trip_type='one_way',
            is_active=True,
            date__gte=timezone.now().date(),
            start_destination_id=selected_destination_id
        )
        return_trips = Trip.objects.filter(
            trip_type='return',
            is_active=True,
            date__gte=timezone.now().date(),
            start_destination_id=selected_destination_id
        )
    else:
        departure_trips = Trip.objects.none()
        return_trips = Trip.objects.none()

    if request.method == 'POST':
        try:
            departure_trip_id = request.POST.get('departure_trip')
            return_trip_id = request.POST.get('return_trip')
            selected_departure_seats = request.POST.getlist('departure_seats')
            selected_return_seats = request.POST.getlist('return_seats')
            departure_route_point = request.POST.get('departure_route')
            return_route_point = request.POST.get('return_route')

            if not departure_trip_id or not return_trip_id:
                messages.error(request, "يرجى اختيار رحلات الذهاب والعودة.")
                raise ValueError("Trip IDs مفقودة")

            if not selected_departure_seats or not selected_return_seats:
                messages.error(request, "يجب اختيار المقاعد.")
                raise ValueError("المقاعد غير محددة")

            if not departure_route_point or not return_route_point:
                messages.error(request, "يجب اختيار نقاط الركوب.")
                raise ValueError("نقاط الركوب غير محددة")

            departure_trip = Trip.objects.get(id=departure_trip_id)
            return_trip = Trip.objects.get(id=return_trip_id)
            student = passenger.objects.get(user=request.user)

            # ✅ حساب السعر
            departure_price = float(departure_trip.one_way_price) * len(selected_departure_seats)
            return_price = float(return_trip.return_price) * len(selected_return_seats)
            total_amount = departure_price + return_price

            # ✅ توليد رقم طلب فريد
            def generate_unique_transaction_number():
                while True:
                    order_id = str(uuid.uuid4().int)[:10]
                    if not Booking.objects.filter(transaction_number=order_id).exists():
                        return order_id

            order_id = generate_unique_transaction_number()

            merchant_id = settings.KASHIER_ACCOUNT_KEY
            mode = settings.KASHIER_MODE
            currency = 'EGP'
            amount_str = str(int(total_amount))

            order_data = {
                'amount': amount_str,
                'currency': currency,
                'merchantOrderId': order_id,
            }

            def generateKashierOrderHash(order):
                mid = settings.KASHIER_ACCOUNT_KEY
                amount = order['amount']
                currency = order['currency']
                orderId = order['merchantOrderId']
                full_secret = settings.KASHIER_API_KEY
                secret = full_secret.split('$')[-1]
                path = f"/?payment={mid}.{orderId}.{amount}.{currency}"
                return hmac.new(secret.encode('utf-8'), path.encode('utf-8'), hashlib.sha256).hexdigest()

            hash_signature = generateKashierOrderHash(order_data)

            params = {
                'merchantId': merchant_id,
                'orderId': order_id,
                'amount': amount_str,
                'currency': currency,
                'allowedMethods': 'card,wallet,bank_installments',
                'merchantRedirect': 'https://allen.allentravels.com/allen/round-trip/payment/success/',
                'failureRedirect': 'https://your-domain.com/payment/failed/',
                'redirectMethod': 'get',
                'brandColor': '#ff0000',
                'display': 'ar',
                'hash': hash_signature,
                'mode': mode,
            }

            checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"

            request.session['round_trip_booking'] = {
                'departure_trip_id': departure_trip_id,
                'return_trip_id': return_trip_id,
                'departure_seats': selected_departure_seats,
                'return_seats': selected_return_seats,
                'departure_route_point': departure_route_point,
                'return_route_point': return_route_point,
                'order_id': order_id,
            }

            return JsonResponse({
                'checkout_url': checkout_url,
                'total_amount': total_amount,
                'order_id': order_id
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f"حدث خطأ أثناء الحجز: {str(e)}")

    context = {
        'departure_trips': departure_trips,
        'return_trips': return_trips,
        'destinations': destinations,
        'selected_destination_id': int(selected_destination_id) if selected_destination_id else None,
    }

    return render(request, 'round_trip_booking.html', context)

import uuid

@csrf_exempt
def round_trip_payment_success(request):
    session_data = request.session.get('round_trip_booking')

    if not session_data:
        messages.error(request, "حدث خطأ في البيانات المؤقتة. حاول الحجز من جديد.")
        return redirect('index')

    try:
        departure_trip = Trip.objects.get(id=session_data['departure_trip_id'])
        return_trip = Trip.objects.get(id=session_data['return_trip_id'])
        student = passenger.objects.get(user=request.user)

        # ✅ توليد رقمين فريدين للمعاملات
        dep_transaction_number = f"{session_data['order_id']}-A"
        ret_transaction_number = f"{session_data['order_id']}-B"

        # ✅ حجز الذهاب
        dep_booking = Booking.objects.create(
            Trip=departure_trip,
            passenger=student,
            user=student.user,
            payment_method='online',
            trip_type='one_way',
            selected_route=session_data['departure_route_point'],
            transaction_number=dep_transaction_number
        )
        for seat_id in session_data['departure_seats']:
            seat = Seat.objects.get(id=seat_id)
            dep_booking.seats_reserved.add(seat)

        # ✅ حجز العودة
        ret_booking = Booking.objects.create(
            Trip=return_trip,
            passenger=student,
            user=student.user,
            payment_method='online',
            trip_type='return',
            selected_route=session_data['return_route_point'],
            transaction_number=ret_transaction_number
        )
        for seat_id in session_data['return_seats']:
            seat = Seat.objects.get(id=seat_id)
            ret_booking.seats_reserved.add(seat)

        # ✅ توليد روابط Telegram
        from telegram_bot.utils import generate_telegram_link
        dep_telegram_link = generate_telegram_link(dep_booking.id)
        ret_telegram_link = generate_telegram_link(ret_booking.id)

        # ✅ إرسال تأكيد
        send_round_trip_whatsapp_confirmation(
            passenger=student,
            departure_trip=departure_trip,
            return_trip=return_trip,
            departure_seats=[Seat.objects.get(id=sid) for sid in session_data['departure_seats']],
            return_seats=[Seat.objects.get(id=sid) for sid in session_data['return_seats']],
            departure_route=session_data['departure_route_point'],
            return_route=session_data['return_route_point']
        )

        # ✅ إرسال تأكيد تلقائي للبوت
        from telegram_bot.utils import generate_telegram_link, send_telegram_booking_confirmation
        dep_telegram_link = generate_telegram_link(dep_booking.id)
        ret_telegram_link = generate_telegram_link(ret_booking.id)

        # ✅ إرسال تأكيد تلقائي للبوت
        try:
            send_telegram_booking_confirmation(dep_booking, 'departure')
            send_telegram_booking_confirmation(ret_booking, 'return')
            print(f"✅ Telegram confirmations sent for {student.username}")
        except Exception as e:
            print(f"❌ Error sending Telegram confirmations: {e}")

        del request.session['round_trip_booking']

        return render(request, 'success.html', {
            'message': '✅ تم الدفع وحجز الرحلتين بنجاح!',
            'dep_telegram_link': dep_telegram_link,
            'ret_telegram_link': ret_telegram_link,
            'dep_booking': dep_booking,
            'ret_booking': ret_booking
        })

    except Exception as e:
        print("❌ خطأ أثناء إنشاء الحجز:", e)
        messages.error(request, "حدث خطأ أثناء تأكيد الحجز بعد الدفع.")
        return redirect('index')

from django.http import JsonResponse
from .models import Trip
from django.utils import timezone

from django.http import JsonResponse
from django.utils import timezone
from .models import Trip

@login_required
def get_trips_by_destination(request):
    destination_id = request.GET.get('destination_id')

    if not destination_id:
        return JsonResponse({'departure_trips': [], 'return_trips': []})

    departure_trips = Trip.objects.filter(
        trip_type='one_way',
        is_active=True,
        date__gte=timezone.now().date(),
        start_destination_id=destination_id  # 👈 مهم جدًا
    )

    return_trips = Trip.objects.filter(
        trip_type='return',
        is_active=True,
        date__gte=timezone.now().date(),
        start_destination_id=destination_id
    )

    departure_data = [{
        'id': trip.id,
        'name': f"{trip.trip_name} / {trip.date.strftime('%Y-%m-%d')}"
    } for trip in departure_trips]

    return_data = [{
        'id': trip.id,
        'name': f"{trip.trip_name} / {trip.date.strftime('%Y-%m-%d')}"
    } for trip in return_trips]

    return JsonResponse({
        'departure_trips': departure_data,
        'return_trips': return_data
    })

@login_required
def get_trip_seats(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    seats = Seat.objects.filter(bus=trip.bus).order_by('seat_number')
    
    # الكراسي المحجوزة بالفعل
    reserved_seats = Booking.objects.filter(Trip=trip).values_list('seats_reserved__id', flat=True)
    
    seats_data = []
    for seat in seats:
        seats_data.append({
            'id': seat.id,
            'number': seat.seat_number,
            'row': seat.row,
            'column': seat.column,
            'is_reserved': seat.id in reserved_seats
        })
    
    return JsonResponse({
        'seats': seats_data,
        'bus_name': trip.bus.name,
        'trip_name': trip.trip_name,
        'trip_date': trip.date.strftime('%Y-%m-%d')
    })
import requests
import requests
def send_round_trip_whatsapp_confirmation(passenger, departure_trip, return_trip, departure_seats, return_seats, departure_route, return_route):
    INSTANCE_ID = "instance105329"
    API_TOKEN = settings.ULTRAMSG_API_TOKEN
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    bookings_url = "https://allen.allentravels.com/allen/bookings/"

    departure_seat_numbers = ", ".join([str(seat.seat_number) for seat in departure_seats])
    return_seat_numbers = ", ".join([str(seat.seat_number) for seat in return_seats])

    departure_message = f"""
🚍 تأكيد حجز الذهاب 🚍
✅ {passenger.name}، تم تأكيد حجزك لرحلة الذهاب بنجاح.
🚌 الرحلة: {departure_trip.trip_name}
📅 التاريخ: {departure_trip.date.strftime('%Y-%m-%d')}
⏰ الوقت: {departure_trip.start_time.strftime('%I:%M %p')}
📍 نقطة الركوب: {departure_route}
💺 المقاعد: {departure_seat_numbers}
🔗 تفاصيل: {bookings_url}
"""

    return_message = f"""
🚍 تأكيد حجز العودة 🚍
✅ {passenger.name}، تم تأكيد حجزك لرحلة العودة بنجاح.
🚌 الرحلة: {return_trip.trip_name}
📅 التاريخ: {return_trip.date.strftime('%Y-%m-%d')}
⏰ الوقت: {return_trip.start_time.strftime('%I:%M %p')}
📍 نقطة الركوب: {return_route}
💺 المقاعد: {return_seat_numbers}
🔗 تفاصيل: {bookings_url}
"""

    for msg in [departure_message, return_message]:
        payload = {
            "token": API_TOKEN,
            "to": passenger.phone_number,
            "body": msg.strip(),
        }
        requests.post(URL, data=payload)

from django.http import JsonResponse
from .models import Trip
@login_required
def get_trip_pickup_points(request, trip_id):
    try:
        trip = Trip.objects.get(id=trip_id)
        routes = [r.strip() for r in trip.route.split('\n') if r.strip()]
        return JsonResponse({'routes': routes})
    except Trip.DoesNotExist:
        return JsonResponse({'error': 'الرحلة غير موجودة'}, status=404)


#esp 32-cam section 
# views.py

from django.http import JsonResponse
from .models import Bus

def update_ip(request):
    bus_id = request.GET.get("bus_id")
    ip = request.GET.get("ip")
    try:
        bus = Bus.objects.get(id=bus_id)
        bus.esp_ip = ip
        bus.save()
        return JsonResponse({"status": "updated", "ip": ip})
    except Bus.DoesNotExist:
        return JsonResponse({"status": "bus not found"}, status=404)
from django.http import JsonResponse
from .models import Bus

def update_esp_ip(request):
    bus_id = request.GET.get("bus_id")
    ip = request.GET.get("ip")

    if not bus_id or not ip:
        return JsonResponse({"status": "error", "message": "Missing data"}, status=400)

    try:
        bus = Bus.objects.get(id=bus_id)
        bus.esp_ip = ip
        bus.save()
        return JsonResponse({"status": "success", "ip": ip})
    except Bus.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Bus not found"}, status=404)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from django.http import JsonResponse
from .models import Esp32Data
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Esp32Data
import json
import requests
import math

def send_whatsapp_crash_alert(severity, wheel_speed):
    INSTANCE_ID = "instance105329"
    API_TOKEN = settings.ULTRAMSG_API_TOKEN
    URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"

    danger_level = {
        'high': "⚠️⚠️⚠️ خبطه عنيفة جدًا!",
        'moderate': "⚠️ خبطه متوسطة الشدة.",
        'low': "⚠️ خبطه خفيفة.",
    }

    message = f"""
🚨🚗 تنبيه بحادث للعربية رقم 1 🚨
{danger_level.get(severity, '⚠️ خبطه غير محددة الشدة')}
الرجاء التواصل فورًا مع السائق أو الجهات المختصة.

📉 سرعة العجلة: {wheel_speed:.2f} m/s
📍 يرجى التحقق من الحالة بشكل سريع.
    """

    payload = {
        "token": API_TOKEN,
        "to": "+201272345796",
        "body": message.strip(),
    }
    requests.post(URL, data=payload)

@csrf_exempt
def receive_esp_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # حفظ البيانات
        Esp32Data.objects.create(
            latitude=data['latitude'],
            longitude=data['longitude'],
            accX=data['accX'],
            accY=data['accY'],
            accZ=data['accZ'],
            gyroX=data['gyroX'],
            gyroY=data['gyroY'],
            gyroZ=data['gyroZ'],
        )

        # تحليل الخبطة
        gyroX = abs(data['gyroX'])
        gyroY = abs(data['gyroY'])
        gyroZ = abs(data['gyroZ'])
        is_crash = gyroX > 250 or gyroY > 250 or gyroZ > 250

        # سرعة العجلة (مشتقة من عجلة التسارع)
        accX = data['accX']
        accY = data['accY']
        accZ = data['accZ']
        acceleration_magnitude = math.sqrt(accX**2 + accY**2 + accZ**2)  # بوحدة m/s^2

        # تقريب السرعة التقديرية (افتراض زمني بسيط dt = 1 ثانية)
        estimated_speed = acceleration_magnitude * 1

        # درجة الخطورة
        if estimated_speed >= 20:
            severity = 'high'
        elif estimated_speed >= 10:
            severity = 'moderate'
        else:
            severity = 'low'

        # لو في خبطة ابعت
        if is_crash:
            send_whatsapp_crash_alert(severity, estimated_speed)

        return JsonResponse({"status": "received", "data": data})
    return JsonResponse({"error": "Invalid request method"}, status=405)

from django.shortcuts import render
from .models import Esp32Data
from django.shortcuts import render
from .models import Esp32Data
import math

def show_dashboard(request):
    raw_data = Esp32Data.objects.order_by('-timestamp')[:100]
    processed_data = []

    for d in raw_data:
        speed = math.sqrt(d.accX**2 + d.accY**2 + d.accZ**2)
        is_crash = abs(d.gyroX) > 250 or abs(d.gyroY) > 250 or abs(d.gyroZ) > 250

        if is_crash:
            if speed > 20:
                severity = "🔴 عنيفة جداً"
            elif speed > 10:
                severity = "🟠 متوسطة"
            else:
                severity = "🟡 خفيفة"
        else:
            severity = "✅ لا يوجد"

        processed_data.append({
            'timestamp': d.timestamp,
            'latitude': d.latitude,
            'longitude': d.longitude,
            'accX': d.accX,
            'accY': d.accY,
            'accZ': d.accZ,
            'gyroX': d.gyroX,
            'gyroY': d.gyroY,
            'gyroZ': d.gyroZ,
            'speed': round(speed, 2),
            'severity': severity,
        })

    return render(request, 'dashboard.html', {'data': processed_data})

# دالة لتحديث حالة الحضور (للسائق) - محدثة لتشمل خصم الرحلات
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

@csrf_exempt
def mark_attendance(request ):
    if request.method == 'POST':
        source = request.POST.get('source')
        booking_id = request.POST.get('id')

        try:
            # استخدام database transaction لضمان سلامة البيانات
            with transaction.atomic():
                if source == 'form':
                    reservation = FormReservation.objects.get(id=booking_id)
                    
                    # التحقق من أن الحضور لم يسجل مسبقاً
                    if reservation.attendance_status == 'present':
                        return JsonResponse({
                            'success': False, 
                            'error': 'تم تسجيل حضور هذا الراكب مسبقاً'
                        }, status=400)
                    
                    # تسجيل الحضور
                    reservation.attendance_status = 'present'
                    reservation.save()
                    
                    # تحديث عدد الرحلات للراكب
                    passenger_obj = reservation.passenger
                    
                    # --- أضف هذه الأسطر للطباعة --- START
                    print(f"[DEBUG] FormReservation ID: {booking_id}")
                    print(f"[DEBUG] Passenger object: {passenger_obj}")
                    if passenger_obj:
                        print(f"[DEBUG] Before update - rides_used: {passenger_obj.rides_used}")
                    else:
                        print("[DEBUG] No passenger object linked to this FormReservation.")
                    # --- أضف هذه الأسطر للطباعة --- END

                    if passenger_obj:
                        # زيادة عدد الرحلات المستخدمة
                        passenger_obj.rides_used += 1
                        passenger_obj.save()
                        
                        # --- أضف هذه الأسطر للطباعة --- START
                        print(f"[DEBUG] After update - rides_used: {passenger_obj.rides_used}")
                        # --- أضف هذه الأسطر للطباعة --- END

                        return JsonResponse({
                            'success': True,
                            'message': f'تم تسجيل حضور {passenger_obj.name} بنجاح',
                            'passenger_name': passenger_obj.name,
                            'rides_used': passenger_obj.rides_used,
                            'remaining_rides': passenger_obj.remaining_rides
                        })
                    else:
                        return JsonResponse({
                            'success': False, 
                            'error': 'لا يوجد راكب مرتبط بهذا الحجز'
                        }, status=400)
                        
                elif source == 'booking':
                    booking = Booking.objects.get(id=booking_id)
                    
                    # التحقق من أن الحضور لم يسجل مسبقاً
                    if booking.attendance_status == 'present':
                        return JsonResponse({
                            'success': False, 
                            'error': 'تم تسجيل حضور هذا الراكب مسبقاً'
                        }, status=400)
                    
                    # تسجيل الحضور
                    booking.attendance_status = 'present'
                    booking.save()
                    
                    # تحديث عدد الرحلات للراكب
                    passenger_obj = booking.passenger

                    # --- أضف هذه الأسطر للطباعة --- START
                    print(f"[DEBUG] Booking ID: {booking_id}")
                    print(f"[DEBUG] Passenger object: {passenger_obj}")
                    if passenger_obj:
                        print(f"[DEBUG] Before update - rides_used: {passenger_obj.rides_used}")
                    else:
                        print("[DEBUG] No passenger object linked to this Booking.")
                    # --- أضف هذه الأسطر للطباعة --- END

                    if passenger_obj:
                        # زيادة عدد الرحلات المستخدمة
                        passenger_obj.rides_used += 1
                        passenger_obj.save()
                        
                        # --- أضف هذه الأسطر للطباعة --- START
                        print(f"[DEBUG] After update - rides_used: {passenger_obj.rides_used}")
                        # --- أضف هذه الأسطر للطباعة --- END

                        return JsonResponse({
                            'success': True,
                            'message': f'تم تسجيل حضور {passenger_obj.name} بنجاح',
                            'passenger_name': passenger_obj.name,
                            'rides_used': passenger_obj.rides_used,
                            'remaining_rides': passenger_obj.remaining_rides
                        })
                    else:
                        return JsonResponse({
                            'success': False, 
                            'error': 'لا يوجد راكب مرتبط بهذا الحجز'
                        }, status=400)
                else:
                    return JsonResponse({'success': False, 'error': 'مصدر غير صالح'}, status=400)
                    
        except (FormReservation.DoesNotExist, Booking.DoesNotExist):
            return JsonResponse({'success': False, 'error': 'الحجز غير موجود'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'حدث خطأ: {str(e)}'}, status=500)
            
    return JsonResponse({'success': False, 'error': 'طريقة غير مسموح بها'}, status=405)

from django.utils.timezone import now
from .models import Installment

def check_and_send_due_installments():
    today = now().date()
    due_installments = Installment.objects.filter(due_date=today, is_paid=False)

    for installment in due_installments:
        passenger = installment.passenger
        phone_number = passenger.phone  # لازم Passenger عنده رقم phone
        message = (
            f"🚨 تنبيه هام\n\n"
            f"عزيزي {passenger.name},\n"
            f"لديك قسط جديد مستحق اليوم بمبلغ {installment.amount} جنيه.\n"
            f"لديك 24 ساعة لإتمام الدفع، وإلا سيتم تطبيق رسوم إضافية أو إلغاء الاشتراك.\n\n"
            f"في حال وجود مشكلة، يرجى التواصل مع إدارة الشركة."
        )
        send_whatsapp_message(phone_number, message)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from datetime import timedelta
from .models import FormReservation, passenger
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.timezone import now, timedelta
from .models import Booking, FormReservation, passenger

@login_required
def repeat_last_reservation(request):
    passenger_instance = get_object_or_404(passenger, user=request.user)

    today = now().date()
    last_week_same_day = today - timedelta(days=7)

    # نحسب الأيام المحتملة (اليوم اللي قبله، نفس اليوم، واليوم اللي بعده)
    possible_dates = [
        today - timedelta(days=8),
        today - timedelta(days=7),
        today - timedelta(days=6),
    ]

    # ندور في FormReservation على أي حجز في الأيام دي
    last_reservations = FormReservation.objects.filter(
        passenger=passenger_instance,
        trip_date__in=possible_dates
    ).order_by('-trip_date')  # نجيب الأحدث منهم


    # لو مفيش حجز في الفورم → ندور في Booking
    if not last_reservations.exists():
        last_bookings = Booking.objects.filter(
            passenger=passenger_instance,
            Trip__date=last_week_same_day  # ✅ بدل departure_time
        )
    else:
        last_bookings = None

    # لو مفيش ولا في الفورم ولا في البوكينج
    if not last_reservations.exists() and (not last_bookings or not last_bookings.exists()):
        messages.warning(request, "مفيش أي حجز سابق عشان يتكرر.")
        return redirect("index")

    if request.method == "POST":
        # ✅ تكرار من FormReservation لكن من غير Trip
        if last_reservations.exists():
            for res in last_reservations:
                FormReservation.objects.create(
                    passenger=passenger_instance,
                    user=request.user,
                    trip=None,  # ❌ منغير تريب
                    trip_date=today,
                    trip_type=res.trip_type,
                    pickup_location=request.POST.get("pickup_location", res.pickup_location),
                    going_dropoff_location=request.POST.get("going_dropoff_location", res.going_dropoff_location),
                    return_pickup_location=request.POST.get("return_pickup_location", res.return_pickup_location),
                    return_dropoff_location=request.POST.get("return_dropoff_location", res.return_dropoff_location),
                    category=res.category,
                    city=res.city,
                    status="confirmed",
                    seat=res.seat if hasattr(res, "seat") else None
                )

        # ✅ تكرار من Booking → FormReservation من غير Trip
        elif last_bookings and last_bookings.exists():
            for book in last_bookings:
                FormReservation.objects.create(
                    passenger=passenger_instance,
                    user=request.user,
                    trip=None,  # ❌ منغير تريب
                    trip_date=today,
                    trip_type=book.trip_type,
                    pickup_location=request.POST.get("pickup_location", book.selected_route),
                    going_dropoff_location=None,
                    return_pickup_location=None,
                    return_dropoff_location=None,
                    category=book.Trip.bus.category if book.Trip and book.Trip.bus else None,
                    city=book.Trip.bus.city if book.Trip and hasattr(book.Trip.bus, "city") else None,
                    status="confirmed",
                    seat=book.seats_reserved.first() if book.seats_reserved.exists() else None
                )

        return redirect('booking_success')

    return render(request, "repeat_reservation.html", {
        "last_reservations": last_reservations if last_reservations.exists() else last_bookings,
    })


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import passenger

@login_required
def face_scan_page(request):
    """صفحة فيها الكاميرا وزرار التصوير"""
    return render(request, "face_scan.html")

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

@login_required
def upload_face(request):
    passenger = request.user.passenger
    if request.method == "POST" and "face_image" in request.FILES:
        try:
            # نحفظ الصورة في الحقل
            passenger.face_thumbnail = request.FILES["face_image"]
            passenger.save()  # هنا بيتضغط ويتصغر أوتوماتيك من save() في الموديل
            messages.success(request, "✅ تم رفع الصورة بنجاح")
            return redirect("index")  # يروح للصفحة الرئيسية بعد الحفظ
        except Exception as e:
            messages.error(request, f"❌ حصل خطأ: {str(e)}")

    return render(request, "upload_face.html", {"passenger": passenger})
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import Trip, Booking

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from datetime import date, timedelta
from django.db.models import Q
def generate_pdf_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    # جلب الحجوزات
    form_reservations = FormReservation.objects.filter(trip=trip )
    bookings = Booking.objects.filter(Trip=trip)

    # الكراسي
    seats = Seat.objects.filter(bus=trip.bus)
    reserved_seats_ids = list(
        FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list("seat__id", flat=True)
    ) + list(
        Seat.objects.filter(bookings__Trip=trip).values_list("id", flat=True)
    )

    html_string = render_to_string("admin/trip_report.html", {
        "trip": trip,
        "form_reservations": form_reservations,
        "bookings": bookings,
        "seats": seats,
        "reserved_seats_ids": reserved_seats_ids
    })

    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="trip_{trip_id}_report.pdf"'
    return response


def trip_report_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)

    form_reservations = FormReservation.objects.filter(trip=trip)
    bookings = Booking.objects.filter(Trip=trip)

    seats = Seat.objects.filter(bus=trip.bus)
    reserved_seats_ids = list(
        FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list("seat__id", flat=True)
    ) + list(
        Seat.objects.filter(bookings__Trip=trip).values_list("id", flat=True)
    )

    return render(request, "admin/trip_report.html", {
        "trip": trip,
        "form_reservations": form_reservations,
        "bookings": bookings,
        "seats": seats,
        "reserved_seats_ids": reserved_seats_ids
    })
from django.http import JsonResponse
from django.utils import timezone
from .models import Trip, Booking

@login_required
def get_available_trips_for_edit(request ):
    booking_id = request.GET.get('booking_id')
    
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return JsonResponse({'error': 'الحجز غير موجود'}, status=404)

    # جلب الرحلات المتاحة لنفس الجامعة ونوع الرحلة وتاريخها بعد اليوم
    available_trips = Trip.objects.filter(
        category=booking.Trip.category,      # نفس الجامعة
        trip_type=booking.trip_type,         # نفس نوع الرحلة (ذهاب/عودة)
        date__gte=timezone.now().date(),     # من اليوم فصاعداً
        is_active=True
    ).exclude(id=booking.Trip.id).values('id', 'trip_name', 'date', 'start_time') # استبعاد الرحلة الحالية

    # يمكنك إضافة شرط للتحقق من وجود مقاعد متاحة هنا إذا أردت
    
    return JsonResponse({'trips': list(available_trips)})
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from .models import Trip, Booking, Seat
# views.py

from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Trip, Booking, Seat # تأكد من استيراد كل النماذج المطلوبة

@login_required
@transaction.atomic # يضمن أن كل العمليات تتم كوحدة واحدة
def change_booking_trip(request, booking_id, new_trip_id):
    try:
        # --- الخطوة 1: جلب البيانات الأساسية ---
        old_booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        new_trip = get_object_or_404(Trip, id=new_trip_id)

        if old_booking.status != 'active':
            messages.error(request, "لا يمكن تعديل حجز غير نشط.")
            return redirect('user_bookings')

        # --- الخطوة 2: التحقق من توفر المقاعد في الرحلة الجديدة ---
        num_seats_needed = old_booking.seats_reserved.count()
        available_seats_in_new_trip = Seat.objects.filter(bus=new_trip.bus, is_reserved=False)
        
        if available_seats_in_new_trip.count() < num_seats_needed:
            messages.error(request, f"❌ لا توجد مقاعد كافية في الرحلة الجديدة. (مطلوب: {num_seats_needed})")
            return redirect('user_bookings')

        # --- الخطوة 3: تحرير المقاعد القديمة وحذف الحجز القديم ---
        
        # أ) نحتفظ بمعرفات المقاعد القديمة لتحريرها
        old_seat_ids = list(old_booking.seats_reserved.values_list('id', flat=True))

        # ب) تحرير المقاعد القديمة في قاعدة البيانات لتصبح متاحة للآخرين
        Seat.objects.filter(id__in=old_seat_ids).update(is_reserved=False)
        
        # ج) حذف الحجز القديم بالكامل من قاعدة البيانات
        old_booking.delete()

        # --- الخطوة 4: إنشاء الحجز الجديد وربطه بالرحلة والمقاعد الجديدة ---
        new_booking = Booking.objects.create(
            passenger=old_booking.passenger,
            user=old_booking.user,
            Trip=new_trip,
            trip_type=old_booking.trip_type,
            selected_route=old_booking.selected_route,
            payment_method=old_booking.payment_method,
            status='active',
        )

        # أ) اختيار المقاعد الجديدة من القائمة المتاحة
        new_seats_to_reserve = available_seats_in_new_trip[:num_seats_needed]
        new_seat_ids = [seat.id for seat in new_seats_to_reserve]

        # ب) ربط المقاعد الجديدة بالحجز الجديد
        new_booking.seats_reserved.set(new_seats_to_reserve)
        
        # ج) تحديث حالة المقاعد الجديدة إلى "محجوزة"
        Seat.objects.filter(id__in=new_seat_ids).update(is_reserved=True)

        messages.success(request, f"✅ تم نقل حجزك بنجاح إلى رحلة '{new_trip.trip_name}'.")

    except Exception as e:
        messages.error(request, f"حدث خطأ غير متوقع أثناء تعديل الحجز: {e}")

    return redirect('user_bookings')




















































@login_required
@transaction.atomic
def change_form_booking_trip(request, form_booking_id, new_trip_id):
    """
    يقوم بتغيير حجز فورم من "معلق" إلى "مكتمل" عبر ربطه برحلة ومقعد.
    """
    try:
        # --- الخطوة 1: جلب البيانات الأساسية ---
        # نتأكد أن الحجز يخص المستخدم الحالي عبر passenger
        form_booking = get_object_or_404(FormReservation, id=form_booking_id, passenger__user=request.user)
        new_trip = get_object_or_404(Trip, id=new_trip_id)

        # التحقق من أن الحجز لم يتم ربطه من قبل
        if form_booking.trip is not None:
            messages.error(request, "هذا الحجز مرتبط بالفعل برحلة ولا يمكن تعديله.")
            return redirect('user_bookings')

        # --- الخطوة 2: التحقق من توفر مقعد في الرحلة الجديدة ---
        available_seat = Seat.objects.filter(bus=new_trip.bus, is_reserved=False).first()
        if not available_seat:
            messages.error(request, "❌ لا توجد مقاعد متاحة في الرحلة الجديدة التي اخترتها.")
            return redirect('user_bookings')

        # --- الخطوة 3: تحديث حجز الفورم وربطه بالرحلة والمقعد الجديد ---
        form_booking.trip = new_trip
        form_booking.seat = available_seat
        form_booking.save()

        # --- الخطوة 4: حجز المقعد الجديد ---
        available_seat.is_reserved = True
        available_seat.save()

        messages.success(request, f"✅ تم تأكيد حجزك بنجاح في رحلة '{new_trip.trip_name}'.")

    except Exception as e:
        messages.error(request, f"حدث خطأ غير متوقع أثناء تعديل الحجز: {e}")

    return redirect('user_bookings')



@login_required
def ajax_get_available_trips(request):
    """
    يجلب الرحلات المتاحة بناءً على حجز حالي (سواء كان Booking أو FormReservation).
    """
    booking_id = request.GET.get('booking_id')
    form_booking_id = request.GET.get('form_booking_id')
    today = timezone.now().date()
    
    try:
        if booking_id:
            # منطق تعديل حجز رحلة عادي
            current_booking = get_object_or_404(Booking, id=booking_id, user=request.user)
            category = current_booking.Trip.category
            # استبعاد الرحلة الحالية من الخيارات
            available_trips_qs = Trip.objects.filter(
                category=category,
                date__gte=today,
                is_active=True
            ).exclude(id=current_booking.Trip.id)

        elif form_booking_id:
            # منطق تعديل حجز فورم
            form_booking = get_object_or_404(FormReservation, id=form_booking_id, passenger__user=request.user)
            category = form_booking.category
            # جلب الرحلات في نفس اليوم ونفس النوع (ذهاب/عودة)
            available_trips_qs = Trip.objects.filter(
                category=category,
                date=form_booking.trip_date,
                trip_type=form_booking.trip_type,
                is_active=True
            )
        else:
            return JsonResponse({'error': 'Booking ID or Form Booking ID is required'}, status=400)

        # تحويل QuerySet إلى قائمة من القواميس
        trips_list = list(available_trips_qs.values('id', 'trip_name', 'date', 'start_time'))
        return JsonResponse({'trips': trips_list})

    except (Booking.DoesNotExist, FormReservation.DoesNotExist):
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
# allen/views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from datetime import datetime

# تأكد من استيراد كل النماذج التي تحتاجها
from .models import Booking, FormReservation, Trip, Seat, Category, City
# استيراد الفورم
from .forms import FormReservationForm 
# تأكد من استيراد كل ما تحتاجه في بداية الملف
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.contrib import messages
import json # لاستيراد مكتبة JSON

# استيراد الموديلات والفورمز الخاصة بك
from .models import FormReservation, City, Category 
from .forms import FormReservationForm
# تأكد من استيراد كل ما تحتاجه في بداية الملف
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.template.loader import render_to_string
from django.contrib import messages
import json

# استيراد الموديلات والفورمز الخاصة بك
from .models import FormReservation, City, Category 
from .forms import FormReservationForm
@login_required
@transaction.atomic
def edit_form_reservation(request, booking_id):
    reservation = get_object_or_404(FormReservation, id=booking_id, user=request.user)

    # ✅ شيل الشرط بتاع لو في trip
    # مش هنمنع التعديل حتى لو الحجز مربوط بـ trip

    if request.method == 'POST':
        form = FormReservationForm(
            request.POST,
            instance=reservation,
            user=request.user,
            category=reservation.category
        )

        if form.is_valid():
            # تحديث الحقول المطلوبة فقط
            reservation.arrival_time = form.cleaned_data.get('arrival_time')
            reservation.back_time = form.cleaned_data.get('back_time')

            # تحديث المدن
            going_city_id = request.POST.get('going_city')
            if going_city_id:
                reservation.going_city_id = going_city_id

            return_city_id = request.POST.get('return_city')
            if return_city_id:
                reservation.return_city_id = return_city_id

            # تحديث أماكن الركوب
            reservation.going_pickup_location = request.POST.get('going_pickup_location')
            reservation.return_pickup_location = request.POST.get('return_pickup_location')

            # تحديث الحقل الموحد pickup_location
            if reservation.trip_type == 'ذهاب':
                reservation.pickup_location = reservation.going_pickup_location
            elif reservation.trip_type == 'عودة':
                reservation.pickup_location = reservation.return_pickup_location
            elif reservation.trip_type == 'ذهاب وعودة':
                reservation.pickup_location = reservation.going_pickup_location

            reservation.save()

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': 'تم تعديل الحجز بنجاح'})
            messages.success(request, "✅ تم تعديل الحجز بنجاح.")
            return redirect('user_bookings')

        else:
            errors_json = json.loads(form.errors.as_json())
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'فشل التعديل', 'errors': errors_json}, status=400)
            messages.error(request, "❌ فشل التعديل.")
            return redirect('user_bookings')

    # GET request
    form = FormReservationForm(instance=reservation, user=request.user, category=reservation.category)
    cities = City.objects.filter(is_active=True, category=reservation.category).distinct()

    context = {
        'form': form,
        'booking_id': booking_id,
        'cities': cities,
    }
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form_html = render_to_string('partials/form_reservation_form.html', context, request=request)
        return JsonResponse({'form_html': form_html})

    return redirect('user_bookings')
@login_required
@transaction.atomic
def cancel_form_reservation(request, booking_id):
    """
    يقوم بحذف حجز فورم معلق من قاعدة البيانات.
    """
    try:
        reservation = get_object_or_404(FormReservation, id=booking_id, passenger__user=request.user)
        
        if reservation.trip:
            messages.error(request, "لا يمكن إلغاء حجز مكتمل من هنا.")
            return redirect('user_bookings')

        # حذف الحجز
        reservation.delete()
        messages.success(request, "✅ تم إلغاء حجزك بنجاح.")

    except FormReservation.DoesNotExist:
        messages.error(request, "الحجز غير موجود أو لا تملك صلاحية إلغائه.")
    except Exception as e:
        messages.error(request, f"حدث خطأ أثناء الإلغاء: {e}")

    return redirect('user_bookings')
# يسطا         قولتلك بروبليم ما الها حل ولله 


import openai
from django.http import JsonResponse
from django.conf import settings

openai.api_key = settings.OPENAI_API_KEY

from openai import OpenAI
from django.http import JsonResponse
from django.conf import settings

def ask_gpt(request):
    q = request.GET.get("q", "Hello GPT")

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": q}
        ]
    )

    answer = response.choices[0].message.content
    return JsonResponse({"answer": answer})
# views.py

import google.generativeai as genai
from django.http import JsonResponse
from django.conf import settings
from .models import Booking, FormReservation, passenger # استيراد الموديلات اللازمة

# ... (باقي دوال الـ views الخاصة بك ) ...

# --- دوال مساعدة لجلب البيانات ---
import google.generativeai as genai
from django.http import JsonResponse
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count

from .models import Booking, FormReservation, passenger
import re
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count
from .models import FormReservation, City, Category # افترض أن النماذج في نفس التطبيق

# --- السياق المبدئي للنظام ---
SYSTEM_CONTEXT = """
أنت "Allen-AI"، مساعد ذكي متقدم لنظام حجز الحافلات والسيارات الخاص بشركة Allen.
مهمتك هي تحليل خطوط السير وتنظيم الرحلات بناءً على الحجوزات المتاحة.

**المهام المطلوبة**:
1. جمع جميع نقاط الركوب من جميع المدن
2. تحليل الحجوزات المتاحة لكل نقطة
3. ترتيب خط السير الأمثل حسب الكثافة والموقع
4. حساب أوقات الوصول المتوقعة لكل نقطة
5. توفير تقرير شامل ومنظم

**مبادئ تنظيم خط السير**:
- البدء بالنقاط الأبعد عن الجامعة
- تجميع النقاط المتقاربة جغرافياً
- مراعاة الكثافة (النقاط ذات الحجوزات الكبيرة أولاً)
- حساب وقت الوصول بناءً على المسافة والمرور

**معدلات الوقت المتوقعة**:
- كل 10 كم ≈ 15-20 دقيقة (حسب المرور)
- نقطة التجميع ≈ 5-10 دقائق انتظار
- الوقت بين النقاط المتقاربة ≈ 5 دقائق

أنت تجيب فقط باللغة العربية وبشكل منظم باستخدام الجداول والتنسيق الواضح.
"""

def get_cities_for_university(university_name):
    """
    جلب قائمة المدن المرتبطة بجامعة معينة.
    """
    try:
        # تنظيف اسم الجامعة من كلمات مثل "جامعة" أو "جامعه"
        cleaned_name = re.sub(r'جامعة|جامعه|كليه|كلية|university|college', '', university_name, flags=re.IGNORECASE).strip()
        
        print(f"البحث عن جامعة: '{cleaned_name}'")  # للتصحيح
        
        # البحث أولاً بمطابقة تامة
        category = Category.objects.filter(
            name__iexact=cleaned_name
        ).first()
        
        if not category:
            # إذا لم توجد مطابقة تامة، جرب البحث الجزئي
            category = Category.objects.filter(
                name__icontains=cleaned_name
            ).first()
        
        if not category:
            # محاولة أخيرة: البحث في كل الأسماء بدون تنظيف
            category = Category.objects.filter(
                name__icontains=university_name
            ).first()
        
        if not category:
            # عرض جميع الجامعات المتاحة للمساعدة في التصحيح
            all_universities = Category.objects.all().values_list('name', flat=True)
            return f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'. الجامعات المتاحة: {', '.join(all_universities)}"

        print(f"تم العثور على الجامعة: {category.name}")  # للتصحيح

        cities = City.objects.filter(category=category, is_active=True)
        if not cities.exists():
            return f"لا توجد مدن متاحة حالياً لجامعة '{category.name}'."

        response_text = f"المدن المتاحة لجامعة '{category.name}' هي:\n"
        for city in cities:
            response_text += f"- {city.name}\n"
        
        return response_text

    except Exception as e:
        return f"حدث خطأ أثناء جلب المدن: {str(e)}"

def get_bookings_for_city(university_name, city_name):
    """
    جلب تقرير الحجوزات وخطوط السير لمدينة وجامعة معينة.
    """
    try:
        # التحقق من وجود الجامعة والمدينة
        category = Category.objects.filter(name__icontains=university_name).first()
        if not category:
            return f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'."

        city = City.objects.filter(name__icontains=city_name, category=category).first()
        if not city:
            return f"عفواً، لم أتمكن من العثور على مدينة '{city_name}' مرتبطة بجامعة '{university_name}'."

        # جلب الحجوزات للمدينة والجامعة المحددة (لرحلات الذهاب)
        today = timezone.localdate()
        bookings = FormReservation.objects.filter(
            category=category,
            going_city=city,
            trip_date__gte=today # يمكن تعديل التاريخ حسب الحاجة
        ).order_by('going_pickup_location')

        if not bookings.exists():
            return f"لا توجد حجوزات قادمة في مدينة '{city.name}' لجامعة '{category.name}'."

        response_text = f"تقرير الحجوزات في مدينة '{city.name}' لجامعة '{category.name}':\n\n"
        
        # تجميع المستخدمين حسب نقطة الركوب
        pickup_points = {}
        for booking in bookings:
            pickup_location = booking.going_pickup_location or "غير محددة"
            if pickup_location not in pickup_points:
                pickup_points[pickup_location] = []
            
            student_info = f"{booking.student_name} (تاريخ الرحلة: {booking.trip_date})"
            pickup_points[pickup_location].append(student_info)

        # بناء النص النهائي
        for location, students in pickup_points.items():
            response_text += f"📍 نقطة الركوب: {location}\n"
            for student in students:
                response_text += f"  - {student}\n"
            response_text += "\n"

        return response_text

    except Exception as e:
        return f"حدث خطأ أثناء جلب تفاصيل الحجوزات: {str(e)}"
import googlemaps
from datetime import datetime, timedelta

# تهيئة عميل Google Maps
GOOGLE_MAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

def get_complete_route_analysis(university_name):
    """
    تحليل شامل لخط السير، مع إرجاع تقرير نصي وإحداثيات لرسم الخريطة.
    (نسخة معدلة لتدعم رسم الخرائط)
    """
    try:
        # --- 1. جلب البيانات الأساسية (لا تغيير كبير هنا) ---
        cleaned_name = re.sub(r'جامعة|جامعه|كليه|كلية|university|college', '', university_name, flags=re.IGNORECASE).strip()
        category = Category.objects.filter(name__icontains=cleaned_name).first()
        if not category:
            return {"report": f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'.", "route_path": []}

        cities = City.objects.filter(category=category, is_active=True)
        if not cities.exists():
            return {"report": f"لا توجد مدن متاحة لجامعة '{category.name}'.", "route_path": []}

        today = timezone.localdate()
        bookings = FormReservation.objects.filter(
            category=category,
            going_city__in=cities,
            status__in=['confirmed', 'cash', 'subscription'],
            trip_date__gte=today
        )
        if not bookings.exists():
            return {"report": f"لا توجد حجوزات نشطة لجامعة '{category.name}'.", "route_path": []}

        # --- 2. تجميع النقاط والحصول على إحداثياتها ---
        locations_with_cities = {}
        for booking in bookings:
            if booking.going_city and booking.going_pickup_location:
                city_name = booking.going_city.name
                location_name = booking.going_pickup_location.strip()
                
                if location_name and location_name != "غير محددة":
                    if city_name not in locations_with_cities:
                        locations_with_cities[city_name] = {
                            'bookings_count': 0,
                            'locations': {} # تغيير set إلى dict لتخزين الإحداثيات
                        }
                    
                    locations_with_cities[city_name]['bookings_count'] += 1
                    # استخدام اسم النقطة كمفتاح لتجنب التكرار
                    if location_name not in locations_with_cities[city_name]['locations']:
                        locations_with_cities[city_name]['locations'][location_name] = {'coords': None}

        # الحصول على إحداثيات الجامعة
        try:
            university_geocode = gmaps.geocode(f"{category.name}, Egypt")
            university_coords = (university_geocode[0]['geometry']['location']['lat'], university_geocode[0]['geometry']['location']['lng'])
        except Exception:
            university_coords = (30.0444, 31.2357)

        # الحصول على إحداثيات النقاط داخل كل مدينة
        for city_name, data in locations_with_cities.items():
            for location in data['locations']:
                try:
                    location_geocode = gmaps.geocode(f"{location}, {city_name}, Egypt")
                    if location_geocode:
                        coords = (location_geocode[0]['geometry']['location']['lat'], location_geocode[0]['geometry']['location']['lng'])
                        data['locations'][location]['coords'] = coords
                except Exception as e:
                    print(f"Error geocoding {location}, {city_name}: {e}")
                    continue

        # --- 3. ترتيب النقاط الفردية (وليس المدن) حسب بعدها عن الجامعة ---
        all_points_sorted = []
        for city_name, data in locations_with_cities.items():
            for location, loc_data in data['locations'].items():
                if loc_data['coords']:
                    try:
                        dist_matrix = gmaps.distance_matrix(loc_data['coords'], university_coords, mode='driving')
                        duration_seconds = dist_matrix['rows'][0]['elements'][0].get('duration', {}).get('value', 99999)
                        all_points_sorted.append({
                            "name": location,
                            "city": city_name,
                            "coords": loc_data['coords'],
                            "duration_to_uni": duration_seconds
                        })
                    except Exception:
                        continue
        
        # ترتيب كل النقاط من الأبعد إلى الأقرب
        all_points_sorted.sort(key=lambda p: p['duration_to_uni'], reverse=True)

        if not all_points_sorted:
            return {"report": "لم يتم العثور على إحداثيات لأي من نقاط الركوب.", "route_path": []}

        # --- 4. بناء التقرير النصي ومسار الخريطة ---
        report = f"🚌 **خطة السير المقترحة لجامعة {category.name}**\n\n"
        report += f"📊 **إجمالي الحجوزات:** {bookings.count()} راكب في {len(all_points_sorted)} نقطة.\n\n"
        report += "🗺️ **خط السير المقترح (مرتب جغرافياً من الأبعد للأقرب):**\n"

        route_path_for_map = []
        for i, point in enumerate(all_points_sorted, 1):
            report += f"   {i}. {point['name']} ({point['city']})\n"
            route_path_for_map.append(point['coords'])
        
        report += f"   🏁 **الوصول إلى {category.name}**\n"
        route_path_for_map.append(university_coords)

        # --- 5. إرجاع القاموس النهائي ---
        return {
            "report": report,
            "route_path": route_path_for_map
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"report": f"حدث خطأ فني أثناء تحليل خط السير: {str(e)}", "route_path": []}

def calculate_arrival_time(minutes):
    """حساب وقت الوصول بناءً على الدقائق من الآن"""
    from datetime import datetime, timedelta
    now = datetime.now()
    arrival = now + timedelta(minutes=minutes)
    return arrival.strftime("%I:%M %p")

def get_general_bookings_stats():
    """
    جلب إحصائية عامة للحجوزات في النظام
    """
    try:
        today = timezone.localdate()
        
        # إحصائيات الحجوزات
        total_bookings = FormReservation.objects.count()
        today_bookings = FormReservation.objects.filter(trip_date=today).count()
        upcoming_bookings = FormReservation.objects.filter(trip_date__gte=today).count()
        
        # الحجوزات حسب الحالة
        pending_count = FormReservation.objects.filter(status='pending').count()
        confirmed_count = FormReservation.objects.filter(status='confirmed').count()
        cash_count = FormReservation.objects.filter(status='cash').count()
        subscription_count = FormReservation.objects.filter(status='subscription').count()
        
        response_text = f"📊 إحصائية الحجوزات العامة:\n\n"
        response_text += f"• إجمالي الحجوزات: {total_bookings}\n"
        response_text += f"• حجوزات اليوم ({today}): {today_bookings}\n"
        response_text += f"• الحجوزات القادمة: {upcoming_bookings}\n\n"
        response_text += f"• قيد الانتظار: {pending_count}\n"
        response_text += f"• مؤكدة: {confirmed_count}\n"
        response_text += f"• نقداً: {cash_count}\n"
        response_text += f"• اشتراك: {subscription_count}\n\n"
        response_text += "لمعرفة تفاصيل أكثر، اسأل عن حجوزات جامعة أو مدينة محددة."
        
        return response_text

    except Exception as e:
        return f"حدث خطأ أثناء جلب إحصائية الحجوزات: {str(e)}"
def get_optimized_routes(university_name, max_passengers_per_bus=50, min_passengers_per_bus=18):
    """
    إنشاء خطوط سير متعددة ومحسنة للعربيات المختلفة
    """
    try:
        # تنظيف اسم الجامعة
        cleaned_name = re.sub(r'جامعة|جامعه|كليه|كلية|university|college', '', university_name, flags=re.IGNORECASE).strip()
        
        # البحث عن الجامعة
        category = Category.objects.filter(name__icontains=cleaned_name).first()
        if not category:
            return f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'."

        # جلب الحجوزات المؤكدة للرحلات القادمة
        today = timezone.localdate()
        bookings = FormReservation.objects.filter(
            category=category,
            status__in=['confirmed', 'cash', 'subscription'],
            trip_date__gte=today
        )

        if not bookings.exists():
            return f"لا توجد حجوزات نشطة لجامعة '{category.name}'."

        # تجميع النقاط والمدن مع عدد الركاب
        locations_data = {}
        for booking in bookings:
            if booking.going_city and booking.going_pickup_location:
                city_name = booking.going_city.name
                location_name = booking.going_pickup_location.strip()
                
                if location_name and location_name != "غير محددة":
                    key = f"{city_name}||{location_name}"
                    if key not in locations_data:
                        locations_data[key] = {
                            'city': city_name,
                            'location': location_name,
                            'passengers': 0,
                            'coordinates': None
                        }
                    locations_data[key]['passengers'] += 1

        # إذا لا توجد نقاط محددة
        if not locations_data:
            return f"لا توجد نقاط ركوب محددة في الحجوزات."

        # الحصول على إحداثيات الجامعة
        try:
            university_geocode = gmaps.geocode(f"{category.name} مصر")
            if university_geocode:
                university_location = university_geocode[0]['geometry']['location']
                university_coords = (university_location['lat'], university_location['lng'])
            else:
                university_coords = (30.0444, 31.2357)
        except:
            university_coords = (30.0444, 31.2357)

        # الحصول على إحداثيات النقاط وحساب المسافات
        locations_list = []
        for key, data in locations_data.items():
            try:
                location_geocode = gmaps.geocode(f"{data['location']}، {data['city']} مصر")
                if location_geocode:
                    loc_location = location_geocode[0]['geometry']['location']
                    data['coordinates'] = (loc_location['lat'], loc_location['lng'])
                    
                    # حساب المسافة إلى الجامعة
                    distance_matrix = gmaps.distance_matrix(
                        origins=data['coordinates'],
                        destinations=university_coords,
                        mode="driving",
                        departure_time=datetime.now() + timedelta(hours=1)
                    )
                    
                    if distance_matrix['rows'][0]['elements'][0]['status'] == 'OK':
                        duration_text = distance_matrix['rows'][0]['elements'][0]['duration']['text']
                        # تحويل الوقت إلى دقائق
                        minutes = 0
                        time_parts = duration_text.split()
                        for i, part in enumerate(time_parts):
                            if 'hour' in part or 'ساعة' in part:
                                minutes += int(time_parts[i-1]) * 60
                            elif 'min' in part or 'دقيقة' in part:
                                minutes += int(time_parts[i-1])
                        
                        data['time_to_university'] = minutes
                        locations_list.append(data)
            except:
                continue

        if not locations_list:
            return "لم يتم العثور على إحداثيات للنقاط."

        # ترتيب النقاط حسب البعد عن الجامعة (الأبعد أولاً)
        locations_list.sort(key=lambda x: x['time_to_university'], reverse=True)

        # تقسيم النقاط إلى خطوط سير
        routes = []
        current_route = {
            'passengers': 0,
            'locations': [],
            'total_time': 0,
            'estimated_duration': 0
        }

        for location in locations_list:
            # إذا كانت العربية الحالية ممتلئة أو إضافة هذه النقطة تتجاوز السعة
            if (current_route['passengers'] + location['passengers'] > max_passengers_per_bus or
                (current_route['passengers'] >= min_passengers_per_bus and 
                 current_route['passengers'] + location['passengers'] > max_passengers_per_bus)):
                
                if current_route['locations']:  # تأكد أن الخط به نقاط
                    routes.append(current_route)
                    current_route = {
                        'passengers': 0,
                        'locations': [],
                        'total_time': 0,
                        'estimated_duration': 0
                    }

            # إضافة النقطة إلى الخط الحالي
            current_route['passengers'] += location['passengers']
            current_route['locations'].append(location)
            current_route['total_time'] += location['time_to_university']
            
            # تقدير مدة الخط (وقت أطول نقطة + وقت التجميع)
            pickup_time = len(current_route['locations']) * 5  # 5 دقائق لكل نقطة
            current_route['estimated_duration'] = max(current_route['estimated_duration'], 
                                                     location['time_to_university']) + pickup_time

        # إضافة آخر خط إذا كان به نقاط
        if current_route['locations']:
            routes.append(current_route)

        # تحسين خطوط السير وتجميع النقاط المتقاربة
        optimized_routes = []
        for i, route in enumerate(routes, 1):
            if route['locations']:
                # تجميع النقاط حسب المدينة
                cities_in_route = {}
                for loc in route['locations']:
                    if loc['city'] not in cities_in_route:
                        cities_in_route[loc['city']] = []
                    cities_in_route[loc['city']].append(loc)
                
                # ترتيب المدن حسب البعد عن الجامعة
                sorted_cities = sorted(cities_in_route.items(), 
                                     key=lambda x: max(loc['time_to_university'] for loc in x[1]), 
                                     reverse=True)
                
                optimized_route = {
                    'bus_number': i,
                    'total_passengers': route['passengers'],
                    'estimated_duration': route['estimated_duration'],
                    'cities_order': [],
                    'cities_details': {}
                }
                
                for city_name, city_locations in sorted_cities:
                    optimized_route['cities_order'].append(city_name)
                    optimized_route['cities_details'][city_name] = {
                        'locations': [loc['location'] for loc in city_locations],
                        'passengers': sum(loc['passengers'] for loc in city_locations),
                        'max_time': max(loc['time_to_university'] for loc in city_locations)
                    }
                
                optimized_routes.append(optimized_route)

        # بناء التقرير
        report = f"🚌 خطوط السير المحسنة لجامعة {category.name}\n\n"
        report += f"📊 إجمالي الحجوزات: {bookings.count()} راكب\n"
        report += f"🚐 عدد العربيات المطلوبة: {len(optimized_routes)}\n\n"

        for route in optimized_routes:
            report += f"🚐 العربية #{route['bus_number']}\n"
            report += f"   👥 عدد الركاب: {route['total_passengers']}\n"
            report += f"   ⏰ المدة المتوقعة: {route['estimated_duration']} دقيقة\n"
            report += f"   🗺️ خط السير:\n"
            
            for i, city_name in enumerate(route['cities_order'], 1):
                city_data = route['cities_details'][city_name]
                report += f"      {i}. {city_name}\n"
                report += f"          👥 الركاب: {city_data['passengers']}\n"
                report += f"          🚏 النقاط: {', '.join(city_data['locations'])}\n"
                report += f"          ⏰ الوقت للجامعة: {city_data['max_time']} دقيقة\n"
            
            report += f"      🏁 الوصول إلى الجامعة\n\n"

        report += "💡 ملاحظات مهمة:\n"
        report += "- تم تحسين الخطوط لتجنب المرور على نفس الطريق أكثر من مرة\n"
        report += "- كل عربية تخدم مجموعة من المدن المتقاربة جغرافياً\n"
        report += "- الأوقات تشمل وقت التجميع في النقاط (5 دقائق لكل نقطة)\n"
        report += "- السعة القصوى للعربية: 50 راكب، الدنيا: 18 راكب\n"

        return report

    except Exception as e:
        return f"حدث خطأ أثناء إنشاء خطوط السير: {str(e)}"
# --- الدالة الرئيسية بعد التعديل ---
# Imports الأساسية التي قد تحتاجها في أعلى الملف
import re
from datetime import date, timedelta
import traceback

from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Count

# افترض أن هذه هي الموديلز الخاصة بك
# from .models import Category, City, FormReservation, Trip, Bus

# ==============================================================================
# 1. الدوال المساعدة والذكية
# ==============================================================================

def clean_location_name(location_name ):
    """
    دالة ذكية لتنظيف وتوحيد أسماء نقاط الركوب.
    - تزيل الأرقام (العربية والإنجليزية).
    - تزيل علامات الترقيم الشائعة والأوقات (am/pm).
    - تزيل المسافات الزائدة.
    """
    if not location_name:
        return ""
    
    cleaned_name = str(location_name).lower()
    cleaned_name = re.sub(r'(am|pm|ص|م)', '', cleaned_name)
    cleaned_name = re.sub(r'[0-9٠-٩]', '', cleaned_name)
    cleaned_name = re.sub(r'[:\-\.,_#*]', ' ', cleaned_name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name)
    return cleaned_name.strip()

def get_bus_size_suggestion(passenger_count):
    """
    تقترح حجم الحافلة بناءً على عدد الركاب.
    """
    if passenger_count <= 14:
        return "H1 (14 راكب)"
    elif passenger_count <= 28:
        return "كوستر (28 راكب)"
    elif passenger_count <= 50:
        return "باص كبير (50 راكب)"
    else:
        return f"تحتاج أكثر من باص ({passenger_count} راكب)"

def create_draft_trip(category, trip_date, passenger_count, route_name, trip_type_value):
    # ... (نفس الدالة السابقة المصححة)
    try:
        trip_name = f"مقترح: {route_name} - {trip_date}"
        new_trip = Trip.objects.create(
            name=trip_name, category=category, date=trip_date,
            status='draft', trip_type=trip_type_value,
            notes=f"تم إنشاء هذه الرحلة تلقائيًا كاقتراح لـ {passenger_count} راكب."
        )
        return new_trip
    except Exception as e:
        print(f"فشل في إنشاء رحلة مسودة: {e}")
        return None
# ==============================================================================
# 2. الدوال الوظيفية الأساسية (بما في ذلك الدالة الجديدة والمحسّنة)
# ==============================================================================

# ... (ضع هنا دوالك الأخرى مثل get_cities_for_university, get_bookings_for_city, etc.)
# ... (get_complete_route_analysis, get_optimized_routes, get_general_bookings_stats)

def predict_trip_template(university_name, trip_direction='going'):
    """
    يطابق الحجوزات الجديدة مع قوالب رحلات تاريخية (قديمة ونشطة)
    ويقترح أفضل رحلة تاريخية لتكون نموذجاً للرحلة الجديدة.
    """
    try:
        category = Category.objects.filter(name__icontains=university_name).first()
        if not category:
            return f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'."

        # --- الخطوة 1: جلب وتحليل الحجوزات الجديدة ---
        pickup_field = 'going_pickup_location' if trip_direction == 'going' else 'return_pickup_location'
        trip_type_filter = ['ذهاب', 'ذهاب وعودة'] if trip_direction == 'going' else ['عودة', 'ذهاب وعودة']
        
        today = date.today()
        # نفترض أننا نحلل حجوزات يوم معين، وليكن اليوم
        target_date = today 
        target_weekday = target_date.weekday() # 0=Monday, 6=Sunday

        new_bookings = FormReservation.objects.filter(
            category=category,
            trip__isnull=True,
            trip_date=target_date, # نركز على حجوزات يوم محدد
            status__in=['confirmed', 'cash', 'subscription'],
            trip_type__in=trip_type_filter
        ).exclude(**{f'{pickup_field}__isnull': True, f'{pickup_field}__exact': ''})

        if not new_bookings.exists():
            return f"لا توجد حجوزات {trip_direction} جديدة ليوم {target_date} لتحليلها."

        new_bookings_locations = {clean_location_name(loc) for loc in new_bookings.values_list(pickup_field, flat=True) if loc}
        total_new_passengers = new_bookings.count()

        report = f"🔮 **توقع قالب الرحلة الأنسب لحجوزات يوم {target_date}**\n\n"
        report += f"تم العثور على **{total_new_passengers}** حجز جديد في **{len(new_bookings_locations)}** نقطة مختلفة.\n"

        # --- الخطوة 2: تحليل جميع الرحلات التاريخية كقوالب ---
        historical_templates = []
        # نبحث في كل الرحلات السابقة لهذه الجامعة التي لها خط سير محدد
        all_past_trips = Trip.objects.filter(
            category=category, 
            route__isnull=False
        ).exclude(route__exact='').order_by('-date')

        # لتجنب تكرار نفس خط السير، نستخدم قاموس لتخزين القوالب الفريدة
        unique_templates = {}

        for trip in all_past_trips:
            cleaned_route_points = {clean_location_name(point) for point in trip.route.splitlines() if point}
            if not cleaned_route_points:
                continue

            # نستخدم tuple من النقاط المجمدة كمفتاح لضمان عدم التكرار
            template_key = frozenset(cleaned_route_points)
            if template_key not in unique_templates:
                unique_templates[template_key] = {
                    "trip_name": trip.trip_name or f"رحلة تاريخ {trip.date}",
                    "weekday": trip.date.weekday() if trip.date else -1,
                    "route_points": cleaned_route_points,
                    "trip_id": trip.id
                }
        
        historical_templates = list(unique_templates.values())

        if not historical_templates:
            return report + "\nلم يتم العثور على أي رحلات تاريخية لها خطوط سير مسجلة لتحليلها."

        # --- الخطوة 3: حساب درجة التطابق لكل قالب ---
        match_scores = []
        for template in historical_templates:
            # 1. حساب تطابق النقاط (الأهم)
            matched_points = new_bookings_locations.intersection(template['route_points'])
            unmatched_points = new_bookings_locations.difference(template['route_points'])
            
            # درجة تطابق النقاط (كنسبة مئوية)
            if not new_bookings_locations: continue
            points_score = (len(matched_points) / len(new_bookings_locations)) * 100

            # 2. حساب تطابق يوم الأسبوع (نقاط إضافية)
            day_score = 20 if template['weekday'] == target_weekday else 0

            # 3. حساب إجمالي الدرجة (نعطي وزن أكبر لتطابق النقاط)
            total_score = (points_score * 0.8) + day_score

            if total_score > 30: # نعرض فقط التطابقات التي تزيد عن 30%
                match_scores.append({
                    "score": total_score,
                    "template_name": template['trip_name'],
                    "matched_points": matched_points,
                    "unmatched_points": unmatched_points,
                    "weekday_match": template['weekday'] == target_weekday
                })

        # --- الخطوة 4: عرض أفضل التوصيات ---
        if not match_scores:
            report += "\nلم يتم العثور على رحلات تاريخية ذات تشابه كافٍ مع الحجوزات الجديدة."
            return report

        # ترتيب التوصيات من الأعلى للأقل درجة
        sorted_matches = sorted(match_scores, key=lambda x: x['score'], reverse=True)

        report += "\n--- **أفضل قوالب الرحلات المتطابقة** ---\n"
        for i, match in enumerate(sorted_matches[:3], 1): # عرض أفضل 3 توصيات
            report += f"\n**التوصية #{i} (درجة التطابق: {match['score']:.0f}%)**\n"
            report += f"   - **القالب المقترح:** رحلة مشابهة لـ **'{match['template_name']}'**\n"
            if match['weekday_match']:
                report += f"   - ✅ **تطابق في يوم الأسبوع** (كلاهما يوم {target_date.strftime('%A')})\n"
            
            report += f"   - **عدد الركاب:** {total_new_passengers}\n"
            report += f"   - **نقاط متطابقة ({len(match['matched_points'])}):** {', '.join(match['matched_points']) or 'لا يوجد'}\n"
            if match['unmatched_points']:
                report += f"   - **نقاط جديدة تحتاج إضافة ({len(match['unmatched_points'])}):** {', '.join(match['unmatched_points'])}\n"
        
        return report

    except Exception as e:
        traceback.print_exc()
        return f"حدث خطأ فني أثناء محاولة توقع قالب الرحلة: {str(e)}"


def predict_and_suggest_trips(university_name, trip_direction='going', create_drafts=False, max_passengers_per_bus=50):
    """
    تحليل وتوزيع الحجوزات الجديدة، مع اقتراح باصات فعلية بناءً على تحليل تاريخي لأسطول الشركة.
    """
    try:
        category = Category.objects.filter(name__icontains=university_name).first()
        if not category:
            return f"عفواً، لم أتمكن من العثور على جامعة باسم '{university_name}'."

        # --- الخطوة 1: تحليل الأسطول التاريخي لهذه الجامعة ---
        historical_bus_routes = defaultdict(set)
        # ابحث في كل الرحلات السابقة لهذه الجامعة التي كان لها باص
        past_trips_with_buses = Trip.objects.filter(
            category=category, 
            bus__isnull=False
        ).select_related('bus').order_by('-date')[:500] # تحليل آخر 500 رحلة

        for trip in past_trips_with_buses:
            # تنظيف النقاط من حقل 'route' في موديل Trip
            cleaned_route_points = {clean_location_name(point) for point in trip.route.splitlines() if point}
            historical_bus_routes[trip.bus.name].update(cleaned_route_points)

        report = f"🔮 **اقتراحات ذكية لتوزيع الحجوزات لجامعة {category.name} (اتجاه: {trip_direction})**\n\n"
        
        # --- الخطوة 2: جلب الحجوزات الجديدة (مع التأكد من الاتجاه) ---
        pickup_field = 'going_pickup_location' if trip_direction == 'going' else 'return_pickup_location'
        city_field = 'going_city' if trip_direction == 'going' else 'return_city'
        trip_type_value = 'one_way' if trip_direction == 'going' else 'return'

        today = date.today()
        new_bookings = FormReservation.objects.filter(
            category=category, trip__isnull=True, trip_date__gte=today,
            status__in=['confirmed', 'cash', 'subscription'],
            trip_type__in=['ذهاب', 'ذهاب وعودة'] if trip_direction == 'going' else ['عودة', 'ذهاب وعودة']
        ).exclude(**{f'{pickup_field}__isnull': True}).exclude(**{f'{pickup_field}__exact': ''}).select_related(city_field)

        if not new_bookings.exists():
            return f"لا توجد حجوزات {trip_direction} جديدة غير موزعة لهذه الجامعة."
        
        report += f"تم العثور على **{new_bookings.count()}** حجز {trip_direction} جديد غير مرتبط برحلات.\n"

        # --- الخطوة 3: تجميع الحجوزات الجديدة ---
        new_bookings_summary = defaultdict(lambda: {'passenger_count': 0, 'raw_names': set()})
        for booking in new_bookings:
            raw_location = getattr(booking, pickup_field)
            cleaned_location = clean_location_name(raw_location)
            city_obj = getattr(booking, city_field)
            city = city_obj.name if city_obj else "غير محددة"
            if not cleaned_location: continue
            key = (city, cleaned_location)
            new_bookings_summary[key]['passenger_count'] += 1
            new_bookings_summary[key]['raw_names'].add(raw_location)

        report += "\n--- **مقترحات لرحلات جديدة** ---\n"
        
        # --- الخطوة 4: التوزيع الجغرافي (كما في السابق) ---
        # (هذا الجزء يقوم بالترتيب الجغرافي وتقسيم الباصات)
        geocoded_points = []
        # ... (منطق جلب الإحداثيات والترتيب، لا تغيير كبير هنا)
        
        # --- الخطوة 5: خوارزمية التجميع مع المطابقة الذكية للباصات ---
        sorted_points = [] # افترض أن هذه القائمة تم ملؤها وترتيبها جغرافياً
        bus_number = 1
        points_to_process = list(new_bookings_summary.items()) # استخدام النقاط المجمعة

        while points_to_process:
            current_bus_passengers = 0
            current_bus_route_locations = set()
            current_bus_route_display = []

            # ابدأ بأبعد نقطة (إذا تم ترتيبها جغرافياً) أو أي نقطة
            # ... (منطق أكثر تقدماً يمكن إضافته هنا لاختيار نقطة البداية)

            temp_points = list(points_to_process)
            for key, data in temp_points:
                city, location = key
                if current_bus_passengers + data['passenger_count'] <= max_passengers_per_bus:
                    current_bus_passengers += data['passenger_count']
                    current_bus_route_locations.add(location)
                    current_bus_route_display.append(location)
                    points_to_process.remove((key, data))

            if current_bus_route_locations:
                # --- المطابقة الذكية للباص ---
                best_bus_match = None
                highest_match_score = 0
                
                for bus_name, bus_historical_route in historical_bus_routes.items():
                    # حساب عدد النقاط المشتركة
                    matched_points = current_bus_route_locations.intersection(bus_historical_route)
                    match_score = len(matched_points)
                    
                    if match_score > highest_match_score:
                        highest_match_score = match_score
                        best_bus_match = bus_name
                
                report += f"\n     - **مقترح رحلة (باص #{bus_number}):**\n"
                report += f"       - **عدد الركاب:** {current_bus_passengers}\n"
                
                if best_bus_match:
                    match_percentage = (highest_match_score / len(current_bus_route_locations)) * 100
                    report += f"       - **الباص المقترح:** **{best_bus_match}** (يطابق {match_percentage:.0f}% من نقاط المسار تاريخياً)\n"
                else:
                    report += f"       - **الباص المقترح:** لا يوجد باص تاريخي يطابق هذا المسار، اقترح باص جديد.\n"

                report += f"       - **خط السير المقترح:** {' → '.join(current_bus_route_display)}\n"
                bus_number += 1
        
        return report

    except Exception as e:
        traceback.print_exc()
        return f"حدث خطأ فني أثناء محاولة التنبؤ بالرحلات: {str(e)}"


# ==============================================================================
# 3. الدالة الرئيسية للعرض (View) - لا تغيير هنا
# ==============================================================================

# ==============================================================================
# 3. الدالة الرئيسية للعرض (View) بعد التعديل النهائي
# ==============================================================================
# ==============================================================================
# 3. الدالة الرئيسية للعرض (View) - النسخة النهائية المنظمة
# ==============================================================================

@login_required
def ask_gemini(request):
    # --- 1. التحقق الأولي من السؤال والمستخدم ---
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"error": "لا يوجد سؤال"}, status=400)

    user = request.user
    # التحقق من صلاحيات الأدمن في البداية
    if not user.is_staff:
        # إذا كان المستخدم ليس أدمن، يمكنه فقط الاستعلام عن حجوزاته
        if "حجوزاتي" in q or "رحلاتي" in q:
            context_data = "خاصية عرض حجوزات المستخدم قيد التطوير."
            return JsonResponse({"answer": context_data})
        else:
            return JsonResponse({"answer": "عفواً، هذه الخدمة متاحة للمسؤولين فقط."}, status=403)

    # --- 2. تعريف كل الأنماط الممكنة (من الأحدث إلى الأقدم) ---
    context_data = ""
    
    # النمط الأكثر تقدماً: مطابقة قوالب الرحلات التاريخية
    match_template = re.search(r"(?:طابق|توقع قالب|ما هي انسب رحله لـ|اي رحله انزلها لـ)\s*(?:حجوزات|رحلات)?\s*(?:جامعة|لـ|في)\s*(.+)", q, re.IGNORECASE)
    
    # نمط إنشاء الرحلات المقترحة (جغرافياً)
    match_predict_trips = re.search(r"(?:توقع|اقترح|توزيع|تسكين|انشاء|إنشاء)\s*(?:رحلات|حجوزات|مسودات)\s*(?:جديدة|الجديدة)?\s*(?:لجامعة|لـ|في)\s*(.+)", q, re.IGNORECASE)
    
    # الأنماط القديمة
    match_cities = re.search(r"(?:ما هي|عرض|قائمة|اسماء|ايه|عاوز|ابي|اريد)\s*(?:المدن|مدن|مدينة|مدنها)\s*(?:التابعة|الخاصة|ل|لـ|في)?\s*(?:جامعة|كليه)?\s*(.+)", q, re.IGNORECASE)
    match_bookings = re.search(r"(?:حجوزات|الحجوزات|مين حاجز في)\s+(?:مدينة|لمدينة)\s+(.+?)\s+(?:لجامعة|التابعة لـ)\s+(.+)", q, re.IGNORECASE)
    match_general_bookings = re.search(r"(?:مين|في مين|مين فيه|ايه|عاوز اعرف|كم|عدد)\s*(?:فيه|في|عندنا|عندك)\s*(?:حجوزات|حجز|حاجزين|حجازات)", q, re.IGNORECASE)
    match_route_analysis = re.search(r"(?:تحليل|تقرير|خط سير|نقاط|الحجوزات)\s*(?:كامل|شامل|كل|جميع)?\s*(?:لجامعة|لـ|في)\s*(.+)", q, re.IGNORECASE)
    match_optimized_routes = re.search(r"(?:خطوط سير|عربيات|توزيع|شغل)\s*(?:عربيات|باصات|اتوبيسات)?\s*(?:لجامعة|لـ|في)\s*(.+)", q, re.IGNORECASE)

    # --- 3. تنفيذ المنطق بناءً على النمط المتطابق ---
    if match_template:
        university_name = match_template.group(1).strip()
        direction = 'return' if 'عودة' in q or 'العودة' in q else 'going'
        context_data = predict_trip_template(university_name, trip_direction=direction)

    elif match_predict_trips:
        university_name = match_predict_trips.group(1).strip()
        direction = 'return' if 'عودة' in q or 'العودة' in q else 'going'
        create_drafts = 'انشاء' in q or 'إنشاء' in q or 'مسودات' in q
        # تأكد من أن لديك دالة predict_and_suggest_trips في الكود
        context_data = predict_and_suggest_trips(university_name, trip_direction=direction, create_drafts=create_drafts)

    elif match_cities:
        university_name = match_cities.group(1).strip()
        # تأكد من أن لديك دالة get_cities_for_university
        context_data = get_cities_for_university(university_name)

    elif match_bookings:
        city_name = match_bookings.group(1).strip()
        university_name = match_bookings.group(2).strip()
        # تأكد من أن لديك دالة get_bookings_for_city
        context_data = get_bookings_for_city(university_name, city_name)
        
    elif match_general_bookings:
        # تأكد من أن لديك دالة get_general_bookings_stats
        context_data = get_general_bookings_stats()

    elif match_route_analysis:
        university_name = match_route_analysis.group(1).strip()
        # تأكد من أن لديك دالة get_complete_route_analysis
        context_data = get_complete_route_analysis(university_name)

    elif match_optimized_routes:
        university_name = match_optimized_routes.group(1).strip()
        # تأكد من أن لديك دالة get_optimized_routes
        context_data = get_optimized_routes(university_name)

    else:
        # إذا لم يتطابق أي نمط
        context_data = "لم أتعرف على هذا السؤال. جرب 'طابق حجوزات جامعة...' أو 'اقترح رحلات لجامعة...'."

    # --- 4. إرسال الاستجابة النهائية ---
    return JsonResponse({"answer": context_data})

def ask_gemini_page(request):
    return render(request, "ask_gemini.html")
# api/views.py

from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.utils import timezone
from django.db.models import Count

# استيراد النماذج و Serializers
from Anaconda_bus_APP.models import Trip, Booking, passenger, Bus, FormReservation
from .serializers import (
    TripListSerializer, TripDetailSerializer, BookingCreateUpdateSerializer,
    PassengerDetailSerializer, BookingStatsSerializer, BusLocationSerializer
)

# --- 1. واجهات إدارة الرحلات والحجوزات ---

from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

# ... استيراد باقي النماذج والـ Serializers ...

# --- 1. واجهات إدارة الرحلات والحجوزات ---

@authentication_classes([SessionAuthentication, BasicAuthentication]) # 1. تحديد طرق المصادقة
@permission_classes([IsAuthenticated, IsAdminUser]) # 2. تحديد الأذونات المطلوبة
@api_view(['GET'])
def get_active_trips(request):
    """
    API لجلب جميع الرحلات النشطة في تاريخ اليوم.
    يمكن تمرير تاريخ معين كـ query parameter: /api/trips/active/?date=YYYY-MM-DD
    """
    target_date_str = request.query_params.get('date', None)
    if target_date_str:
        target_date = timezone.datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        target_date = timezone.localdate()
        
    active_trips = Trip.objects.filter(date=target_date, is_active=True)
    serializer = TripListSerializer(active_trips, many=True)
    return Response(serializer.data)

class TripDetailView(generics.RetrieveAPIView):
    """
    API للحصول على تفاصيل رحلة معينة وكل الحجوزات المرتبطة بها.
    """
            # --- السطرين المطلوب إضافتهما ---
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    # ---------------------------------
    queryset = Trip.objects.all()
    serializer_class = TripDetailSerializer
    lookup_field = 'id' # للبحث باستخدام الرقم التعريفي



class BookingCreateView(generics.CreateAPIView):
    """
    API لإنشاء حجز جديد.
    """
        # --- السطرين المطلوب إضافتهما ---
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    # ---------------------------------
    
    queryset = Booking.objects.all()
    serializer_class = BookingCreateUpdateSerializer

class BookingCancelView(views.APIView):
    """
    API لإلغاء حجز قائم.
    """
            # --- السطرين المطلوب إضافتهما ---
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    # ---------------------------------
    def post(self, request, id, format=None):
        try:
            booking = Booking.objects.get(id=id)
            # يمكنك إضافة منطق للتحقق من إمكانية الإلغاء (مثلاً، قبل موعد الرحلة بـ 24 ساعة)
            booking.status = 'cancelled'
            booking.save()
            return Response({'message': f'Booking {id} has been cancelled.'}, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

# --- 2. واجهات إدارة الركاب ---

@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication]) # 1. تحديد طرق المصادقة
@permission_classes([IsAuthenticated, IsAdminUser]) # 2. تحديد الأذونات المطلوبة
def get_passenger_by_phone(request):
    """
    API لجلب بيانات راكب معين باستخدام رقم هاتفه.
    استخدمه هكذا: /api/passengers/by-phone/?phone=+201234567890
    """
            # --- السطرين المطلوب إضافتهما ---
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    # ---------------------------------
    phone_number = request.query_params.get('phone', None)
    if not phone_number:
        return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # تأكد من أن نموذج passenger يحتوي على حقل phone_number
        p = passenger.objects.get(phone_number=phone_number)
        serializer = PassengerDetailSerializer(p)
        return Response(serializer.data)
    except passenger.DoesNotExist:
        return Response({'error': 'Passenger with this phone number not found.'}, status=status.HTTP_404_NOT_FOUND)

# --- 3. واجهات التحليل الذكي ---
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
@api_view(['GET'])
@authentication_classes([SessionAuthentication, BasicAuthentication]) # 1. تحديد طرق المصادقة
@permission_classes([IsAuthenticated, IsAdminUser]) # 2. تحديد الأذونات المطلوبة
def get_booking_stats(request):
    """
    API للحصول على إحصائيات عامة عن الحجوزات.
    """
    today = timezone.localdate()
    stats = {
        'total_bookings': FormReservation.objects.count(),
        'today_bookings': FormReservation.objects.filter(trip_date=today).count(),
        'pending_bookings': FormReservation.objects.filter(status='pending').count(),
        'confirmed_bookings': FormReservation.objects.filter(status__in=['confirmed', 'cash', 'subscription']).count(),
    }
    serializer = BookingStatsSerializer(data=stats)
    serializer.is_valid(raise_exception=True)
    return Response(serializer.validated_data)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .models import passenger, Booking


@api_view(['POST'])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated, IsAdminUser])
def check_student_trips(request):
    """
    API للتحقق من الرحلات الخاصة بطالب باستخدام رقم الهاتف،
    + اقتراح رحلة حالية قريبة بناءً على آخر رحلة سابقة.
    """
    phone_number = request.data.get('phone_number')
    if not phone_number:
        return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # ابحث عن الراكب
        p = passenger.objects.get(phone_number=phone_number)

        # احضر كل الحجوزات
        bookings = Booking.objects.filter(passenger=p).order_by('-booking_date')

        # لو مفيش حجوزات أصلاً
        if not bookings.exists():
            return Response({'student': p.name, 'trips': [], 'suggested_trip': None})

        # آخر رحلة حجزها
        last_booking = bookings.first()
        last_trip = last_booking.Trip

        # بيانات الرحلات السابقة
        trip_data = []
        for booking in bookings:
            if booking.Trip:
                trip_data.append({
                    "trip_id": booking.Trip.id,
                    "trip_name": str(booking.Trip),
                    "trip_type": booking.trip_type,
                    "status": booking.status,
                    "booking_date": booking.booking_date,
                })

        # 👇 من هنا نبدأ نحسب الرحلة المقترحة 👇
        suggested_trip = None

        if last_trip and last_trip.start_destination:
            # البحث عن رحلة بتاريخ اليوم في نفس الكاتيجوري
            # وتكون نقطة البداية مشابهة لنقطة البداية أو النهاية السابقة
            similar_trips = Trip.objects.filter(
                Q(category=last_trip.category),
                Q(date=date.today()),
                Q(is_active=True),
                route__icontains=last_selected_route.strip()
            ).exclude(id=last_trip.id)

            # لو لقينا رحلات قريبة
            if similar_trips.exists():
                closest_trip = similar_trips.first()
                suggested_trip = {
                    "trip_id": closest_trip.id,
                    "trip_name": str(closest_trip),
                    "category": str(closest_trip.category),
                    "date": closest_trip.date,
                    "start_destination": str(closest_trip.start_destination),
                    "end_destination": str(closest_trip.end_destination),
                    "trip_type": closest_trip.trip_type,
                }

        return Response({
            'student': p.name,
            'trips': trip_data,
            'suggested_trip': suggested_trip
        })

    except passenger.DoesNotExist:
        return Response({'error': 'Passenger not found.'}, status=status.HTTP_404_NOT_FOUND)
class BusLiveLocationView(generics.RetrieveAPIView):
    """
    API للحصول على الموقع الجغرافي المباشر لحافلة معينة.
    """
    queryset = Bus.objects.filter(location_sharing_is_active=True)
    serializer_class = BusLocationSerializer
    lookup_field = 'id'

class BusStatusUpdateView(views.APIView):
    """
    API لتحديث حالة الحافلة (مثال بسيط).
    يمكنك تطويره ليكون أكثر تعقيداً.
    """
    def post(self, request, id, format=None):
        try:
            bus = Bus.objects.get(id=id)
            new_status = request.data.get('status') # مثلاً: "arrived", "on_the_way"
            # هنا يمكنك إضافة منطق لتحديث حالة الرحلة أو إرسال إشعارات
            # هذا مثال مبسط جداً
            bus.notes = f"Current status: {new_status}" # افترضنا وجود حقل notes
            bus.save()
            return Response({'message': f'Bus {id} status updated to {new_status}.'}, status=status.HTTP_200_OK)
        except Bus.DoesNotExist:
            return Response({'error': 'Bus not found.'}, status=status.HTTP_404_NOT_FOUND)

# Anaconda_bus_APP/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Trip, Bus, FormReservation, Booking
from .forms import RenewTripForm # ✅ --- استيراد الفورم الجديد --- ✅

# ... (باقي دوال الـ views كما هي) ...
# Anaconda_bus_APP/views.py
from .utils import send_renewal_notification
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Trip, Bus, FormReservation, Booking, Category
from .forms import RenewTripForm

# ... (باقي دوال الـ views) ...
# Anaconda_bus_APP/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from .models import Trip, Bus, FormReservation, Booking, Category
from .forms import RenewTripForm
from .utils import send_renewal_notification # ✅ --- تأكد من وجود دالة الإرسال في utils.py --- ✅
@staff_member_required
def renew_trip_view(request, old_trip_id):
    old_trip = get_object_or_404(Trip, id=old_trip_id)

    if request.method == 'POST':
        form = RenewTripForm(request.POST)
        if form.is_valid():
            new_bus = form.cleaned_data['bus']
            
            # إنشاء الرحلة الجديدة
            new_trip = Trip.objects.create(
                trip_name=form.cleaned_data['trip_name'],
                bus=new_bus,
                category=new_bus.category,
                date=timezone.now().date(),
                start_time=form.cleaned_data['start_time'],
                route=old_trip.route,
                is_active=True,
                is_old=False
            )
            
            # --- جمع كل الركاب من الحجزين ---
            all_bookings = []

            # 1️⃣ حجوزات الفورم
            form_reservations = FormReservation.objects.filter(trip=old_trip).select_related('passenger')
            for booking in form_reservations:
                if booking.passenger:
                    all_bookings.append(('form', booking, booking.passenger))

            # 2️⃣ الحجوزات العادية
            regular_bookings = Booking.objects.filter(Trip=old_trip).select_related('passenger')
            for booking in regular_bookings:
                if booking.passenger:
                    all_bookings.append(('regular', booking, booking.passenger))

            # --- إرسال الإشعارات ---
            sent_count = 0
            failed_count = 0

            for booking_type, booking, passenger in all_bookings:
                success, reason = send_renewal_notification(passenger, new_trip, booking_type)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1

            messages.success(
                request,
                f"✅ تم إنشاء الرحلة الجديدة '{new_trip.trip_name}' بنجاح.\n"
                f"تم إرسال إشعارات إلى {sent_count} راكب.\n"
                f"⚠️ فشل إرسال {failed_count} رسالة." if failed_count else ""
            )
            return redirect('admin:Anaconda_bus_APP_trip_changelist')
    else:
        initial_data = {
            'trip_name': f"{old_trip.trip_name}",
            'start_time': old_trip.start_time,
            'category': old_trip.category,
        }
        form = RenewTripForm(initial=initial_data)
        if old_trip.category:
            form.fields['bus'].queryset = Bus.objects.filter(category=old_trip.category)

    context = {
        'title': f"تجديد الرحلة: {old_trip.trip_name}",
        'form': form,
        'old_trip': old_trip
    }
    return render(request, 'admin/renew_trip_page.html', context)

@staff_member_required
def load_buses_ajax(request):
    """
    View مساعد يتم استدعاؤه عبر AJAX لجلب الحافلات بناءً على الجامعة.
    """
    category_id = request.GET.get('category_id')
    buses = Bus.objects.filter(category_id=category_id).order_by('name')
    return render(request, 'admin/partials/bus_options.html', {'buses': buses})
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import passenger, WhatsAppOTP
import requests

def send_otp_whatsapp(request):
    if request.method == "POST":
        phone = request.POST.get("phone_number")
        try:
            user = passenger.objects.get(phone_number=phone)
        except passenger.DoesNotExist:
            messages.error(request, "رقم الهاتف غير مسجل.")
            return redirect("send_otp_whatsapp")

        # إنشاء OTP جديد
        otp = WhatsAppOTP.generate_otp()
        WhatsAppOTP.objects.create(passenger=user, otp_code=otp)

        # إرسال عبر Ultramsg API
        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
        message = f"رمز التحقق لإعادة تعيين كلمة المرور هو: {otp} (صالح لمدة 5 دقائق)"
        payload = {"token": API_TOKEN, "to": user.phone_number, "body": message}
        requests.post(URL, data=payload)

        messages.success(request, "تم إرسال كود التحقق عبر واتساب ✅")
        return redirect("verify_otp")

    return render(request, "send_otp.html")


def verify_otp(request):
    if request.method == "POST":
        phone = request.POST.get("phone_number")
        otp = request.POST.get("otp")

        try:
            user = passenger.objects.get(phone_number=phone)
            otp_record = WhatsAppOTP.objects.filter(passenger=user, otp_code=otp).last()
            if otp_record and otp_record.is_valid():
                otp_record.is_verified = True
                otp_record.save()
                messages.success(request, "تم التحقق بنجاح ✅")
                return redirect("reset_password")
            else:
                messages.error(request, "كود غير صحيح أو منتهي الصلاحية ❌")
        except passenger.DoesNotExist:
            messages.error(request, "رقم الهاتف غير مسجل.")

    return render(request, "verify_otp.html")
from django.contrib.auth.models import User

def reset_password(request):
    if request.method == "POST":
        phone = request.POST.get("phone_number")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "كلمتا المرور غير متطابقتين.")
            return redirect("reset_password")

        try:
            p = passenger.objects.get(phone_number=phone)
            user = p.user
            user.set_password(new_password)
            user.save()
            messages.success(request, "تم تعيين كلمة مرور جديدة بنجاح ✅")
            return redirect("login")
        except passenger.DoesNotExist:
            messages.error(request, "رقم الهاتف غير مسجل.")
    
    return render(request, "reset_password.html")
import time
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import time
from threading import Lock

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# =========================
# تخزين آخر فريم فقط لكل ESP
# =========================
frames = {}
frames_lock = Lock()

FRAME_TTL = 5  # ثواني – لو ESP وقف


# =========================
# استقبال الفريم من ESP
from datetime import datetime

@csrf_exempt
def upload_frame(request, esp_id):
    """
    ESP32 يبعث آخر فريم
    URL: /allen/upload/<esp_id>/
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    image_data = request.body
    if not image_data:
        return JsonResponse({"error": "No data received"}, status=400)

    with frames_lock:
        frames[esp_id] = {
            "image": image_data,
            "timestamp": time.time()
        }

    # ✅ الطباعة المطلوبة
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        f"ESP ID: {esp_id} | Frame received | Size: {len(image_data)} bytes"
    )

    return JsonResponse({
        "status": "ok",
        "esp_id": esp_id,
        "size": len(image_data)
    })

# =========================
# إرجاع آخر فريم (NO STREAM)
# =========================
def latest_frame(request, esp_id):
    """
    Viewer / AI يطلب آخر فريم فقط
    """
    with frames_lock:
        cam = frames.get(esp_id)

    if not cam:
        return HttpResponse(status=204)  # No Content

    # لو الفريم قديم
    if time.time() - cam["timestamp"] > FRAME_TTL:
        return HttpResponse(status=204)

    return HttpResponse(
        cam["image"],
        content_type="image/jpeg"
    )


# =========================
# صفحة المشاهدة
# =========================
def viewer_page(request):
    return render(request, "viewer.html")


# =========================
# Weekly Booking Views
# =========================

@login_required
def weekly_booking_view(request, category_id):
    """صفحة الحجز الأسبوعي للمستخدم"""
    try:
        # جلب بيانات الطالب والجامعة
        passenger_obj = passenger.objects.get(user=request.user)
        category = Category.objects.get(id=category_id)
        
        # التحقق من أن الطالب ينتمي لهذه الجامعة
        if passenger_obj.category != category:
            messages.error(request, "لا يمكنك الحجز في جامعة غير جامعتك")
            return redirect('my_buses')
        
        # جلب الحجز الأسبوعي الحالي أو إنشاء جديد
        weekly_booking, created = WeeklyBooking.objects.get_or_create(
            passenger=passenger_obj,
            category=category,
            defaults={
                'departure_days': [],
                'return_days': []
            }
        )
        
        if request.method == 'POST':
            form = WeeklyBookingForm(request.POST, instance=weekly_booking)
            if form.is_valid():
                # تحويل الأوقات من string إلى time objects
                cleaned_data = form.cleaned_data
                
                # معالجة الأيام من JSON
                if cleaned_data.get('departure_days'):
                    try:
                        import json
                        departure_days_list = json.loads(cleaned_data['departure_days'])
                        form.instance.departure_days = departure_days_list
                    except (ValueError, json.JSONDecodeError):
                        form.instance.departure_days = []
                
                if cleaned_data.get('return_days'):
                    try:
                        import json
                        return_days_list = json.loads(cleaned_data['return_days'])
                        form.instance.return_days = return_days_list
                    except (ValueError, json.JSONDecodeError):
                        form.instance.return_days = []
                
                # تحويل الأوقات من string إلى time objects
                if cleaned_data.get('departure_time'):
                    try:
                        from datetime import datetime
                        departure_time_obj = datetime.strptime(cleaned_data['departure_time'], '%H:%M').time()
                        form.instance.departure_time = departure_time_obj
                    except ValueError:
                        pass
                
                if cleaned_data.get('return_time'):
                    try:
                        from datetime import datetime
                        return_time_obj = datetime.strptime(cleaned_data['return_time'], '%H:%M').time()
                        form.instance.return_time = return_time_obj
                    except ValueError:
                        pass
                
                form.save()
                messages.success(request, "تم حفظ الحجز الأسبوعي بنجاح!")
                return redirect('my_buses')
        else:
            form = WeeklyBookingForm(instance=weekly_booking)
        
        context = {
            'form': form,
            'passenger': passenger_obj,
            'category': category,
            'weekly_booking': weekly_booking
        }
        
        return render(request, 'weekly_booking.html', context)
        
    except passenger.DoesNotExist:
        messages.error(request, "لم يتم العثور على بيانات الطالب")
        return redirect('my_buses')
    except Category.DoesNotExist:
        messages.error(request, "لم يتم العثور على الجامعة")
        return redirect('my_buses')


def get_weekly_schedules_api(request, category_id):
    """API لجلب الجداول الزمنية الأسبوعية والنقاط المتاحة مقسمة حسب المدينة"""
    try:
        category = Category.objects.get(id=category_id)
        schedules = WeeklySchedule.objects.filter(category=category, is_active=True)
        
        departure_schedules = []
        return_schedules = []
        
        for schedule in schedules:
            schedule_data = {
                'day': schedule.day_of_week,
                'day_arabic': schedule.get_day_of_week_display(),
                'time': schedule.time.strftime('%H:%M'),
                'trip_type': schedule.trip_type
            }
            
            if schedule.trip_type == 'departure':
                departure_schedules.append(schedule_data)
            else:
                return_schedules.append(schedule_data)
        
        # جلب النقاط من الرحلات الموجودة وتقسيمها حسب المدينة
        cities_data = {}
        
        trips = Trip.objects.filter(category=category, is_active=True)
        for trip in trips:
            if trip.route:
                # تقسيم الـ route إلى نقاط فردية
                points = [point.strip() for point in trip.route.split('\n') if point.strip()]
                for point in points:
                    # إزالة الوقت من بداية النقطة إذا وجد
                    clean_point = point
                    if ':' in point and point.count(':') == 1:
                        # قد يكون الوقت في البداية مثل "07:00 - نقطة ما"
                        parts = point.split('-', 1)
                        if len(parts) == 2:
                            clean_point = parts[1].strip()
                    
                    # استخراج اسم المدينة (أول كلمة أو بين قوسين)
                    city_name = extract_city_from_point(clean_point)
                    
                    if city_name not in cities_data:
                        cities_data[city_name] = {
                            'pickup_points': set(),
                            'dropoff_points': set()
                        }
                    
                    cities_data[city_name]['pickup_points'].add(clean_point)
                    cities_data[city_name]['dropoff_points'].add(clean_point)
            
            # إضافة نقاط البداية والنهاية إذا وجدت
            if trip.start_destination:
                city_name = extract_city_from_point(trip.start_destination.name)
                if city_name not in cities_data:
                    cities_data[city_name] = {
                        'pickup_points': set(),
                        'dropoff_points': set()
                    }
                cities_data[city_name]['pickup_points'].add(trip.start_destination.name)
            
            if trip.end_destination:
                city_name = extract_city_from_point(trip.end_destination.name)
                if city_name not in cities_data:
                    cities_data[city_name] = {
                        'pickup_points': set(),
                        'dropoff_points': set()
                    }
                cities_data[city_name]['dropoff_points'].add(trip.end_destination.name)
        
        # تحويل إلى قواميس مرتبة
        cities_list = []
        for city_name in sorted(cities_data.keys()):
            cities_list.append({
                'name': city_name,
                'pickup_points': sorted(list(cities_data[city_name]['pickup_points'])),
                'dropoff_points': sorted(list(cities_data[city_name]['dropoff_points']))
            })
        
        return JsonResponse({
            'departure_schedules': departure_schedules,
            'return_schedules': return_schedules,
            'cities': cities_list
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)


def extract_city_from_point(point_name):
    """استخراج اسم المدينة من اسم النقطة"""
    # البحث عن اسم المدينة بين قوسين
    import re
    match = re.search(r'\(([^)]+)\)', point_name)
    if match:
        return match.group(1).strip()
    
    # البحث عن كلمات مدن شائعة
    city_keywords = ['القاهرة', 'الجيزة', 'الإسكندرية', 'الأقصر', 'أسوان', 'المنصورة', 'السويس', 'دمياط', 'طنطا', 'الشرقية']
    for city in city_keywords:
        if city in point_name:
            return city
    
    # إذا لم يتم العثور على مدينة، استخدم أول كلمة
    words = point_name.split()
    if words:
        return words[0]
    
    return point_name


@login_required
def form_bookings_day_view(request, date_str=None):
    """صفحة عرض حجوزات الفورم اليومية (للأدمن)"""
    if not request.user.is_staff:
        return redirect('my_buses')
    
    # تحديد التاريخ
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = date.today()
    
    today = date.today()
    
    context = {
        'selected_date': selected_date,
        'today': today,
    }
    
    return render(request, 'admin/form_bookings_day.html', context)


@login_required
def get_form_bookings_api(request, date_str):
    """API لجلب حجوزات الفورم ليوم معين"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # جلب حجوزات الفورم في التاريخ المحدد
        bookings = FormReservation.objects.filter(trip_date=selected_date).select_related(
            'passenger', 'going_city', 'return_city', 'trip'
        ).order_by('-created_at')
        
        bookings_data = []
        total_count = bookings.count()
        confirmed_count = bookings.filter(status='confirmed').count()
        pending_count = bookings.filter(status='pending').count()
        total_revenue = sum(booking.total_price or 0 for booking in bookings)
        
        for booking in bookings:
            booking_data = {
                'id': booking.id,
                'student_name': booking.student_name,
                'passenger_name': booking.passenger.name if booking.passenger else None,
                'university_code': booking.university_code,
                'phone_number': booking.phone_number,
                'passenger_phone': booking.passenger.phone_number if booking.passenger else None,
                'trip_date': booking.trip_date.strftime('%Y-%m-%d'),
                'trip_type': booking.trip_type,
                'arrival_time': booking.arrival_time.strftime('%H:%M') if booking.arrival_time else None,
                'back_time': booking.back_time.strftime('%H:%M') if booking.back_time else None,
                'status': booking.status,
                'total_price': float(booking.total_price or 0),
                'paid_amount': float(booking.paid_amount or 0),
                'seat_number': booking.seat_number,
                'merchant_order_id': booking.merchant_order_id,
                'trip_id': booking.trip.id if booking.trip else None,
                'attendance_status': booking.attendance_status,
                
                # معلومات المدن والنقاط
                'going_city_name': booking.going_city.name if booking.going_city else None,
                'going_pickup_location': booking.going_pickup_location,
                'going_dropoff_location': booking.going_dropoff_location,
                'return_city_name': booking.return_city.name if booking.return_city else None,
                
                # معلومات الرحلة
                'trip_name': booking.trip.trip_name if booking.trip else None,
                'bus_name': booking.trip.bus.name if booking.trip and booking.trip.bus else None,
                
                # معلومات الجامعة
                'category_name': booking.category.name if booking.category else None,
                
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            bookings_data.append(booking_data)
        
        return JsonResponse({
            'bookings': bookings_data,
            'total_count': total_count,
            'confirmed_count': confirmed_count,
            'pending_count': pending_count,
            'total_revenue': f"{total_revenue:.2f}",
            'selected_date': date_str,
        })
        
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def weekly_booking_view_new(request, category_id):
    """صفحة الحجز الأسبوعي الجديدة (بنفس طريقة الفورم ريسرفيشن)"""
    category = get_object_or_404(Category, id=category_id)
    # التحقق من أن الفورم مدعوم للكاتيجوري
    if not category.Form_support:
        messages.error(request, "❌ الحجز الأسبوعي غير متاح حالياً لهذه الجامعة.")
        return redirect("index")

    if request.method == "POST":
        # التحقق إذا كان طلب Ajax
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            form = WeeklyBookingForm(request.POST)
            
            if form.is_valid():
                try:
                    trip_type = request.POST.get("trip_type")
                    if not trip_type:
                        return JsonResponse({
                            'success': False,
                            'message': 'يرجى اختيار نوع الرحلة'
                        })
                    
                    booking_data = {
                        'category_id': category.id,
                        'user_id': request.user.id,
                    }

                    if hasattr(request.user, "passenger"):
                        p = request.user.passenger
                        booking_data.update({
                            'passenger_id': p.id,
                        })

                    bookings = []

                    # دالة آمنة لتحليل JSON
                    def safe_json_loads(json_str, default=[]):
                        try:
                            if json_str:
                                return json.loads(json_str)
                            return default
                        except (json.JSONDecodeError, TypeError):
                            return default

                    if trip_type == "ذهاب":
                        bookings.append({
                            **booking_data,
                            'trip_type': "ذهاب",
                            'departure_days': safe_json_loads(request.POST.get("departure_days")),
                            'departure_time': request.POST.get("departure_time", ""),
                            'going_city_id': request.POST.get("going_city_id"),
                            'going_pickup_location': request.POST.get("going_pickup_location", ""),
                            'going_dropoff_location': request.POST.get("going_dropoff_location", ""),
                            'pickup_location': request.POST.get("going_pickup_location", ""),
                            'dropoff_location': request.POST.get("going_dropoff_location", ""),
                        })

                    elif trip_type == "عودة":
                        bookings.append({
                            **booking_data,
                            'trip_type': "عودة",
                            'return_days': safe_json_loads(request.POST.get("return_days")),
                            'return_time': request.POST.get("return_time", ""),
                            'return_city_id': request.POST.get("return_city_id"),
                            'return_pickup_location': request.POST.get("return_pickup_location", ""),
                            'return_dropoff_location': request.POST.get("return_dropoff_location", ""),
                            'pickup_location': request.POST.get("return_pickup_location", ""),
                            'dropoff_location': request.POST.get("return_dropoff_location", ""),
                        })

                    elif trip_type == "ذهاب وعودة":
                        bookings.append({
                            **booking_data,
                            'trip_type': "ذهاب",
                            'departure_days': safe_json_loads(request.POST.get("departure_days")),
                            'departure_time': request.POST.get("departure_time", ""),
                            'going_city_id': request.POST.get("going_city_id"),
                            'going_pickup_location': request.POST.get("going_pickup_location", ""),
                            'going_dropoff_location': request.POST.get("going_dropoff_location", ""),
                            'pickup_location': request.POST.get("going_pickup_location", ""),
                            'dropoff_location': request.POST.get("going_dropoff_location", ""),
                        })
                        bookings.append({
                            **booking_data,
                            'trip_type': "عودة",
                            'return_days': safe_json_loads(request.POST.get("return_days")),
                            'return_time': request.POST.get("return_time", ""),
                            'return_city_id': request.POST.get("return_city_id"),
                            'return_pickup_location': request.POST.get("return_pickup_location", ""),
                            'return_dropoff_location': request.POST.get("return_dropoff_location", ""),
                            'pickup_location': request.POST.get("return_pickup_location", ""),
                            'dropoff_location': request.POST.get("return_dropoff_location", ""),
                        })

                    # تحديد السعر
                    if trip_type == "ذهاب" or trip_type == "عودة":
                        base_price = category.one_way_price
                    elif trip_type == "ذهاب وعودة":
                        base_price = category.round_trip_price
                    else:
                        base_price = Decimal('0.00')
                    final_price = (base_price * Decimal('1.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                    # إنشاء أو تحديث الحجوزات
                    for book in bookings:
                        # التحقق من وجود حجز سابق
                        existing_booking = WeeklyBooking.objects.filter(
                            passenger_id=book.get("passenger_id"),
                            category_id=book["category_id"]
                        ).first()
                        
                        if existing_booking:
                            # تحديث الحجز الموجود
                            existing_booking.departure_days = book.get("departure_days", [])
                            existing_booking.return_days = book.get("return_days", [])
                            existing_booking.departure_time = book.get("departure_time")
                            existing_booking.return_time = book.get("return_time")
                            existing_booking.pickup_location = book.get("pickup_location")
                            existing_booking.dropoff_location = book.get("dropoff_location")
                            existing_booking.is_active = True
                            existing_booking.save()
                        else:
                            # إنشاء حجز جديد
                            WeeklyBooking.objects.create(
                                category=Category.objects.get(id=book["category_id"]),
                                passenger_id=book.get("passenger_id"),
                                departure_days=book.get("departure_days", []),
                                return_days=book.get("return_days", []),
                                departure_time=book.get("departure_time"),
                                return_time=book.get("return_time"),
                                pickup_location=book.get("pickup_location"),
                                dropoff_location=book.get("dropoff_location"),
                            )

                    return JsonResponse({
                        'success': True,
                        'message': '✅ تم حفظ الحجز الأسبوعي بنجاح!',
                        'redirect_url': reverse('my_buses')
                    })

                except Exception as e:
                    print(f"Error in weekly booking: {str(e)}")  # للتصحيح
                    import traceback
                    traceback.print_exc()  # طباعة الـ traceback الكامل
                    return JsonResponse({
                        'success': False,
                        'message': f"حدث خطأ أثناء الحجز: {str(e)}"
                    })
            else:
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                
                return JsonResponse({
                    'success': False,
                    'message': 'يرجى تصحيح الأخطاء التالية:',
                    'errors': errors
                })
        else:
            # طلب عادي (غير Ajax)
            form = WeeklyBookingForm(request.POST)

            if form.is_valid():
                try:
                    trip_type = request.POST.get("trip_type")
                    booking_data = {
                        'category_id': category.id,
                        'user_id': request.user.id,
                    }

                    if hasattr(request.user, "passenger"):
                        p = request.user.passenger
                        booking_data.update({
                            'passenger_id': p.id,
                        })

                    bookings = []

                    # دالة آمنة لتحليل JSON
                    def safe_json_loads(json_str, default=[]):
                        try:
                            if json_str:
                                return json.loads(json_str)
                            return default
                        except (json.JSONDecodeError, TypeError):
                            return default

                    if trip_type == "ذهاب":
                        bookings.append({
                            **booking_data,
                            'trip_type': "ذهاب",
                            'departure_days': safe_json_loads(request.POST.get("departure_days")),
                            'departure_time': request.POST.get("departure_time", ""),
                            'going_city_id': request.POST.get("going_city_id"),
                            'going_pickup_location': request.POST.get("going_pickup_location", ""),
                            'going_dropoff_location': request.POST.get("going_dropoff_location", ""),
                            'pickup_location': request.POST.get("going_pickup_location", ""),
                            'dropoff_location': request.POST.get("going_dropoff_location", ""),
                        })

                    elif trip_type == "عودة":
                        bookings.append({
                            **booking_data,
                            'trip_type': "عودة",
                            'return_days': safe_json_loads(request.POST.get("return_days")),
                            'return_time': request.POST.get("return_time", ""),
                            'return_city_id': request.POST.get("return_city_id"),
                            'return_pickup_location': request.POST.get("return_pickup_location", ""),
                            'return_dropoff_location': request.POST.get("return_dropoff_location", ""),
                            'pickup_location': request.POST.get("return_pickup_location", ""),
                            'dropoff_location': request.POST.get("return_dropoff_location", ""),
                        })

                    elif trip_type == "ذهاب وعودة":
                        bookings.append({
                            **booking_data,
                            'trip_type': "ذهاب",
                            'departure_days': safe_json_loads(request.POST.get("departure_days")),
                            'departure_time': request.POST.get("departure_time", ""),
                            'going_city_id': request.POST.get("going_city_id"),
                            'going_pickup_location': request.POST.get("going_pickup_location", ""),
                            'going_dropoff_location': request.POST.get("going_dropoff_location", ""),
                            'pickup_location': request.POST.get("going_pickup_location", ""),
                            'dropoff_location': request.POST.get("going_dropoff_location", ""),
                        })
                        bookings.append({
                            **booking_data,
                            'trip_type': "عودة",
                            'return_days': safe_json_loads(request.POST.get("return_days")),
                            'return_time': request.POST.get("return_time", ""),
                            'return_city_id': request.POST.get("return_city_id"),
                            'return_pickup_location': request.POST.get("return_pickup_location", ""),
                            'return_dropoff_location': request.POST.get("return_dropoff_location", ""),
                            'pickup_location': request.POST.get("return_pickup_location", ""),
                            'dropoff_location': request.POST.get("return_dropoff_location", ""),
                        })

                    # تحديد السعر
                    if trip_type == "ذهاب" or trip_type == "عودة":
                        base_price = category.one_way_price
                    elif trip_type == "ذهاب وعودة":
                        base_price = category.round_trip_price
                    else:
                        base_price = Decimal('0.00')
                    final_price = (base_price * Decimal('1.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

                    # إنشاء أو تحديث الحجوزات
                    for book in bookings:
                        # التحقق من وجود حجز سابق
                        existing_booking = WeeklyBooking.objects.filter(
                            passenger_id=book.get("passenger_id"),
                            category_id=book["category_id"]
                        ).first()
                        
                        if existing_booking:
                            # تحديث الحجز الموجود
                            existing_booking.departure_days = book.get("departure_days", [])
                            existing_booking.return_days = book.get("return_days", [])
                            existing_booking.departure_time = book.get("departure_time")
                            existing_booking.return_time = book.get("return_time")
                            existing_booking.pickup_location = book.get("pickup_location")
                            existing_booking.dropoff_location = book.get("dropoff_location")
                            existing_booking.is_active = True
                            existing_booking.save()
                        else:
                            # إنشاء حجز جديد
                            WeeklyBooking.objects.create(
                                category=Category.objects.get(id=book["category_id"]),
                                passenger_id=book.get("passenger_id"),
                                departure_days=book.get("departure_days", []),
                                return_days=book.get("return_days", []),
                                departure_time=book.get("departure_time"),
                                return_time=book.get("return_time"),
                                pickup_location=book.get("pickup_location"),
                                dropoff_location=book.get("dropoff_location"),
                            )

                    messages.success(request, "✅ تم حفظ الحجز الأسبوعي بنجاح!")
                    return redirect("my_buses")

                except Exception as e:
                    messages.error(request, f"حدث خطأ أثناء الحجز: {str(e)}")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = WeeklyBookingForm()

    return render(request, "weekly_booking_new.html", {
        "form": form,
        "category": category,
        "category_id": category.id,
        "passenger": getattr(request.user, 'passenger', None),
        "cities": City.objects.filter(is_active=True, category=category).distinct()
    })


@login_required
def get_pickup_locations_api(request, city_id):
    """API لجلب نقاط الركوب والنزول حسب المدينة"""
    try:
        city = City.objects.get(id=city_id)
        
        # جلب الرحلات الخاصة بالمدينة فقط (تحسين الأداء)
        trips = Trip.objects.filter(
            Q(start_destination_id=city.id) | Q(end_destination_id=city.id)
        ).distinct()
        
        # إذا لم تكن هناك رحلات للمدينة، جلب رحلات من نفس الـ category
        if not trips.exists() and hasattr(city, 'category'):
            trips = Trip.objects.filter(
                category=city.category
            ).distinct()
        
        # إذا لم تكن هناك رحلات أيضاً، جلب أول 100 رحلة فقط
        if not trips.exists():
            trips = Trip.objects.all()[:100]
        
        # استخراج النقاط
        all_locations = set()
        
        # استخراج النقاط من حقل route
        for trip in trips:
            if trip.route:
                lines = trip.route.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 2:  # تجاهل الأسطر الفارغة أو القصيرة جداً
                        # إزالة الأوقات من النقاط (مثل 10:40)
                        if ':' not in line or not any(char.isdigit() for char in line[:5]):
                            all_locations.add(line)
        
        # إضافة نقاط من الوجهات إذا كانت موجودة
        for trip in trips:
            if trip.start_destination:
                all_locations.add(trip.start_destination.name)
            if trip.end_destination:
                all_locations.add(trip.end_destination.name)
        
        # فلترة النقاط لإزالة الأوقات والبيانات غير الصالحة
        filtered_locations = set()
        for location in all_locations:
            cleaned = location.strip()
            
            # إزالة الأوقات من أي مكان في النص
            cleaned = re.sub(r'\s*\d{1,2}:\d{2}\s*(?:ص|م)?\s*$', '', cleaned)  # وقت في النهاية
            cleaned = re.sub(r'^\d{1,2}:\d{2}\s*(?:ص|م)?\s*', '', cleaned)  # وقت في البداية
            cleaned = re.sub(r'\s*\d{1,2}:\d{2}\s*(?:ص|م)?\s*', ' ', cleaned)  # وقت في المنتصف
            
            # إزالة الأوقات فقط بدون ص/م
            cleaned = re.sub(r'\s*\d{1,2}:\d{2}\s*$', '', cleaned)
            cleaned = re.sub(r'^\d{1,2}:\d{2}\s*', '', cleaned)
            cleaned = re.sub(r'\s*\d{1,2}:\d{2}\s*', ' ', cleaned)
            
            # تنظيف الفراغات الزائدة
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # التحقق من أن النقاط صالحة
            if cleaned and len(cleaned) > 2 and not re.match(r'^\d{1,2}:\d{2}$', cleaned):
                filtered_locations.add(cleaned)
        
        # إذا لم يتم العثور على نقاط، أضف نقاط افتراضية
        if not filtered_locations:
            # نقاط افتراضية شائعة
            default_locations = [
                'المطار',
                'ميدان الساعة',
                'المحطة المركزية',
                'جامعة القاهرة',
                'جامعة عين شمس',
                'مصر الجديدة',
                'الهرم',
                'الأهرامات',
                'نادي الصيد',
                'مول العرب',
                city.name  # إضافة اسم المدينة نفسه
            ]
            filtered_locations.update(default_locations)
        
        # تحويل القائمة إلى قائمة مرتبة (تحديد أول 50 نقطة فقط لتحسين الأداء)
        locations_list = sorted(list(filtered_locations))[:50]
        
        return JsonResponse({
            'locations': locations_list,
            'pickup_locations': locations_list,
            'dropoff_locations': locations_list,
            'city_name': city.name,
            'trips_count': trips.count()
        })
        
    except City.DoesNotExist:
        return JsonResponse({'error': 'المدينة غير موجودة'}, status=404)
    except Exception as e:
        print(f"Error in get_pickup_locations_api: {str(e)}")  # للتصحيح
        import traceback
        traceback.print_exc()  # طباعة الـ traceback الكامل
        return JsonResponse({'error': f'حدث خطأ: {str(e)}'}, status=500)


@login_required
def weekly_bookings_day_view(request, date_str=None):
    """صفحة عرض الحجوزات الأسبوعية ليوم معين (للأدمن)"""
    if not request.user.is_staff:
        return redirect('my_buses')
    
    # تحديد التاريخ
    if date_str:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        selected_date = date.today()
    
    # تحديد اسم اليوم
    day_name = selected_date.strftime('%A').lower()
    day_mapping = {
        'saturday': 'saturday',
        'sunday': 'sunday', 
        'monday': 'monday',
        'tuesday': 'tuesday',
        'wednesday': 'wednesday',
        'thursday': 'thursday',
        'friday': 'friday'
    }
    day_name_arabic = day_mapping.get(day_name, day_name)
    
    # جلب الحجوزات لهذا اليوم
    all_bookings = WeeklyBooking.objects.filter(is_active=True)
    bookings_by_category = {}
    total_bookings = 0
    departure_bookings = 0
    return_bookings = 0
    
    for booking in all_bookings:
        # التحقق إذا كان الحجز يشمل هذا اليوم
        has_departure = day_name_arabic in booking.departure_days
        has_return = day_name_arabic in booking.return_days
        
        if has_departure or has_return:
            category = booking.category
            if category not in bookings_by_category:
                bookings_by_category[category] = []
            
            bookings_by_category[category].append(booking)
            total_bookings += 1
            
            if has_departure:
                departure_bookings += 1
            if has_return:
                return_bookings += 1
    
    context = {
        'selected_date': selected_date,
        'bookings_by_category': bookings_by_category,
        'total_bookings': total_bookings,
        'departure_bookings': departure_bookings,
        'return_bookings': return_bookings,
        'categories_count': len(bookings_by_category),
        'day_name': day_name_arabic
    }
    
    return render(request, 'admin/weekly_bookings_day.html', context)


def send_whatsapp_weekly_notifications(request, date_str):
    """Send WhatsApp notifications for weekly bookings"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_name = selected_date.strftime('%A').lower()
        day_mapping = {
            'saturday': 'saturday',
            'sunday': 'sunday', 
            'monday': 'monday',
            'tuesday': 'tuesday',
            'wednesday': 'wednesday',
            'thursday': 'thursday',
            'friday': 'friday'
        }
        day_name_arabic = day_mapping.get(day_name, day_name)
        
        # Get bookings for this day
        bookings = WeeklyBooking.objects.filter(is_active=True)
        sent_count = 0
        
        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
        
        for booking in bookings:
            has_departure = day_name_arabic in booking.departure_days
            has_return = day_name_arabic in booking.return_days
            
            if has_departure or has_return:
                # Create custom message
                message_parts = [f"Bus confirmation for {selected_date.strftime('%Y-%m-%d')}"]
                
                if has_departure:
                    message_parts.append(f"Departure: {booking.departure_time or 'Not specified'}")
                    message_parts.append(f"Pickup: {booking.pickup_location or 'Not specified'}")
                
                if has_return:
                    message_parts.append(f"Return: {booking.return_time or 'Not specified'}")
                    message_parts.append(f"Dropoff: {booking.dropoff_location or 'Not specified'}")
                
                message_parts.append(f"University: {booking.category.name}")
                message = "\n".join(message_parts)
                
                # Send message
                if booking.passenger.phone_number:
                    payload = {
                        "token": API_TOKEN,
                        "to": booking.passenger.phone_number,
                        "body": message
                    }
                    requests.post(URL, data=payload)
                    sent_count += 1
        
        return JsonResponse({
            'success': True,
            'sent_count': sent_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


