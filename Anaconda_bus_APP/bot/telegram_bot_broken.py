import os
import sys
import django
from datetime import date, timedelta
from io import BytesIO
from PIL import Image
import qrcode
from django.core.files.base import ContentFile
from asgiref.sync import sync_to_async

# --- أضف مسار المشروع داخل الكونتينر ---
sys.path.append("/app")  # /app هو root المشروع داخل الكونتينر

# --- ربط مع settings Django الصحيح ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Main_Bus_Management.settings")
print("Setting up Django...")
try:
    django.setup()
    print("Django setup completed successfully")
except Exception as e:
    print(f"Django setup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# --- استدعاء المكتبات ---
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from Anaconda_bus_APP.models import passenger, Trip, Booking, Bus
from Anaconda_bus_APP.models import Booking

# --- التوكن من settings.py ---
try:
    TOKEN = settings.TELEGRAM_BOT_TOKEN
    print(f"Token loaded from settings: {TOKEN[:10]}..." if TOKEN else "Token is None or empty")
except Exception as e:
    print(f"Error loading token from settings: {e}")
    TOKEN = None

# --- دالة إرسال تأكيد الحجز التلقائي ---
async def send_booking_confirmation(booking_id):
    """إرسال تأكيد تلقائي عبر التليجرام بعد الحجز"""
    try:
        from telegram import Bot
        from asgiref.sync import sync_to_async
        
        # الحصول على بيانات الحجز
        booking = await sync_to_async(lambda: Booking.objects.get(id=booking_id))()
        passenger_obj = await sync_to_async(lambda: booking.passenger)()
        
        # التحقق إذا للراكب telegram_id
        telegram_id = await sync_to_async(lambda: passenger_obj.telegram_id)()
        
        if not telegram_id:
            print(f"Passenger {passenger_obj.name} has no telegram_id")
            return
        
        # إنشاء رسالة التأكيد
        passenger_name = await sync_to_async(lambda: passenger_obj.name)()
        booking_date = await sync_to_async(lambda: booking.booking_date)()
        transaction_number = await sync_to_async(lambda: booking.transaction_number)()
        status_display = await sync_to_async(lambda: booking.get_status_display())()
        
        # الحصول على معلومات الرحلة
        trip = await sync_to_async(lambda: booking.Trip)()
        if trip:
            trip_name = await sync_to_async(lambda: trip.trip_name)()
            trip_date = await sync_to_async(lambda: trip.date)()
            start_time = await sync_to_async(lambda: trip.start_time)()
            back_time = await sync_to_async(lambda: trip.back_time)()
            route = await sync_to_async(lambda: trip.route)()
        else:
            trip_name = "N/A"
            trip_date = "N/A"
            start_time = "N/A"
            back_time = "N/A"
            route = "N/A"
        
        confirmation_message = f"""
🎉 **تأكيد الحجز الناجح!**

👋 **مرحباً {passenger_name}**

🎫 **تفاصيل الحجز:**
📅 **تاريخ الحجز:** {booking_date.strftime('%Y-%m-%d %H:%M') if booking_date else 'N/A'}
🆔 **كود المعاملة:** {transaction_number or 'N/A'}
📊 **الحالة:** {status_display}

🚌 **معلومات الرحلة:**
📅 **التاريخ:** {trip_date}
⏰ **وقت الذهاب:** {start_time}
⏰ **وقت العودة:** {back_time}
🛣️ **الطريق:** {route or 'N/A'}
🚌 **اسم الرحلة:** {trip_name or 'N/A'}

✅ **تم حجز رحلتك بنجاح!**
📍 **يرجى الحضور في نقطة الركوب قبل 10 دقائق من موعد الانطلاق.**

📞 **للاستفسار:** يمكنكم التواصل مع خدمة العملاء.
"""
        
        # إرسال الرسالة عبر التليجرام
        bot = Bot(token=TOKEN)
        await bot.send_message(
            chat_id=telegram_id,
            text=confirmation_message,
            parse_mode='Markdown'
        )
        
        print(f"Booking confirmation sent to {passenger_name} (Telegram ID: {telegram_id})")
        
    except Exception as e:
        print(f"Error sending booking confirmation: {e}")
        import traceback
        traceback.print_exc()

# --- دالة مساعدة للحصول على رابط الصورة الكامل ---
def get_full_image_url(image_field):
    """الحصول على الرابط الكامل للصورة"""
    if not image_field:
        return None
    
    try:
        # استخدام settings.MEDIA_URL للحصول على الرابط الكامل
        if hasattr(image_field, 'url') and image_field.url:
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
            
            # التأكد من أن الرابط يبدأ بـ http
            if image_field.url.startswith('http'):
                return image_field.url
            else:
                return f"{base_url}{media_url}{image_field.url.lstrip('/')}"
    except Exception as e:
        print(f"Error building image URL: {e}")
        return None
    
    return None

# --- دالة عرض حجوزات الأسبوع أو الرحلات المتاحة ---
async def show_weekly_trips_or_available(update: Update, context: ContextTypes.DEFAULT_TYPE, passenger_obj):
    try:
        from datetime import datetime, date, timedelta
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())  # بداية الأسبوع (السبت)
        week_end = week_start + timedelta(days=6)  # نهاية الأسبوع (الجمعة)
        
        passenger_name = await sync_to_async(lambda: passenger_obj.name)()
        passenger_pickup = await sync_to_async(lambda: passenger_obj.last_selected_route)()
        
        # البحث عن حجوزات الأسبوع الحالي
        weekly_bookings = await sync_to_async(
            lambda: list(Booking.objects.filter(
                passenger=passenger_obj,
                booking_date__date__range=[week_start, week_end]
            ).order_by('-booking_date'))
        )()
        
        if weekly_bookings:
            # عرض حجوزات الأسبوع
            message = f"📅 **حجوزاتك هذا الأسبوع** ({week_start} - {week_end})\n\n"
            
            for i, booking in enumerate(weekly_bookings, 1):
                booking_date = await sync_to_async(lambda: booking.booking_date)()
                trip = await sync_to_async(lambda: booking.Trip)()
                
                if trip:
                    trip_name = await sync_to_async(lambda: trip.trip_name)()
                    trip_date = await sync_to_async(lambda: trip.date)()
                    start_time = await sync_to_async(lambda: trip.start_time)()
                    
                    message += f"🎫 **حجز {i}**\n"
                    message += f"📅 التاريخ: {trip_date}\n"
                    message += f"⏰ الوقت: {start_time}\n"
                    message += f"🚌 الرحلة: {trip_name or 'N/A'}\n"
                    message += f"📊 الحالة: {await sync_to_async(lambda: booking.get_status_display())()}\n\n"
            
            await update.message.reply_text(message)
            
        else:
            # لا يوجد حجوزات هذا الأسبوع - عرض الرحلات المتاحة
            await show_available_trips(update, context, passenger_obj, passenger_pickup)
            
    except Exception as e:
        print(f"Error in show_weekly_trips_or_available: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# --- دالة عرض الرحلات المتاحة ---
async def show_available_trips(update: Update, context: ContextTypes.DEFAULT_TYPE, passenger_obj, pickup_location=None):
    try:
        from datetime import datetime, date, timedelta
        
        today = date.today()
        passenger_name = await sync_to_async(lambda: passenger_obj.name)()
        passenger_category = await sync_to_async(lambda: passenger_obj.category)()
        
        # البحث عن الرحلات المتاحة اليوم
        available_trips = await sync_to_async(
            lambda: list(Trip.objects.filter(
                category=passenger_category,
                date=today,
                is_active=True
            ).order_by('start_time'))
        )()
        
        if available_trips:
            message = f"🚌 **الرحلات المتاحة اليوم** ({today})\n\n"
            
            for i, trip in enumerate(available_trips, 1):
                trip_name = await sync_to_async(lambda: trip.trip_name)()
                start_time = await sync_to_async(lambda: trip.start_time)()
                back_time = await sync_to_async(lambda: trip.back_time)()
                route = await sync_to_async(lambda: trip.route)()
                
                message += f"🚌 **رحلة {i}**\n"
                message += f"📅 التاريخ: {today}\n"
                message += f"⏰ الذهاب: {start_time}\n"
                message += f"⏰ العودة: {back_time}\n"
                message += f"🛣️ الطريق: {route or 'N/A'}\n"
                
                # إنشاء رابط الحجز
                booking_url = f"https://your-domain.com/book/{trip.id}"
                message += f"🔗 [احجز الآن]({booking_url})\n\n"
            
            message += "💡 **ملاحظة:** بعد الحجز، سيتم إرسال تأكيد تلقائي عبر التليجرام."
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        else:
            await update.message.reply_text(
                f"👋 مرحباً {passenger_name}!\n"
                f"❌ لا توجد رحلات متاحة اليوم ({today}).\n"
                "🔄 يرجى المحاولة مرة أخرى لاحقاً."
            )
            
    except Exception as e:
        print(f"Error in show_available_trips: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# --- Command /mybookings ---
async def show_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض كل حجوزات المستخدم بتفاصيل كاملة"""
    try:
        telegram_user_id = update.effective_user.id
        
        # التحقق إذا كان المستخدم مسجل
        try:
            passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            passenger_name = await sync_to_async(lambda: passenger_obj.name)()
            
            # الحصول على كل حجوزات المستخدم
            all_bookings = await sync_to_async(
                lambda: list(Booking.objects.filter(passenger=passenger_obj).order_by('-booking_date'))
            )()
            
            if not all_bookings:
                await update.message.reply_text(
                    f"👋 مرحباً {passenger_name}!\n"
                    "❌ لا توجد حجوزات سابقة لك."
                )
                return
            
            message = f"📋 **كل حجوزاتك**\n\n"
            
            for i, booking in enumerate(all_bookings, 1):
                # بيانات الحجز الأساسية
                booking_date = await sync_to_async(lambda: booking.booking_date)()
                transaction_number = await sync_to_async(lambda: booking.transaction_number)()
                
                # الحصول على القيم المعروضة بشكل آمن
                payment_method_field = await sync_to_async(lambda: booking.payment_method)()
                payment_method = dict(Booking.PAYMENT_METHODS).get(payment_method_field, payment_method_field)
                
                status_field = await sync_to_async(lambda: booking.status)()
                status = dict(Booking.STATUS_CHOICES).get(status_field, status_field)
                
                # الحصول على نوع الرحلة بشكل آمن
                trip_type_field = await sync_to_async(lambda: booking.trip_type)()
                trip_type = dict(Booking.TRIP_TYPE_CHOICES).get(trip_type_field, trip_type_field)
                
                message += f"🎫 **حجز {i}**\n"
                message += f"🆔 **كود المعاملة:** {transaction_number or 'N/A'}\n"
                message += f"📅 **تاريخ الحجز:** {booking_date.strftime('%Y-%m-%d %H:%M') if booking_date else 'N/A'}\n"
                message += f"💰 **طريقة الدفع:** {payment_method}\n"
                message += f"📊 **الحالة:** {status}\n"
                message += f"🚌 **نوع الرحلة:** {trip_type}\n"
                
                # بيانات رحلة الذهاب
                if trip_type in ['ذهاب فقط', 'ذهاب وعودة', 'ذهاب']:
                    departure_trip = await sync_to_async(lambda: booking.departure_trip)()
                    if departure_trip:
                        dep_date = await sync_to_async(lambda: departure_trip.date)()
                        dep_start_time = await sync_to_async(lambda: departure_trip.start_time)()
                        dep_route = await sync_to_async(lambda: departure_trip.route)()
                        dep_bus = await sync_to_async(lambda: departure_trip.bus)()
                        
                        message += f"\n🚌 **بيانات الذهاب:**\n"
                        message += f"📅 **التاريخ:** {dep_date}\n"
                        message += f"⏰ **الوقت:** {dep_start_time}\n"
                        message += f"🛣️ **الطريق:** {dep_route or 'N/A'}\n"
                        message += f"📍 **نقطة الركوب:** {selected_route_field = await sync_to_async(lambda: booking.selected_route)() or 'N/A'}\n"
                        
                        # بيانات السائق والباص
                        if dep_bus:
                            bus_name = await sync_to_async(lambda: dep_bus.name)()
                            bus_plate = await sync_to_async(lambda: dep_bus.plate_number)()
                            driver_name = "N/A"
                            
                            # محاولة الحصول على اسم السائق
                            if dep_bus.Bus_driver:
                                driver_first_name = await sync_to_async(lambda: dep_bus.Bus_driver.first_name)()
                                driver_last_name = await sync_to_async(lambda: dep_bus.Bus_driver.last_name)()
                                driver_username = await sync_to_async(lambda: dep_bus.Bus_driver.username)()
                                driver_name = f"{driver_first_name} {driver_last_name}".strip() or driver_username
                            
                            message += f"🚐 **الباص:** {bus_name} ({bus_plate})\n"
                            message += f"👨‍✈️ **السائق:** {driver_name}\n"
                        
                        # بيانات الكراسي
                        departure_seats_exist = await sync_to_async(lambda: booking.departure_seats.exists())()
                        if departure_seats_exist:
                            seats = await sync_to_async(list)(booking.departure_seats.all())
                            seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                            message += f"💺 **المقاعد:** {seat_numbers}\n"
                
                # بيانات رحلة العودة
                if trip_type in ['عودة فقط', 'ذهاب وعودة', 'عودة']:
                    return_trip = await sync_to_async(lambda: booking.return_trip)()
                    if return_trip:
                        ret_date = await sync_to_async(lambda: return_trip.date)()
                        ret_back_time = await sync_to_async(lambda: return_trip.back_time)()
                        ret_route = await sync_to_async(lambda: return_trip.route)()
                        ret_bus = await sync_to_async(lambda: return_trip.bus)()
                        
                        message += f"\n🚌 **بيانات العودة:**\n"
                        message += f"📅 **التاريخ:** {ret_date}\n"
                        message += f"⏰ **الوقت:** {ret_back_time}\n"
                        message += f"🛣️ **الطريق:** {ret_route or 'N/A'}\n"
                        message += f"📍 **نقطة النزول:** {await sync_to_async(lambda: booking.return_route)() or 'N/A'}\n"
                        
                        # بيانات السائق والباص
                        if ret_bus:
                            bus_name = await sync_to_async(lambda: ret_bus.name)()
                            bus_plate = await sync_to_async(lambda: ret_bus.plate_number)()
                            driver_name = "N/A"
                            
                            # محاولة الحصول على اسم السائق
                            if ret_bus.Bus_driver:
                                driver_first_name = await sync_to_async(lambda: ret_bus.Bus_driver.first_name)()
                                driver_last_name = await sync_to_async(lambda: ret_bus.Bus_driver.last_name)()
                                driver_username = await sync_to_async(lambda: ret_bus.Bus_driver.username)()
                                driver_name = f"{driver_first_name} {driver_last_name}".strip() or driver_username
                            
                            message += f"🚐 **الباص:** {bus_name} ({bus_plate})\n"
                            message += f"👨‍✈️ **السائق:** {driver_name}\n"
                        
                        # بيانات الكراسي
                        return_seats_exist = await sync_to_async(lambda: booking.return_seats.exists())()
                        if return_seats_exist:
                            seats = await sync_to_async(list)(booking.return_seats.all())
                            seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                            message += f"💺 **المقاعد:** {seat_numbers}\n"
                
                # بيانات الرحلة القديمة (للتوافق)
                else:
                    trip = await sync_to_async(lambda: booking.Trip)()
                    if trip:
                        trip_date = await sync_to_async(lambda: trip.date)()
                        trip_start_time = await sync_to_async(lambda: trip.start_time)()
                        trip_back_time = await sync_to_async(lambda: trip.back_time)()
                        trip_route = await sync_to_async(lambda: trip.route)()
                        trip_bus = await sync_to_async(lambda: trip.bus)()
                        
                        message += f"\n🚌 **بيانات الرحلة:**\n"
                        message += f"📅 **التاريخ:** {trip_date}\n"
                        message += f"⏰ **وقت الذهاب:** {trip_start_time}\n"
                        message += f"⏰ **وقت العودة:** {trip_back_time}\n"
                        message += f"🛣️ **الطريق:** {trip_route or 'N/A'}\n"
                        message += f"📍 **نقطة الركوب:** {selected_route_field = await sync_to_async(lambda: booking.selected_route)() or 'N/A'}\n"
                        
                        # بيانات السائق والباص
                        if trip_bus:
                            bus_name = await sync_to_async(lambda: trip_bus.name)()
                            bus_plate = await sync_to_async(lambda: trip_bus.plate_number)()
                            driver_name = "N/A"
                            
                            # محاولة الحصول على اسم السائق
                            if trip_bus.Bus_driver:
                                driver_first_name = await sync_to_async(lambda: trip_bus.Bus_driver.first_name)()
                                driver_last_name = await sync_to_async(lambda: trip_bus.Bus_driver.last_name)()
                                driver_username = await sync_to_async(lambda: trip_bus.Bus_driver.username)()
                                driver_name = f"{driver_first_name} {driver_last_name}".strip() or driver_username
                            
                            message += f"🚐 **الباص:** {bus_name} ({bus_plate})\n"
                            message += f"👨‍✈️ **السائق:** {driver_name}\n"
                        
                        # بيانات الكراسي
                        seats_reserved_exist = await sync_to_async(lambda: booking.seats_reserved.exists())()
                        if seats_reserved_exist:
                            seats = await sync_to_async(list)(booking.seats_reserved.all())
                            seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                            message += f"💺 **المقاعد:** {seat_numbers}\n"
                
                message += "\n" + "="*40 + "\n\n"
            
            # تقسيم الرسالة لو كانت طويلة جداً
            if len(message) > 4000:
                # إرسال أول جزء
                await update.message.reply_text(message[:4000] + "\n\n*(يتم إرسال الباقي في رسالة تالية)*")
                # إرسال باقي الرسالة
                await update.message.reply_text(message[4000:])
            else:
                await update.message.reply_text(message)
                
        except passenger.DoesNotExist:
            await update.message.reply_text(
                "❌ لم يتم العثور على حسابك.\n"
                "🔄 يرجى إرسال كود الجامعة للتسجيل أولاً."
            )
            
    except Exception as e:
        print(f"Error in show_my_bookings: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# --- Command /trips ---
async def show_trips_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الرحلات المتاحة"""
    try:
        telegram_user_id = update.effective_user.id
        
        # التحقق إذا كان المستخدم مسجل
        try:
            passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            passenger_pickup = await sync_to_async(lambda: passenger_obj.last_selected_route)()
            
            # عرض الرحلات المتاحة
            await show_available_trips(update, context, passenger_obj, passenger_pickup)
            
        except passenger.DoesNotExist:
            await update.message.reply_text(
                "❌ لم يتم العثور على حسابك.\n"
                "🔄 يرجى إرسال كود الجامعة للتسجيل أولاً."
            )
            
    except Exception as e:
        print(f"Error in show_trips_command: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# --- Command /reset ---
async def reset_telegram_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_user_id = update.effective_user.id
        
        # البحث عن الراكب المرتبط بالـ telegram_id الحالي
        try:
            passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            
            # مسح الـ telegram_id
            passenger_obj.telegram_id = None
            await sync_to_async(passenger_obj.save)()
            
            await update.message.reply_text(
                "✅ تم حذف حسابك من البوت بنجاح!\n"
                "🔄 الآن يمكنك إرسال كود جامعة جديد للتسجيل مرة أخرى."
            )
            
        except passenger.DoesNotExist:
            await update.message.reply_text(
                "❌ لم يتم العثور على حساب مرتبط بهذا البوت.\n"
                "🔄 يمكنك إرسال كود الجامعة للتسجيل الآن."
            )
            
    except Exception as e:
        print(f"Error in reset function: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")

# --- Command /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        print(f"Start command received from user: {update.effective_user.id}")
        
        telegram_user_id = update.effective_user.id
        telegram_username = update.effective_user.username

        # التحقق إذا كان المستخدم مسجل مسبقاً
        try:
            print(f"Checking for existing passenger with telegram_id: {telegram_user_id}")
            existing_passenger = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            print(f"Found existing passenger: {existing_passenger.name}")
            
            # عرض حجوزات الأسبوع أو الرحلات المتاحة
            await show_weekly_trips_or_available(update, context, existing_passenger)
            return
        except passenger.DoesNotExist:
            print("No existing passenger found, asking for university code")
            pass
        except Exception as e:
            print(f"Error checking existing passenger: {e}")
        
        # طلب كود الجامعة من المستخدم
        print("Sending university code request message")
        await update.message.reply_text(
            "👋 مرحباً!\n"
            "للتسجيل في البوت، يرجى إرسال كود الجامعة الخاص بك."
        )
        
    except Exception as e:
        print(f"Error in start function: {e}")
        try:
            await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")
        except:
            print("Could not send error message to user")

# --- دالة للتعامل مع كود الجامعة ---
async def handle_university_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_user_id = update.effective_user.id
    university_code = update.message.text.strip()
    
    try:
        # البحث عن الراكب باستخدام كود الجامعة
        passenger_obj = await sync_to_async(passenger.objects.get)(university_code=university_code)
        
        # حفظ Telegram ID
        passenger_obj.telegram_id = telegram_user_id
        await sync_to_async(passenger_obj.save)()
        
        # إرسال آخر حجز للراكب
        await send_latest_booking(update, context, passenger_obj)
        
    except passenger.DoesNotExist:
        await update.message.reply_text(
            "❌ لم يتم العثور على كود الجامعة.\n"
            "يرجى التأكد من الكود والمحاولة مرة أخرى."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)}"
        )

# --- دالة إرسال آخر حجز ---
async def send_latest_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, passenger_obj):
    try:
        # البحث عن آخر حجز للراكب
        latest_booking = await sync_to_async(
            lambda: Booking.objects.filter(passenger=passenger_obj)
            .order_by('-booking_date').first()
        )()
        
        if latest_booking:
            # جمع معلومات الحجز
            booking_info = await get_booking_info(latest_booking)
            
            # إرسال رسالة الحجز
            await update.message.reply_text(booking_info['text'])
            
            # إرسال صورة الباص إذا وجدت
            trip = await sync_to_async(lambda: latest_booking.Trip)()
            if trip:
                bus = await sync_to_async(lambda: trip.bus)()
                if bus:
                    bus_image = await sync_to_async(lambda: bus.bus_image)()
                    if bus_image:
                        try:
                            bus_image_url = get_full_image_url(bus_image)
                            if bus_image_url:
                                await context.bot.send_photo(
                                    chat_id=update.effective_user.id,
                                    photo=bus_image_url,
                                    caption="🚌 صورة الباص"
                                )
                            else:
                                print("Bus image URL is None or empty")
                        except Exception as e:
                            print(f"Error sending bus image: {e}")
            
            # إرسال صورة الطالب إذا وجدت
            face_thumbnail = await sync_to_async(lambda: passenger_obj.face_thumbnail)()
            if face_thumbnail:
                try:
                    face_thumbnail_url = get_full_image_url(face_thumbnail)
                    if face_thumbnail_url:
                        await context.bot.send_photo(
                            chat_id=update.effective_user.id,
                            photo=face_thumbnail_url,
                            caption="👤 صورتك الشخصية"
                        )
                    else:
                        print("Face thumbnail URL is None or empty")
                except Exception as e:
                    print(f"Error sending passenger image: {e}")
                    
        else:
            passenger_name = await sync_to_async(lambda: passenger_obj.name)()
            await update.message.reply_text(
                f"👋 مرحباً {passenger_name}!\n"
                "❌ لا توجد حجوزات سابقة لك."
            )
            
    except Exception as e:
        print(f"Error in send_latest_booking: {e}")
        await update.message.reply_text(
            f"❌ حدث خطأ في جلب بيانات الحجز: {str(e)}"
        )

# --- دالة جمع معلومات الحجز ---
async def get_booking_info(booking):
    try:
        # الحصول على معلومات الحجز الأساسية
        booking_date = await sync_to_async(lambda: booking.booking_date)()
        transaction_number = await sync_to_async(lambda: booking.transaction_number)()
        payment_method_display = await sync_to_async(lambda: booking.get_payment_method_display())()
        status_display = await sync_to_async(lambda: booking.get_status_display())()
        
        info_text = f"""
🎫 **تفاصيل الحجز**
📅 **تاريخ الحجز**: {booking_date.strftime('%Y-%m-%d %H:%M') if booking_date else 'N/A'}
🆔 **كود المعاملة**: {transaction_number or 'N/A'}
💰 **طريقة الدفع**: {payment_method_display}
📊 **الحالة**: {status_display}
"""
        
        # التحقق من رحلة الذهاب
        departure_trip = await sync_to_async(lambda: booking.departure_trip)()
        if departure_trip:
            dep_date = await sync_to_async(lambda: departure_trip.date)()
            dep_start_time = await sync_to_async(lambda: departure_trip.start_time)()
            dep_route = await sync_to_async(lambda: departure_trip.route)()
            selected_route = selected_route_field = await sync_to_async(lambda: booking.selected_route)()
            
            info_text += f"""
🚌 **رحلة الذهاب**:
   📅 التاريخ: {dep_date}
   ⏰ الوقت: {dep_start_time}
   🛣️ الطريق: {dep_route or 'N/A'}
   📍 نقطة الركوب: {selected_route or 'N/A'}
"""
            
            # التحقق من كراسي الذهاب
            departure_seats_exist = await sync_to_async(lambda: booking.departure_seats.exists())()
            if departure_seats_exist:
                seats = await sync_to_async(list)(booking.departure_seats.all())
                seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                info_text += f"   💺 المقاعد: {seat_numbers}\n"
        
        # التحقق من رحلة العودة
        return_trip = await sync_to_async(lambda: booking.return_trip)()
        if return_trip:
            ret_date = await sync_to_async(lambda: return_trip.date)()
            ret_back_time = await sync_to_async(lambda: return_trip.back_time)()
            ret_route = await sync_to_async(lambda: return_trip.route)()
            return_route = await sync_to_async(lambda: booking.return_route)()
            
            info_text += f"""
🚌 **رحلة العودة**:
   📅 التاريخ: {ret_date}
   ⏰ الوقت: {ret_back_time}
   🛣️ الطريق: {ret_route or 'N/A'}
   📍 نقطة النزول: {return_route or 'N/A'}
"""
            
            # التحقق من كراسي العودة
            return_seats_exist = await sync_to_async(lambda: booking.return_seats.exists())()
            if return_seats_exist:
                seats = await sync_to_async(list)(booking.return_seats.all())
                seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                info_text += f"   💺 المقاعد: {seat_numbers}\n"
        
        # معلومات الرحلة القديمة (للتوافق)
        else:
            trip = await sync_to_async(lambda: booking.Trip)()
            if trip:
                trip_date = await sync_to_async(lambda: trip.date)()
                trip_start_time = await sync_to_async(lambda: trip.start_time)()
                trip_back_time = await sync_to_async(lambda: trip.back_time)()
                trip_route = await sync_to_async(lambda: trip.route)()
                
                info_text += f"""
🚌 **معلومات الرحلة**:
   📅 التاريخ: {trip_date}
   ⏰ وقت الذهاب: {trip_start_time}
   ⏰ وقت العودة: {trip_back_time}
   🛣️ الطريق: {trip_route or 'N/A'}
"""
                
                # التحقق من الكراسي المحجوزة
                seats_reserved_exist = await sync_to_async(lambda: booking.seats_reserved.exists())()
                if seats_reserved_exist:
                    seats = await sync_to_async(list)(booking.seats_reserved.all())
                    seat_numbers = ", ".join([str(seat.seat_number) for seat in seats])
                    info_text += f"   💺 المقاعد: {seat_numbers}\n"
        
        return {'text': info_text}
        
    except Exception as e:
        print(f"Error in get_booking_info: {e}")
        return {'text': f"❌ خطأ في جلب تفاصيل الحجز: {str(e)}"}

# --- Main ---
def main():
    try:
        print("Starting bot...")
        print(f"Token: {TOKEN}")
        
        if not TOKEN:
            print("ERROR: TELEGRAM_BOT_TOKEN is not set!")
            return
            
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("trips", show_trips_command))
        app.add_handler(CommandHandler("mybookings", show_my_bookings))
        app.add_handler(CommandHandler("reset", reset_telegram_id))
        
        # معالج الرسائل النصية (لكود الجامعة)
        from telegram.ext import MessageHandler, filters
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_university_code))
        
        print("Bot handlers registered successfully...")
        print("Bot is running...")
        app.run_polling()
        
    except Exception as e:
        print(f"Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()