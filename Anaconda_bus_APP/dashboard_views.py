# Anaconda_bus_APP/dashboard_views.py
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from weasyprint import HTML
import requests
import tempfile
import os

from .models import (
    Trip, Booking, FormReservation, passenger, 
    Category, Bus, Seat, Report
)

# دالة للتحقق من صلاحيات الأدمن
def is_admin(user):
    return user.is_staff or user.is_superuser

# الصفحة الرئيسية للداشبورد
@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    today = timezone.now().date()
    
    # إحصائيات عامة
    total_trips = Trip.objects.filter(is_old=False).count()
    active_trips = Trip.objects.filter(is_active=True, is_old=False).count()
    today_trips = Trip.objects.filter(date=today, is_active=True).count()
    total_passengers = passenger.objects.count()
    
    # الرحلات القادمة
    upcoming_trips = Trip.objects.filter(
        date__gte=today,
        is_active=True,
        is_old=False
    ).order_by('date', 'start_time')[:10]
    
    # إحصائيات الحجوزات
    total_bookings = Booking.objects.filter(status='active').count()
    total_form_reservations = FormReservation.objects.filter(status='confirmed').count()
    
    # الفئات والجامعات
    categories = Category.objects.annotate(
            trips_count=Count('buses__trip', filter=Q(buses__trip__is_active=True))
    )
    
    
    context = {
         'total_trips': total_trips,
        'active_trips': active_trips,
        'today_trips': today_trips,
        'total_passengers': total_passengers,
        'upcoming_trips': upcoming_trips,
        'total_bookings': total_bookings + total_form_reservations,
        'categories': categories,
    }
    
    return render(request, 'dashboard/home.html', context)

# قائمة الرحلات
@login_required
@user_passes_test(is_admin)
def trips_list(request):
    # الفلاتر
    category_id = request.GET.get('category')
    date_filter = request.GET.get('date')
    is_active = request.GET.get('is_active')
    trip_type = request.GET.get('trip_type')
    
    trips = Trip.objects.filter(is_old=False).select_related('bus', 'category')
    
    if category_id:
        trips = trips.filter(category_id=category_id)
    if date_filter:
        trips = trips.filter(date=date_filter)
    if is_active:
        trips = trips.filter(is_active=is_active == 'true')
    if trip_type:
        trips = trips.filter(trip_type=trip_type)
    
    trips = trips.order_by('-date', 'start_time')
    
    # إحصائيات لكل رحلة
    trips_data = []
    for trip in trips:
        bookings_count = Booking.objects.filter(Trip=trip, status='active').count()
        form_reservations_count = FormReservation.objects.filter(trip=trip, status='confirmed').count()
        total_reservations = bookings_count + form_reservations_count
        
        capacity = trip.bus.capacity if trip.bus else 0
        available_seats = capacity - total_reservations
        occupancy_rate = (total_reservations / capacity * 100) if capacity > 0 else 0
        
        trips_data.append({
            'trip': trip,
            'total_reservations': total_reservations,
            'available_seats': available_seats,
            'occupancy_rate': round(occupancy_rate, 2),
        })
    
    categories = Category.objects.all()
    
    context = {
        'trips_data': trips_data,
        'categories': categories,
        'current_filters': {
            'category': category_id,
            'date': date_filter,
            'is_active': is_active,
            'trip_type': trip_type,
        }
    }
    
    return render(request, 'dashboard/trips_list.html', context)

# تفاصيل الرحلة
@login_required
@user_passes_test(is_admin)
def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    # الحجوزات
    form_reservations = FormReservation.objects.filter(trip=trip).select_related('passenger', 'seat')
    bookings = Booking.objects.filter(Trip=trip).select_related('passenger')
    
    # إحصائيات المحطات
    route_stations = [s.strip() for s in trip.route.split('\n') if s.strip()]
    station_stats = []
    
    for station in route_stations:
        count = Booking.objects.filter(
            Trip=trip, 
            selected_route__iexact=station
        ).count()
        station_stats.append({
            'name': station,
            'count': count
        })
    
    # معلومات الباص
    if trip.bus:
        total_capacity = trip.bus.capacity or 0
        total_reservations = form_reservations.count() + bookings.count()
        available_seats = total_capacity - total_reservations
        occupancy_rate = (total_reservations / total_capacity * 100) if total_capacity > 0 else 0
    else:
        total_capacity = 0
        total_reservations = 0
        available_seats = 0
        occupancy_rate = 0
    
    context = {
        'trip': trip,
        'form_reservations': form_reservations,
        'bookings': bookings,
        'station_stats': station_stats,
        'total_capacity': total_capacity,
        'total_reservations': total_reservations,
        'available_seats': available_seats,
        'occupancy_rate': round(occupancy_rate, 2),
    }
    
    return render(request, 'dashboard/trip_detail.html', context)

# الحجوزات الخاصة برحلة
@login_required
@user_passes_test(is_admin)
def trip_bookings(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    form_reservations = FormReservation.objects.filter(trip=trip).select_related('passenger', 'seat')
    bookings = Booking.objects.filter(Trip=trip).select_related('passenger')
    
    context = {
        'trip': trip,
        'form_reservations': form_reservations,
        'bookings': bookings,
    }
    
    return render(request, 'dashboard/trip_bookings.html', context)

# توليد PDF للرحلة
@login_required
@user_passes_test(is_admin)
def generate_trip_pdf(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    form_reservations = FormReservation.objects.filter(trip=trip).order_by('created_at')
    bookings = Booking.objects.filter(Trip=trip).order_by('booking_date')
    
    html_string = render_to_string("dashboard/trip_report_pdf.html", {
        "trip": trip,
        "form_reservations": form_reservations,
        "bookings": bookings,
        "now": timezone.now()
    })
    
    pdf_content = HTML(string=html_string).write_pdf()
    
    # إرسال واتساب للسائق
    send_to_whatsapp = request.GET.get('send_whatsapp') == 'true'
    if send_to_whatsapp and trip.bus and trip.bus.driver_number:
        try:
            driver_number = trip.bus.driver_number.replace(" ", "").replace("+", "").replace("-", "")
            if not driver_number.startswith("2"):
                driver_number = "2" + driver_number
            
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
            
            os.unlink(tmp_file.name)
            
            if response.status_code == 200:
                messages.success(request, f"✅ تم إرسال التقرير على واتساب للسائق")
        except Exception as e:
            messages.error(request, f"⚠️ حدث خطأ أثناء الإرسال: {e}")
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="trip_{trip.id}_{trip.trip_name}.pdf"'
    return response

# تجديد الرحلات
@login_required
@user_passes_test(is_admin)
def renew_trips(request):
    if request.method == 'POST':
        trip_ids = request.POST.getlist('trip_ids')
        days_to_add = int(request.POST.get('days_to_add', 1))
        
        renewed_count = 0
        for trip_id in trip_ids:
            try:
                trip = Trip.objects.get(id=trip_id)
                
                # تفريغ الحجوزات
                trip.bookings.filter(status="active").update(status="inactive")
                form_reservations = FormReservation.objects.filter(trip=trip)
                for form_res in form_reservations:
                    form_res.trip = None
                    form_res.seat = None
                    form_res.status = 'pending'
                    form_res.save()
                
                # تحرير المقاعد
                if trip.bus:
                    Seat.objects.filter(bus=trip.bus).update(is_reserved=False)
                
                # تحديث الرحلة القديمة
                trip.is_active = False
                trip.is_old = True
                trip.save()
                
                # إنشاء رحلة جديدة
                trip_data = {
                    field.name: getattr(trip, field.name)
                    for field in Trip._meta.fields
                    if field.name not in ['id', 'bus', 'category', 'date', 'is_active', 'is_old']
                }
                
                trip_data['date'] = trip.date + timedelta(days=days_to_add)
                trip_data['is_active'] = True
                trip_data['is_old'] = False
                trip_data['bus'] = None
                trip_data['category'] = None
                
                Trip.objects.create(**trip_data)
                renewed_count += 1
                
            except Trip.DoesNotExist:
                continue
        
        messages.success(request, f"✅ تم تجديد {renewed_count} رحلة بنجاح")
        return redirect('dashboard:trips_list')
    
    return redirect('dashboard:trips_list')

# تفعيل/تعطيل الرحلة
@login_required
@user_passes_test(is_admin)
def toggle_trip_active(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    trip.is_active = not trip.is_active
    trip.save()
    
    status = "تفعيل" if trip.is_active else "تعطيل"
    messages.success(request, f"✅ تم {status} الرحلة {trip.trip_name}")
    
    return redirect('dashboard:trip_detail', trip_id=trip_id)

# قائمة الركاب
@login_required
@user_passes_test(is_admin)
def passengers_list(request):
    # الفلاتر
    category_id = request.GET.get('category')
    user_type = request.GET.get('user_type')
    search = request.GET.get('search')
    
    passengers = passenger.objects.all()
    
    if category_id:
        passengers = passengers.filter(category_id=category_id)
    if user_type:
        passengers = passengers.filter(user_type=user_type)
    if search:
        passengers = passengers.filter(
            Q(name__icontains=search) |
            Q(university_code__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    passengers = passengers.order_by('name')
    
    categories = Category.objects.all()
    
    context = {
        'passengers': passengers,
        'categories': categories,
        'current_filters': {
            'category': category_id,
            'user_type': user_type,
            'search': search,
        }
    }
    
    return render(request, 'dashboard/passengers_list.html', context)

# تفاصيل الراكب
@login_required
@user_passes_test(is_admin)
def passenger_detail(request, passenger_id):
    pass_obj = get_object_or_404(passenger, id=passenger_id)
    
    # حجوزات الراكب
    bookings = Booking.objects.filter(passenger=pass_obj).select_related('Trip')
    form_reservations = FormReservation.objects.filter(passenger=pass_obj).select_related('trip')
    
    context = {
        'passenger': pass_obj,
        'bookings': bookings,
        'form_reservations': form_reservations,
    }
    
    return render(request, 'dashboard/passenger_detail.html', context)

# إرسال رسائل واتساب جماعية
@login_required
@user_passes_test(is_admin)
def send_whatsapp_bulk(request):
    if request.method == 'POST':
        passenger_ids = request.POST.getlist('passenger_ids')
        message = request.POST.get('message')
        
        if not passenger_ids or not message:
            messages.error(request, "⚠️ يرجى تحديد ركاب وكتابة رسالة")
            return redirect('dashboard:passengers_list')
        
        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        API_URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
        
        success_count = 0
        fail_count = 0
        
        for passenger_id in passenger_ids:
            try:
                pass_obj = passenger.objects.get(id=passenger_id)
                phone = pass_obj.phone_number
                
                if not phone:
                    fail_count += 1
                    continue
                
                phone = phone.strip()
                if not phone.startswith("+20"):
                    phone = "+20" + phone.lstrip("0")
                
                payload = {
                    "token": API_TOKEN,
                    "to": phone,
                    "body": message,
                }
                
                response = requests.post(API_URL, data=payload, timeout=15)
                
                if response.status_code == 200:
                    success_count += 1
                else:
                    fail_count += 1
                    
            except Exception as e:
                fail_count += 1
        
        msg = f"✅ تم إرسال الرسالة إلى {success_count} راكب بنجاح"
        if fail_count > 0:
            msg += f" ❌ فشل الإرسال إلى {fail_count}"
        
        messages.success(request, msg)
        return redirect('dashboard:passengers_list')
    
    return redirect('dashboard:passengers_list')

# صفحة التقارير
@login_required
@user_passes_test(is_admin)
def reports_home(request):
    categories = Category.objects.all()
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'dashboard/reports_home.html', context)

# تقرير الفئة
@login_required
@user_passes_test(is_admin)
def category_report(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    target_date = timezone.datetime.fromisoformat(date_filter).date()
    
    trips = Trip.objects.filter(
        is_active=True,
        bus__category=category,
        date=target_date
    )
    
    trips_data = []
    for trip in trips:
        bus = trip.bus
        total_capacity = bus.capacity or 0
        total_reservations = Booking.objects.filter(Trip=trip).count()
        remaining_seats = total_capacity - total_reservations
        occupancy_rate = (total_reservations / total_capacity * 100) if total_capacity > 0 else 0
        
        route_stations = [station.strip() for station in trip.route.split("\n") if station.strip()]
        station_reservations = []
        for station in route_stations:
            count = Booking.objects.filter(Trip=trip, selected_route__iexact=station).count()
            station_reservations.append({
                'station': station,
                'count': count
            })
        
        trips_data.append({
            'trip': trip,
            'total_capacity': total_capacity,
            'total_reservations': total_reservations,
            'remaining_seats': remaining_seats,
            'occupancy_rate': round(occupancy_rate, 2),
            'station_reservations': station_reservations,
        })
    
    context = {
        'category': category,
        'target_date': target_date,
        'trips_data': trips_data,
    }
    
    return render(request, 'dashboard/category_report.html', context)

# إرسال تقرير عبر واتساب
@login_required
@user_passes_test(is_admin)
def send_trip_report_view(request):
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        report_type = request.POST.get('report_type', 'today')
        
        category = get_object_or_404(Category, id=category_id)
        
        if not category.admin_phone_number:
            messages.warning(request, f"⚠️ لا يوجد رقم هاتف مسجل لـ {category.name}")
            return redirect('dashboard:reports_home')
        
        # حساب التاريخ المطلوب
        if report_type == 'today':
            target_date = timezone.now().date()
            title = "تقرير رحلات اليوم"
        elif report_type == 'tomorrow':
            target_date = timezone.now().date() + timedelta(days=1)
            title = "تقرير رحلات الغد"
        elif report_type == 'after_tomorrow':
            target_date = timezone.now().date() + timedelta(days=2)
            title = "تقرير رحلات بعد الغد"
        else:
            target_date = timezone.now().date()
            title = "تقرير الرحلات"
        
        # جلب الرحلات
        trips = Trip.objects.filter(
            is_active=True,
            bus__category=category,
            date=target_date
        )
        
        report_data = []
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
        
        report_message = f"{title} ({target_date})\n\n"
        report_message += "=== الرحلات الحالية ===\n"
        report_message += "\n---------------------\n".join(report_data) if report_data else "لا توجد رحلات حالية.\n"
        
        # إرسال الرسالة
        INSTANCE_ID = "instance105329"
        API_TOKEN = settings.ULTRAMSG_API_TOKEN
        URL = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
        
        max_length = 4096
        messages_parts = [report_message[i:i+max_length] for i in range(0, len(report_message), max_length)]
        
        for part in messages_parts:
            payload = {"token": API_TOKEN, "to": category.admin_phone_number, "body": part}
            response = requests.post(URL, data=payload)
            
            if response.status_code != 200:
                messages.error(request, f"❌ حدث خطأ أثناء إرسال التقرير")
                return redirect('dashboard:reports_home')
        
        messages.success(request, f"✅ تم إرسال التقرير إلى {category.name} بنجاح")
        return redirect('dashboard:reports_home')
    
    return redirect('dashboard:reports_home')

# قائمة الفئات
@login_required
@user_passes_test(is_admin)
def categories_list(request):
    categories = Category.objects.annotate(
        buses_count=Count('bus'),
        trips_count=Count('bus__trip', filter=Q(bus__trip__is_active=True))
    )
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'dashboard/categories_list.html', context)

# قائمة الحافلات
@login_required
@user_passes_test(is_admin)
def buses_list(request):
    category_id = request.GET.get('category')
    
    buses = Bus.objects.select_related('category')
    
    if category_id:
        buses = buses.filter(category_id=category_id)
    
    categories = Category.objects.all()
    
    context = {
        'buses': buses,
        'categories': categories,
        'current_category': category_id,
    }
    
    return render(request, 'dashboard/buses_list.html', context)

# AJAX: تحميل الحافلات حسب الفئة
@login_required
@user_passes_test(is_admin)
def load_buses_ajax(request):
    category_id = request.GET.get('category_id')
    buses = Bus.objects.filter(category_id=category_id).values('id', 'name')
    return JsonResponse(list(buses), safe=False)

# AJAX: إحصائيات الرحلة
@login_required
@user_passes_test(is_admin)
def get_trip_stats(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    
    bookings_count = Booking.objects.filter(Trip=trip, status='active').count()
    form_reservations_count = FormReservation.objects.filter(trip=trip, status='confirmed').count()
    total_reservations = bookings_count + form_reservations_count
    
    capacity = trip.bus.capacity if trip.bus else 0
    available_seats = capacity - total_reservations
    occupancy_rate = (total_reservations / capacity * 100) if capacity > 0 else 0
    
    data = {
        'total_reservations': total_reservations,
        'available_seats': available_seats,
        'occupancy_rate': round(occupancy_rate, 2),
        'capacity': capacity,
    }
    
    return JsonResponse(data)
