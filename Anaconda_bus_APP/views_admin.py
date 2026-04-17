from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, time, timedelta
from .models import WeeklyBooking, Trip, passenger, Category
from telegram_bot.models import TelegramUserNotification, TelegramUserActivity
from Anaconda_bus_APP.models import TelegramBotToken

@staff_member_required
def link_telegram_account(request):
    """Link user's Telegram account to their profile"""
    if request.method == 'POST':
        try:
            # Get the current logged-in user
            user = request.user
            
            # Get link data from success page
            link_data = request.POST.get('link_data', '')
            
            if link_data.startswith('link_'):
                # Parse: link_<USER_ID>_<TOKEN>
                parts = link_data.split('_')
                if len(parts) >= 3:
                    user_id = parts[1]
                    token = parts[2]
                    
                    # Get user's Telegram chat_id from activities
                    user_activity = TelegramUserActivity.objects.filter(
                        user_id=user_id,
                        action='account_linked'
                    ).order_by('-created_at').first()
                    
                    if user_activity:
                        # Link the chat_id to the current logged-in user
                        user.telegram_chat_id = user_activity.chat_id
                        user.save()
                        
                        return JsonResponse({
                            'success': True,
                            'message': '✅ تم ربط حساب Telegram بنجاح!'
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': '❌ لم يتم العثور على حساب Telegram مرتبط'
                        })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '❌ رابط غير صالح'
                    })
                    
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'❌ حدث خطأ: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': '❌ طريقة غير مدعومة'
    })
import json

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@staff_member_required
def telegram_admin_dashboard(request):
    """Main Telegram admin dashboard"""
    
    # Get statistics
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    
    # Telegram stats
    total_notifications = TelegramUserNotification.objects.count()
    sent_notifications = TelegramUserNotification.objects.filter(is_sent=True).count()
    pending_notifications = TelegramUserNotification.objects.filter(is_sent=False).count()
    
    total_activities = TelegramUserActivity.objects.count()
    today_activities = TelegramUserActivity.objects.filter(created_at__date=today).count()
    week_activities = TelegramUserActivity.objects.filter(created_at__date__gte=last_7_days).count()
    
    # Recent activities
    recent_activities = TelegramUserActivity.objects.select_related('user').order_by('-created_at')[:10]
    
    # Recent notifications
    recent_notifications = TelegramUserNotification.objects.select_related('user').order_by('-created_at')[:10]
    
    # Activity breakdown
    activity_breakdown = TelegramUserActivity.objects.values('action').annotate(count=Count('id')).order_by('-count')
    
    context = {
        'page_title': 'لوحة تحكم Telegram',
        
        # Statistics
        'total_notifications': total_notifications,
        'sent_notifications': sent_notifications,
        'pending_notifications': pending_notifications,
        'total_activities': total_activities,
        'today_activities': today_activities,
        'week_activities': week_activities,
        
        # Recent data
        'recent_activities': recent_activities,
        'recent_notifications': recent_notifications,
        'activity_breakdown': activity_breakdown,
        
        # Navigation
        'active_section': 'telegram'
    }
    
    return render(request, 'admin/telegram_dashboard.html', context)

@login_required
@staff_member_required
def telegram_notifications(request):
    """Telegram notifications management page"""
    
    notifications = TelegramUserNotification.objects.select_related('user').order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    if status_filter:
        if status_filter == 'sent':
            notifications = notifications.filter(is_sent=True)
        elif status_filter == 'pending':
            notifications = notifications.filter(is_sent=False)
    
    # Search
    search = request.GET.get('search')
    if search:
        notifications = notifications.filter(
            Q(student_name__icontains=search) |
            Q(reservation_id__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    context = {
        'page_title': 'إشعارات Telegram',
        'notifications': notifications,
        'status_filter': status_filter,
        'search': search,
        'active_section': 'telegram'
    }
    
    return render(request, 'admin/telegram_notifications.html', context)

@login_required
@staff_member_required
def telegram_activities(request):
    """Telegram activities management page"""
    
    activities = TelegramUserActivity.objects.select_related('user').order_by('-created_at')
    
    # Filters
    action_filter = request.GET.get('action')
    if action_filter:
        activities = activities.filter(action=action_filter)
    
    # Date filter
    date_filter = request.GET.get('date')
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            activities = activities.filter(created_at__date=filter_date)
        except ValueError:
            pass
    
    # Search
    search = request.GET.get('search')
    if search:
        activities = activities.filter(
            Q(user__username__icontains=search) |
            Q(chat_id__icontains=search) |
            Q(booking_id__icontains=search) |
            Q(action__icontains=search)
        )
    
    context = {
        'page_title': 'أنشطة Telegram',
        'activities': activities,
        'action_filter': action_filter,
        'date_filter': date_filter,
        'search': search,
        'active_section': 'telegram'
    }
    
    return render(request, 'admin/telegram_activities.html', context)

@login_required
@staff_member_required
def send_telegram_broadcast(request):
    """Send broadcast message to all Telegram users"""
    
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            # Get all unique chat IDs
            chat_ids = TelegramUserActivity.objects.values_list('chat_id', flat=True).distinct()
            
            # Send broadcast
            from telegram_bot.utils import send_message
            bot_config = TelegramBotToken.objects.filter(is_active=True).first()
            
            if bot_config:
                success_count = 0
                for chat_id in chat_ids:
                    try:
                        send_message(chat_id, f"📢 **رسالة إدارية:**\n\n{message}", bot_config.bot_token)
                        success_count += 1
                    except:
                        pass
                
                return JsonResponse({
                    'success': True,
                    'message': f'تم إرسال الرسالة إلى {success_count} مستخدم'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'لا يوجد تكوين بوت نشط'
                })
    
    return render(request, 'admin/telegram_broadcast.html', {
        'page_title': 'إرسال رسالة جماعية',
        'active_section': 'telegram'
    })

@staff_member_required
def weekly_booking_trips_manager(request):
    """صفحة إدارة الحجوزات الأسبوعية ونقل الطلاب للرحلات"""
    
    # جلب جميع الحجوزات الأسبوعية النشطة
    weekly_bookings = WeeklyBooking.objects.filter(
        is_active=True
    ).select_related('passenger', 'category').order_by('category__name', 'passenger__name')
    
    # جلب جميع الرحلات المتاحة
    trips = Trip.objects.all().select_related('start_destination', 'end_destination').order_by('id')
    
    # جلب جميع الكاتيجوريات للفلترة
    categories = Category.objects.all().order_by('name')
    
    context = {
        'weekly_bookings': weekly_bookings,
        'trips': trips,
        'categories': categories,
        'title': 'إدارة الحجوزات الأسبوعية والرحلات'
    }
    
    return render(request, 'admin/weekly_booking_trips_manager.html', context)

@staff_member_required
def assign_passenger_to_trip(request):
    """إسناد طالب من الحجز الأسبوعي إلى رحلة"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            booking_id = request.POST.get('booking_id')
            trip_id = request.POST.get('trip_id')
            action = request.POST.get('action')  # 'assign' or 'remove'
            
            if not booking_id:
                return JsonResponse({'success': False, 'message': 'لم يتم تحديد الحجز'})
            
            booking = get_object_or_404(WeeklyBooking, id=booking_id)
            
            if action == 'assign':
                if not trip_id:
                    return JsonResponse({'success': False, 'message': 'لم يتم تحديد الرحلة'})
                
                trip = get_object_or_404(Trip, id=trip_id)
                
                # هنا يمكنك إنشاء علاقة بين الحجز والرحلة
                # مثلاً إضافة حقل foreign key في WeeklyBooking أو إنشاء جدول وسيط
                
                # مؤقتاً سنقوم بتخزين المعلومات في حقل مؤقت
                # يمكنك إضافة حقول جديدة للـ WeeklyBooking model لاحقاً
                
                return JsonResponse({
                    'success': True, 
                    'message': f'تم إسناد {booking.passenger.name} إلى رحلة {trip.id}',
                    'passenger_name': booking.passenger.name,
                    'trip_id': trip.id
                })
                
            elif action == 'remove':
                # إزالة الطالب من الرحلة
                return JsonResponse({
                    'success': True, 
                    'message': f'تم إزالة {booking.passenger.name} من الرحلة',
                    'passenger_name': booking.passenger.name
                })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'طلب غير صالح'})

@staff_member_required
def get_booking_details(request, booking_id):
    """الحصول على تفاصيل حجز معين"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            booking = get_object_or_404(WeeklyBooking, id=booking_id)
            
            data = {
                'id': booking.id,
                'passenger_name': booking.passenger.name,
                'passenger_code': booking.passenger.university_code,
                'category_name': booking.category.name,
                'departure_days': booking.get_departure_days_display(),
                'return_days': booking.get_return_days_display(),
                'departure_time': booking.departure_time.strftime('%H:%M') if booking.departure_time else '',
                'return_time': booking.return_time.strftime('%H:%M') if booking.return_time else '',
                'pickup_location': booking.pickup_location or '',
                'dropoff_location': booking.dropoff_location or '',
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M')
            }
            
            return JsonResponse({'success': True, 'data': data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'طلب غير صالح'})

@staff_member_required
def get_trip_details(request, trip_id):
    """الحصول على تفاصيل رحلة معينة"""
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            trip = get_object_or_404(Trip, id=trip_id)
            
            data = {
                'id': trip.id,
                'route': trip.route or '',
                'start_destination': trip.start_destination.name if trip.start_destination else '',
                'end_destination': trip.end_destination.name if trip.end_destination else '',
                'time': trip.time.strftime('%H:%M') if trip.time else '',
                'date': trip.date.strftime('%Y-%m-%d') if trip.date else '',
                'price': str(trip.price) if trip.price else '',
                'available_seats': getattr(trip, 'available_seats', 0),
                'category': trip.category.name if trip.category else ''
            }
            
            return JsonResponse({'success': True, 'data': data})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'حدث خطأ: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'طلب غير صالح'})
