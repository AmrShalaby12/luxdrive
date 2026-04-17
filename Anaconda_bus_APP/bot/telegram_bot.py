import os
import sys
import django
from datetime import date, timedelta
from io import BytesIO
from PIL import Image
import qrcode
import uuid
import hmac
import hashlib
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode
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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from Anaconda_bus_APP.models import Booking, Category, City, DropoffLocation, FormReservation, PickupLocation, Round, Trip, passenger

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
        status_field = await sync_to_async(lambda: booking.status)()
        status = dict(Booking.STATUS_CHOICES).get(status_field, status_field)
        
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
📊 **الحالة:** {status}

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
        
        # عرض القائمة الرئيسية
        await send_main_menu(update, context, passenger_obj)
        
    except passenger.DoesNotExist:
        await update.message.reply_text(
            "❌ لم يتم العثور على كود الجامعة.\n"
            "يرجى التأكد من الكود والمحاولة مرة أخرى."
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ حدث خطأ: {str(e)}"
        )


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, passenger_obj):
    """عرض القائمة الرئيسية الاحترافية بعد تسجيل الدخول"""
    passenger_name = await sync_to_async(lambda: passenger_obj.name)()
    passenger_category = await sync_to_async(lambda: passenger_obj.category)()
    category_name = await sync_to_async(lambda: passenger_category.name)() if passenger_category else "غير محدد"
    
    welcome_msg = f"""🎉 مرحباً {passenger_name}!
🏫 الجامعة: {category_name}
📱 تم تسجيل دخولك بنجاح

اختر الخدمة المطلوبة من القائمة:"""
    
    keyboard = [
        [InlineKeyboardButton("📋 طلب حجز جديد", callback_data="menu:reserve")],
        [InlineKeyboardButton("🎫 حجوزاتي", callback_data="menu:mybookings")],
        [InlineKeyboardButton("✏️ تعديل الحجز", callback_data="menu:edit_booking")],
        [InlineKeyboardButton("❓ الأسئلة الشائعة", callback_data="menu:faq")],
        [InlineKeyboardButton("📝 إرسال شكوى", callback_data="menu:complaint")],
        [InlineKeyboardButton("🔄 إعادة تعيين", callback_data="menu:reset")],
    ]
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_main_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض زر العودة للقائمة الرئيسية"""
    keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="menu:main")]]
    await update.message.reply_text("اختر من القائمة:", reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data or ""
    if not data.startswith("menu:"):
        return
    
    action = data.split(":")[1]
    
    if action == "main":
        # إعادة عرض القائمة الرئيسية
        telegram_user_id = query.from_user.id
        passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
        await send_main_menu(update, context, passenger_obj)
    elif action == "reserve":
        await start_form_reservation(update, context)
    elif action == "mybookings":
        await show_my_bookings(update, context)
    elif action == "edit_booking":
        await start_edit_booking(update, context)
    elif action == "faq":
        await send_faq(update, context)
    elif action == "complaint":
        await start_complaint(update, context)
    elif action == "reset":
        await reset_telegram_id(update, context)
    else:
        await query.message.reply_text("❌ اختيار غير معروف.")

# --- Command /mybookings ---
async def show_my_bookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر حجز للمستخدم بتفاصيل كاملة"""
    try:
        telegram_user_id = update.effective_user.id
        
        # التحقق إذا كان المستخدم مسجل
        try:
            passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            passenger_name = await sync_to_async(lambda: passenger_obj.name)()
            
            # الحصول على آخر حجز للمستخدم
            latest_booking = await sync_to_async(
                lambda: Booking.objects.filter(passenger=passenger_obj).order_by('-booking_date').first()
            )()
            
            if not latest_booking:
                await update.message.reply_text(
                    f"👋 مرحباً {passenger_name}!\n"
                    "❌ لا توجد حجوزات سابقة لك."
                )
                return
            
            booking = latest_booking

            message = f"🎫 **آخر حجز ليك**\n\n"

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
                    dep_trip_name = await sync_to_async(lambda: departure_trip.trip_name)()
                    dep_bus = await sync_to_async(lambda: departure_trip.bus)()
                    selected_route_field = await sync_to_async(lambda: booking.selected_route)()
                    
                    message += f"\n🚌 **بيانات الذهاب:**\n"
                    message += f"📅 **التاريخ:** {dep_date}\n"
                    message += f"⏰ **الوقت:** {dep_start_time}\n"
                    message += f"🚌 **اسم الرحلة:** {dep_trip_name or 'N/A'}\n"
                    message += f"🛣️ **الطريق:** {dep_route or 'N/A'}\n"
                    message += f"📍 **نقطة الركوب:** {selected_route_field or 'N/A'}\n"
                    
                    # بيانات السائق والباص
                    if dep_bus:
                        bus_name = await sync_to_async(lambda: dep_bus.name)()
                        bus_plate = await sync_to_async(lambda: dep_bus.plate_number)()
                        bus_driver_number = await sync_to_async(lambda: dep_bus.driver_number)()
                        driver_name = "N/A"
                        
                        # محاولة الحصول على اسم السائق
                        bus_driver = await sync_to_async(lambda: dep_bus.Bus_driver)()
                        if bus_driver:
                            driver_first_name = await sync_to_async(lambda: bus_driver.first_name)()
                            driver_last_name = await sync_to_async(lambda: bus_driver.last_name)()
                            driver_username = await sync_to_async(lambda: bus_driver.username)()
                            driver_name = f"{driver_first_name} {driver_last_name}".strip() or driver_username
                        
                        message += f"🚐 **الباص:** {bus_name}\n"
                        message += f"🔢 **نمر العربية:** {bus_plate or 'N/A'}\n"
                        message += f"👨‍✈️ **اسم السواق:** {driver_name}\n"
                        message += f"📞 **رقم السواق:** {bus_driver_number or 'N/A'}\n"
                    
                    # بيانات الكراسي
                    departure_seats_count = await sync_to_async(lambda: booking.departure_seats.count())()
                    if departure_seats_count > 0:
                        seats = await sync_to_async(lambda: list(booking.departure_seats.values('seat_number')))()
                        seat_numbers = ", ".join([str(seat['seat_number']) for seat in seats])
                        message += f"💺 **المقاعد:** {seat_numbers}\n"
                
            # بيانات رحلة العودة
            if trip_type in ['عودة فقط', 'ذهاب وعودة', 'عودة']:
                return_trip = await sync_to_async(lambda: booking.return_trip)()
                # fallback لو الحجز قديم ومستخدم Booking.Trip بدل return_trip
                if not return_trip:
                    return_trip = await sync_to_async(lambda: booking.Trip)()

                if return_trip:
                    ret_date = await sync_to_async(lambda: return_trip.date)()
                    ret_back_time = await sync_to_async(lambda: return_trip.back_time)()
                    ret_route = await sync_to_async(lambda: return_trip.route)()
                    ret_trip_name = await sync_to_async(lambda: return_trip.trip_name)()
                    ret_bus = await sync_to_async(lambda: return_trip.bus)()
                    pickup_point_field = await sync_to_async(lambda: booking.selected_route)()
                    return_route_field = await sync_to_async(lambda: booking.return_route)()
                    
                    message += f"\n🚌 **بيانات العودة:**\n"
                    message += f"📅 **التاريخ:** {ret_date}\n"
                    message += f"⏰ **الوقت:** {ret_back_time}\n"
                    message += f"🚌 **اسم الرحلة:** {ret_trip_name or 'N/A'}\n"
                    message += f"🛣️ **الطريق:** {ret_route or 'N/A'}\n"
                    message += f"📍 **نقطة الركوب:** {pickup_point_field or 'N/A'}\n"
                    message += f"📍 **نقطة النزول:** {return_route_field or 'N/A'}\n"
                    
                    # بيانات السائق والباص
                    if ret_bus:
                        bus_name = await sync_to_async(lambda: ret_bus.name)()
                        bus_plate = await sync_to_async(lambda: ret_bus.plate_number)()
                        bus_driver_number = await sync_to_async(lambda: ret_bus.driver_number)()
                        driver_name = "N/A"
                        
                        # محاولة الحصول على اسم السائق
                        bus_driver = await sync_to_async(lambda: ret_bus.Bus_driver)()
                        if bus_driver:
                            driver_first_name = await sync_to_async(lambda: bus_driver.first_name)()
                            driver_last_name = await sync_to_async(lambda: bus_driver.last_name)()
                            driver_username = await sync_to_async(lambda: bus_driver.username)()
                            driver_name = f"{driver_first_name} {driver_last_name}".strip() or driver_username
                        
                        message += f"🚐 **الباص:** {bus_name}\n"
                        message += f"🔢 **نمر العربية:** {bus_plate or 'N/A'}\n"
                        message += f"👨‍✈️ **اسم السواق:** {driver_name}\n"
                        message += f"📞 **رقم السواق:** {bus_driver_number or 'N/A'}\n"
                    
                    # بيانات الكراسي
                    return_seats_count = await sync_to_async(lambda: booking.return_seats.count())()
                    if return_seats_count > 0:
                        seats = await sync_to_async(lambda: list(booking.return_seats.values('seat_number')))()
                        seat_numbers = ", ".join([str(seat['seat_number']) for seat in seats])
                        message += f"💺 **المقاعد:** {seat_numbers}\n"
                
            await update.message.reply_text(message)

            # إرسال صورة العربية (لو موجودة) بناءً على رحلة الذهاب ثم العودة
            async def _get_bus_image_field():
                dep_trip = await sync_to_async(lambda: booking.departure_trip)()
                if dep_trip:
                    dep_bus_obj = await sync_to_async(lambda: dep_trip.bus)()
                    if dep_bus_obj:
                        img = await sync_to_async(lambda: dep_bus_obj.bus_image)()
                        if img:
                            return img
                ret_trip = await sync_to_async(lambda: booking.return_trip)()
                if ret_trip:
                    ret_bus_obj = await sync_to_async(lambda: ret_trip.bus)()
                    if ret_bus_obj:
                        img = await sync_to_async(lambda: ret_bus_obj.bus_image)()
                        if img:
                            return img
                main_trip = await sync_to_async(lambda: booking.Trip)()
                if main_trip:
                    main_bus_obj = await sync_to_async(lambda: main_trip.bus)()
                    if main_bus_obj:
                        img = await sync_to_async(lambda: main_bus_obj.bus_image)()
                        if img:
                            return img
                return None

            try:
                bus_image_field = await _get_bus_image_field()
                if bus_image_field:
                    image_path = await sync_to_async(lambda: bus_image_field.path)()
                    if image_path and os.path.exists(image_path):
                        image_bytes = await sync_to_async(lambda: open(image_path, 'rb').read())()
                        bio = BytesIO(image_bytes)
                        bio.name = os.path.basename(image_path) or 'bus.jpg'
                        await context.bot.send_photo(
                            chat_id=telegram_user_id,
                            photo=bio,
                            caption="🚌 صورة العربية"
                        )
            except Exception as e:
                print(f"Error sending bus image in /mybookings: {e}")
                
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
                    status_field = await sync_to_async(lambda: booking.status)()
                    status = dict(Booking.STATUS_CHOICES).get(status_field, status_field)
                    message += f"📊 الحالة: {status}\n\n"
            
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
            keyboard = []

            for i, trip in enumerate(available_trips, 1):
                trip_id = await sync_to_async(lambda: trip.id)()
                trip_name = await sync_to_async(lambda: trip.trip_name)()
                start_time = await sync_to_async(lambda: trip.start_time)()
                back_time = await sync_to_async(lambda: trip.back_time)()
                route = await sync_to_async(lambda: trip.route)()
                trip_type_value = await sync_to_async(lambda: trip.trip_type)()

                if trip_type_value == 'one_way':
                    price = await sync_to_async(lambda: trip.one_way_price)()
                elif trip_type_value == 'return':
                    price = await sync_to_async(lambda: trip.return_price)()
                elif trip_type_value == 'round_trip':
                    price = await sync_to_async(lambda: trip.round_trip_price)()
                elif trip_type_value == 'round_differentdays':
                    dep_price = await sync_to_async(lambda: trip.departure_seat_price)()
                    ret_price = await sync_to_async(lambda: trip.return_seat_price)()
                    price = (dep_price or 0) + (ret_price or 0)
                else:
                    price = None

                message += f"🚌 **رحلة {i}**\n"
                message += f"� الرحلة: {trip_name or 'N/A'}\n"
                message += f"⏰ الذهاب: {start_time}\n"
                message += f"⏰ العودة: {back_time}\n"
                message += f"🛣️ الطريق: {route or 'N/A'}\n"
                if price is not None:
                    message += f"💰 السعر: {price}\n"
                message += "\n"

                keyboard.append([
                    InlineKeyboardButton(
                        text=f"احجز رحلة {i}",
                        callback_data=f"book_trip:{trip_id}"
                    )
                ])

            await update.message.reply_text(
                message,
                parse_mode=None,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        else:
            await update.message.reply_text(
                f"👋 مرحباً {passenger_name}!\n"
                f"❌ لا توجد رحلات متاحة اليوم ({today}).\n"
                "🔄 يرجى المحاولة مرة أخرى لاحقاً."
            )
            
    except Exception as e:
        print(f"Error in show_available_trips: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def start_form_reservation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        telegram_user_id = update.effective_user.id
        passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
        passenger_category = await sync_to_async(lambda: passenger_obj.category)()

        if not passenger_category:
            await update.message.reply_text("❌ لا توجد جامعة مرتبطة بحسابك.")
            return

        form_support = await sync_to_async(lambda: getattr(passenger_category, 'Form_support', False))()
        form_active = await sync_to_async(lambda: getattr(passenger_category, 'Form_active', False))()
        if not form_support:
            await update.message.reply_text("❌ هذه الجامعة لا تدعم نموذج الحجز حالياً.")
            return
        if not form_active:
            await update.message.reply_text("❌ هذا النموذج لا يقبل الحجوزات حالياً.")
            return

        context.user_data['form_reservation'] = {
            'category_id': await sync_to_async(lambda: passenger_category.id)(),
            'trip_type': None,
            'going': {},
            'return': {},
            'payment_method': None,
            'trip_date': None,
        }

        keyboard = [[
            InlineKeyboardButton("ذهاب", callback_data="fr:trip_type:ذهاب"),
            InlineKeyboardButton("عودة", callback_data="fr:trip_type:عودة"),
        ], [
            InlineKeyboardButton("ذهاب وعودة", callback_data="fr:trip_type:ذهاب وعودة"),
        ]]

        await update.message.reply_text(
            "اختار نوع الرحلة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except passenger.DoesNotExist:
        await update.message.reply_text("❌ لم يتم العثور على حسابك. أرسل كود الجامعة أولاً.")
    except Exception as e:
        print(f"Error in start_form_reservation: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def cancel_form_reservation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('form_reservation', None)
    await update.message.reply_text("✅ تم إلغاء طلب الحجز.")


async def start_edit_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية تعديل الحجز"""
    try:
        telegram_user_id = update.effective_user.id
        passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
        
        # الحصول على الحجوزات المؤكدة فقط
        bookings = await sync_to_async(
            lambda: list(Booking.objects.filter(passenger=passenger_obj, status='active').order_by('-booking_date'))
        )()
        
        if not bookings:
            await update.message.reply_text(
                "❌ لا توجد حجوزات مؤكدة لتعديلها.\n"
                "يمكنك طلب حجز جديد من القائمة الرئيسية."
            )
            return
        
        # عرض قائمة الحجوزات المتاحة للتعديل
        keyboard = []
        for booking in bookings[:10]:  # عرض آخر 10 حجوزات
            booking_date = await sync_to_async(lambda: booking.booking_date)()
            trip_name = "غير محدد"
            if booking.Trip:
                trip_name = await sync_to_async(lambda: booking.Trip.trip_name)()
            
            display_text = f"حجز #{booking.id} - {trip_name} - {booking_date.strftime('%Y-%m-%d')}"
            keyboard.append([InlineKeyboardButton(display_text, callback_data=f"edit:select:{booking.id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu:main")])
        
        await update.message.reply_text(
            "📝 اختر الحجز الذي تريد تعديله:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except passenger.DoesNotExist:
        await update.message.reply_text("❌ لم يتم العثور على حسابك.")
    except Exception as e:
        print(f"Error in start_edit_booking: {e}")
        await update.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def handle_edit_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيارات تعديل الحجز"""
    query = update.callback_query
    await query.answer()
    
    data = query.data or ""
    if not data.startswith("edit:"):
        return
    
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    
    if action == "select":
        booking_id = int(parts[2])
        context.user_data['edit_booking_id'] = booking_id
        
        keyboard = [
            [InlineKeyboardButton("🪑 تغيير المقعد", callback_data=f"edit:action:seat:{booking_id}")],
            [InlineKeyboardButton("📍 تغيير نقطة الركوب", callback_data=f"edit:action:pickup:{booking_id}")],
            [InlineKeyboardButton("📍 تغيير نقطة النزول", callback_data=f"edit:action:dropoff:{booking_id}")],
            [InlineKeyboardButton("❌ إلغاء الحجز", callback_data=f"edit:action:cancel:{booking_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="menu:main")],
        ]
        
        await query.message.reply_text(
            "✏️ اختر ما تريد تعديله في هذا الحجز:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif action == "action":
        booking_id = int(parts[2])
        edit_type = parts[3]
        
        if edit_type == "cancel":
            await cancel_booking(update, context, booking_id)
        elif edit_type == "seat":
            await start_seat_change(update, context, booking_id)
        elif edit_type == "pickup":
            await start_pickup_change(update, context, booking_id)
        elif edit_type == "dropoff":
            await start_dropoff_change(update, context, booking_id)


async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: int):
    """إلغاء حجز"""
    try:
        booking = await sync_to_async(Booking.objects.get)(id=booking_id)
        booking.status = 'cancelled'
        await sync_to_async(booking.save)()
        
        await update.callback_query.message.reply_text(
            f"✅ تم إلغاء الحجز #{booking_id} بنجاح."
        )
        
    except Booking.DoesNotExist:
        await update.callback_query.message.reply_text("❌ الحجز غير موجود.")
    except Exception as e:
        print(f"Error canceling booking: {e}")
        await update.callback_query.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def start_seat_change(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: int):
    """بدء تغيير المقعد"""
    try:
        booking = await sync_to_async(Booking.objects.get)(id=booking_id)
        
        # الحصول على المقاعد المتاحة
        if booking.Trip and booking.Trip.bus:
            bus = await sync_to_async(lambda: booking.Trip.bus)()
            all_seats = await sync_to_async(lambda: list(bus.seats.all().order_by('seat_number')))()
            
            # الحصول على المقاعد المحجوزة
            reserved_seats = await sync_to_async(
                lambda: set(Booking.objects.filter(Trip=booking.Trip, status='active')
                           .values_list('seats_reserved__seat_number', flat=True))
            )()
            
            available_seats = [seat for seat in all_seats if seat.seat_number not in reserved_seats]
            
            if not available_seats:
                await update.callback_query.message.reply_text("❌ لا توجد مقاعد متاحة للتغيير.")
                return
            
            keyboard = []
            for seat in available_seats[:20]:  # عرض أول 20 مقعد متاح
                keyboard.append([InlineKeyboardButton(
                    f"كرسي {seat.seat_number}",
                    callback_data=f"edit:seat_confirm:{booking_id}:{seat.seat_number}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu:main")])
            
            await update.callback_query.message.reply_text(
                "🪑 اختر المقعد الجديد:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.callback_query.message.reply_text("❌ لا يمكن تغيير المقعد في هذا الحجز.")
            
    except Booking.DoesNotExist:
        await update.callback_query.message.reply_text("❌ الحجز غير موجود.")
    except Exception as e:
        print(f"Error in start_seat_change: {e}")
        await update.callback_query.message.reply_text(f"❌ حدث خطأ: {str(e)}")


async def start_pickup_change(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: int):
    """بدء تغيير نقطة الركوب"""
    # هنا يمكن إضافة منطق تغيير نقطة الركوب
    await update.callback_query.message.reply_text(
        "📍 تغيير نقطة الركوب قيد التطوير...\n"
        "يرجى التواصل مع الدعم لتغيير نقطة الركوب."
    )


async def start_dropoff_change(update: Update, context: ContextTypes.DEFAULT_TYPE, booking_id: int):
    """بدء تغيير نقطة النزول"""
    # هنا يمكن إضافة منطق تغيير نقطة النزول
    await update.callback_query.message.reply_text(
        "📍 تغيير نقطة النزول قيد التطوير...\n"
        "يرجى التواصل مع الدعم لتغيير نقطة النزول."
    )


async def send_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الأسئلة الشائعة"""
    faq_text = """❓ **الأسئلة الشائعة**

🚌 **كيف أحجز رحلة؟**
- اختر "طلب حجز جديد" من القائمة الرئيسية
- اتبع الخطوات لاختيار نوع الرحلة والمدينة والمواعيد

🎫 **كيف أعرض حجوزاتي؟**
- اختر "حجوزاتي" من القائمة الرئيسية
- ستعرض آخر حجز مؤكد مع جميع التفاصيل

✏️ **كيف أعدل حجزي؟**
- اختر "تعديل الحجز" من القائمة الرئيسية
- اختر الحجز ثم اختر ما تريد تعديله (المقعد، نقطة الركوب، إلخ)

💰 **ما هي طرق الدفع المتاحة؟**
- أونلاين (بطاقة ائتمان/محفظة إلكترونية)
- نقداً (للجامعات التي تسمح بذلك)
- اشتراك (برصيد الاشتراك المتاح)

⏰ **متى يتم تأكيد الحجز؟**
- بعد الدفع الأونلاين: فوراً
- الدفع النقدي/الاشتراك: بعد تسكين الأدمن

📞 **كيف أتواصل مع الدعم؟**
- اختر "إرسال شكوى" من القائمة الرئيسية
- أو تواصل مباشرة عبر رقم الدعم

🔄 **ماذا أفعل إذا لم أستقبل رسالة التأكيد؟**
- انتظر 5 دقائق ثم تحقق من "حجوزاتي"
- إذا لم يظهر الحجز، أرسل شكوى للمتابعة"""
    
    keyboard = [
        [InlineKeyboardButton("📝 إرسال شكوى", callback_data="menu:complaint")],
        [InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="menu:main")],
    ]
    
    await update.callback_query.message.reply_text(
        faq_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def start_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية إرسال شكوى"""
    context.user_data['complaint_step'] = 'waiting_text'
    
    complaint_types = [
        "🚌 مشكلة في الحجز",
        "💳 مشكلة في الدفع", 
        "📍 مشكلة في نقطة الركوب/النزول",
        "⏰ مشكلة في المواعيد",
        "📞 مشكلة في التواصل",
        "🔧 مشكلة تقنية",
        "❓ استفسار عام",
        "📝 أخرى"
    ]
    
    keyboard = []
    for i, complaint_type in enumerate(complaint_types):
        keyboard.append([InlineKeyboardButton(complaint_type, callback_data=f"complaint:type:{i}")])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="menu:main")])
    
    await update.callback_query.message.reply_text(
        "📝 اختر نوع الشكوى أو الاستفسار:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def handle_complaint_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة اختيارات الشكوى"""
    query = update.callback_query
    await query.answer()
    
    data = query.data or ""
    if not data.startswith("complaint:"):
        return
    
    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""
    
    if action == "type":
        type_index = int(parts[2])
        complaint_types = [
            "مشكلة في الحجز",
            "مشكلة في الدفع", 
            "مشكلة في نقطة الركوب/النزول",
            "مشكلة في المواعيد",
            "مشكلة في التواصل",
            "مشكلة تقنية",
            "استفسار عام",
            "أخرى"
        ]
        
        context.user_data['complaint_type'] = complaint_types[type_index]
        context.user_data['complaint_step'] = 'waiting_details'
        
        await query.message.reply_text(
            f"📝 اخترت: {complaint_types[type_index]}\n\n"
            "الآن اكتب تفاصيل شكواك في رسالة نصية:\n"
            "(سيتم إرسالها للدعم الفني)"
        )
    
    elif action == "send":
        await send_complaint_to_support(update, context)


async def handle_complaint_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استقبال نص الشكوى"""
    if context.user_data.get('complaint_step') != 'waiting_details':
        return
    
    complaint_text = update.message.text.strip()
    complaint_type = context.user_data.get('complaint_type', 'غير محدد')
    
    if len(complaint_text) < 10:
        await update.message.reply_text("❌ الرسالة قصيرة جداً. يرجى كتابة تفاصيل أكثر.")
        return
    
    # تخزين الشكوى
    context.user_data['complaint_text'] = complaint_text
    
    keyboard = [
        [InlineKeyboardButton("✅ إرسال الشكوى", callback_data="complaint:send")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="menu:main")],
    ]
    
    preview_text = f"""📋 **مراجعة الشكوى**

📝 النوع: {complaint_type}
💬 التفاصيل: {complaint_text}

هل تريد إرسال هذه الشكوى للدعم؟"""
    
    await update.message.reply_text(
        preview_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def send_complaint_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال الشكوى للدعم"""
    try:
        telegram_user_id = update.effective_user.id
        passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
        
        complaint_type = context.user_data.get('complaint_type', 'غير محدد')
        complaint_text = context.user_data.get('complaint_text', '')
        
        # هنا يمكن إضافة منطق حفظ الشكوى في قاعدة البيانات
        # أو إرسالها إلى قناة الدعم أو إيميل
        
        # مسح بيانات الشكوى
        context.user_data.pop('complaint_step', None)
        context.user_data.pop('complaint_type', None)
        context.user_data.pop('complaint_text', None)
        
        await update.callback_query.message.reply_text(
            "✅ تم إرسال شكواك بنجاح!\n"
            "سيقوم الدعم الفني بالرد عليك في أقرب وقت ممكن.\n"
            f"📞 رقم تذكرة الشكوى: #{telegram_user_id}_{int(update.callback_query.message.date.timestamp())}"
        )
        
    except passenger.DoesNotExist:
        await update.callback_query.message.reply_text("❌ لم يتم العثور على حسابك.")
    except Exception as e:
        print(f"Error sending complaint: {e}")
        await update.callback_query.message.reply_text(f"❌ حدث خطأ: {str(e)}")


def _split_lines(text_value: str):
    if not text_value:
        return []
    lines = []
    for line in text_value.strip().splitlines():
        t = line.strip()
        if t:
            lines.append(t)
    return lines


async def _round_times_for(category_id: int, trip_type: str):
    def _fetch():
        qs = Round.objects.filter(category_id=category_id)
        if trip_type in ['ذهاب', 'عودة']:
            qs = qs.filter(trip_type=trip_type)

        times = set()
        for r in qs:
            if trip_type == 'ذهاب':
                if r.start_time:
                    times.add(r.start_time.strftime('%H:%M'))
            elif trip_type == 'عودة':
                if r.back_time:
                    times.add(r.back_time.strftime('%H:%M'))
            elif trip_type == 'ذهاب وعودة':
                if r.start_time:
                    times.add(r.start_time.strftime('%H:%M'))
                if r.back_time:
                    times.add(r.back_time.strftime('%H:%M'))
        return sorted(times)

    return await sync_to_async(_fetch)()


async def _cities_for_round_time(category_id: int, trip_type: str, time_str: str):
    def _fetch():
        rounds = Round.objects.filter(category_id=category_id, trip_type=trip_type)
        if trip_type == 'ذهاب':
            rounds = rounds.filter(start_time=time_str)
        elif trip_type == 'عودة':
            rounds = rounds.filter(back_time=time_str)

        cities = City.objects.filter(round__in=rounds, is_active=True).distinct().order_by('name')
        return [(c.id, c.name) for c in cities]

    return await sync_to_async(_fetch)()


async def _pickup_points_for_city(city_id: int):
    def _fetch():
        points = []
        for loc in PickupLocation.objects.filter(city_id=city_id, is_active=True):
            points.extend(_split_lines(loc.name))
        return points

    return await sync_to_async(_fetch)()


async def _dropoff_points_for(category_id: int, trip_type: str):
    def _fetch():
        points = []
        for loc in DropoffLocation.objects.filter(category_id=category_id, trip_type=trip_type, is_active=True):
            points.extend(_split_lines(loc.name))
        return points

    return await sync_to_async(_fetch)()


async def _choose_trip_date_keyboard(prefix: str = "fr:trip_date"):
    today = date.today()
    days = [today + timedelta(days=i) for i in range(0, 7)]
    keyboard = []
    row = []
    for i, d in enumerate(days, 1):
        row.append(InlineKeyboardButton(d.strftime('%Y-%m-%d'), callback_data=f"{prefix}:{d.strftime('%Y-%m-%d')}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
    return InlineKeyboardMarkup(keyboard)


async def handle_form_reservation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("fr:"):
        return

    if data == "fr:cancel":
        context.user_data.pop('form_reservation', None)
        await query.message.reply_text("✅ تم إلغاء طلب الحجز.")
        return

    state = context.user_data.get('form_reservation')
    if not state:
        await query.message.reply_text("❌ لا يوجد طلب حجز جاري. اكتب /reserve للبدء.")
        return

    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    category_id = state.get('category_id')
    trip_type = state.get('trip_type')

    if action == 'trip_type':
        chosen = ":".join(parts[2:])
        state['trip_type'] = chosen

        if chosen in ['ذهاب', 'عودة']:
            times = await _round_times_for(category_id, chosen)
            if not times:
                await query.message.reply_text("❌ لا توجد مواعيد متاحة حالياً.")
                return
            keyboard = [[InlineKeyboardButton(t, callback_data=f"fr:time:{chosen}:{t}")] for t in times]
            keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
            await query.message.reply_text("اختار المعاد:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if chosen == 'ذهاب وعودة':
            times = await _round_times_for(category_id, 'ذهاب وعودة')
            if not times:
                await query.message.reply_text("❌ لا توجد مواعيد متاحة حالياً.")
                return
            keyboard = [[InlineKeyboardButton(t, callback_data=f"fr:time_round:going:{t}")] for t in times]
            keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
            await query.message.reply_text("اختار معاد الذهاب:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

    if action == 'time':
        chosen_type = parts[2]
        chosen_time = parts[3]
        if chosen_type == 'ذهاب':
            state['going']['time'] = chosen_time
        else:
            state['return']['time'] = chosen_time

        cities = await _cities_for_round_time(category_id, chosen_type, chosen_time)
        if not cities:
            await query.message.reply_text("❌ لا توجد مدن متاحة لهذا المعاد.")
            return
        keyboard = [[InlineKeyboardButton(name, callback_data=f"fr:city:{chosen_type}:{cid}")] for cid, name in cities]
        keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
        await query.message.reply_text("اختار المدينة:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == 'time_round':
        leg = parts[2]
        chosen_time = parts[3]
        if leg == 'going':
            state['going']['time'] = chosen_time
            times = await _round_times_for(category_id, 'ذهاب وعودة')
            keyboard = [[InlineKeyboardButton(t, callback_data=f"fr:time_round:return:{t}")] for t in times]
            keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
            await query.message.reply_text("اختار معاد العودة:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if leg == 'return':
            state['return']['time'] = chosen_time
            cities = await _cities_for_round_time(category_id, 'ذهاب', state['going'].get('time'))
            if not cities:
                await query.message.reply_text("❌ لا توجد مدن متاحة لهذا المعاد.")
                return
            keyboard = [[InlineKeyboardButton(name, callback_data=f"fr:city:ذهاب:{cid}")] for cid, name in cities]
            keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
            await query.message.reply_text("اختار مدينة الذهاب:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

    if action == 'city':
        chosen_type = parts[2]
        city_id = int(parts[3])
        if chosen_type == 'ذهاب':
            state['going']['city_id'] = city_id
        else:
            state['return']['city_id'] = city_id

        pickup_points = await _pickup_points_for_city(city_id)
        if not pickup_points:
            await query.message.reply_text("❌ لا توجد نقاط ركوب لهذه المدينة.")
            return
        state[f'{chosen_type}_pickup_points'] = pickup_points
        keyboard = [[InlineKeyboardButton(p, callback_data=f"fr:pickup:{chosen_type}:{i}")] for i, p in enumerate(pickup_points[:40])]
        keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
        await query.message.reply_text("اختار نقطة الركوب:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == 'pickup':
        chosen_type = parts[2]
        idx = int(parts[3])
        points_key = f'{chosen_type}_pickup_points'
        points = state.get(points_key, [])
        if idx < 0 or idx >= len(points):
            await query.message.reply_text("❌ اختيار غير صالح.")
            return
        pickup = points[idx]
        if chosen_type == 'ذهاب':
            state['going']['pickup'] = pickup
        else:
            state['return']['pickup'] = pickup

        drop_type = 'ذهاب' if chosen_type == 'ذهاب' else 'عودة'
        drop_points = await _dropoff_points_for(category_id, drop_type)
        if not drop_points:
            await query.message.reply_text("❌ لا توجد نقاط نزول متاحة.")
            return
        state[f'{chosen_type}_dropoff_points'] = drop_points
        keyboard = [[InlineKeyboardButton(p, callback_data=f"fr:dropoff:{chosen_type}:{i}")] for i, p in enumerate(drop_points[:40])]
        keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
        await query.message.reply_text("اختار نقطة النزول:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == 'dropoff':
        chosen_type = parts[2]
        idx = int(parts[3])
        points_key = f'{chosen_type}_dropoff_points'
        points = state.get(points_key, [])
        if idx < 0 or idx >= len(points):
            await query.message.reply_text("❌ اختيار غير صالح.")
            return
        dropoff = points[idx]
        if chosen_type == 'ذهاب':
            state['going']['dropoff'] = dropoff
        else:
            state['return']['dropoff'] = dropoff

        if state.get('trip_type') == 'ذهاب وعودة' and chosen_type == 'ذهاب' and not state['return'].get('city_id'):
            cities = await _cities_for_round_time(category_id, 'عودة', state['return'].get('time'))
            if not cities:
                await query.message.reply_text("❌ لا توجد مدن متاحة لعودة لهذا المعاد.")
                return
            keyboard = [[InlineKeyboardButton(name, callback_data=f"fr:city:عودة:{cid}")] for cid, name in cities]
            keyboard.append([InlineKeyboardButton("إلغاء", callback_data="fr:cancel")])
            await query.message.reply_text("اختار مدينة العودة:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        await query.message.reply_text("اختار تاريخ الرحلة:", reply_markup=await _choose_trip_date_keyboard())
        return

    if action == 'trip_date':
        chosen_date = parts[2]
        state['trip_date'] = chosen_date

        keyboard = [
            [InlineKeyboardButton("أونلاين", callback_data="fr:pay:pending")],
            [InlineKeyboardButton("نقداً", callback_data="fr:pay:cash")],
            [InlineKeyboardButton("اشتراك", callback_data="fr:pay:subscription")],
            [InlineKeyboardButton("إلغاء", callback_data="fr:cancel")],
        ]
        await query.message.reply_text("اختار طريقة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == 'pay':
        pay_method = parts[2]
        state['payment_method'] = pay_method

        summary = "📋 ملخص الطلب\n"
        summary += f"🚌 نوع الرحلة: {state.get('trip_type')}\n"
        summary += f"📅 التاريخ: {state.get('trip_date')}\n"
        if state.get('trip_type') in ['ذهاب', 'ذهاب وعودة']:
            summary += f"⏰ معاد الذهاب: {state['going'].get('time')}\n"
            summary += f"🏙️ مدينة الذهاب: {state['going'].get('city_id')}\n"
            summary += f"📍 ركوب الذهاب: {state['going'].get('pickup')}\n"
            summary += f"📍 نزول الذهاب: {state['going'].get('dropoff')}\n"
        if state.get('trip_type') in ['عودة', 'ذهاب وعودة']:
            summary += f"⏰ معاد العودة: {state['return'].get('time')}\n"
            summary += f"🏙️ مدينة العودة: {state['return'].get('city_id')}\n"
            summary += f"📍 ركوب العودة: {state['return'].get('pickup')}\n"
            summary += f"📍 نزول العودة: {state['return'].get('dropoff')}\n"
        summary += f"💳 الدفع: {pay_method}\n"

        keyboard = [
            [InlineKeyboardButton("✅ تأكيد", callback_data="fr:confirm")],
            [InlineKeyboardButton("إلغاء", callback_data="fr:cancel")],
        ]
        await query.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if action == 'confirm':
        try:
            telegram_user_id = query.from_user.id
            passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
            user_obj = await sync_to_async(lambda: getattr(passenger_obj, 'user', None))()
            category = await sync_to_async(Category.objects.get)(id=category_id)

            trip_type_value = state.get('trip_type')
            if trip_type_value in ['ذهاب', 'عودة']:
                base_price = await sync_to_async(lambda: category.one_way_price)()
            elif trip_type_value == 'ذهاب وعودة':
                base_price = await sync_to_async(lambda: category.round_trip_price)()
            else:
                base_price = Decimal('0.00')

            final_price = (Decimal(base_price) * Decimal('1.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            allow_cash = await sync_to_async(lambda: getattr(category, 'allow_cash_payment', False))()
            remaining_rides = await sync_to_async(lambda: getattr(passenger_obj, 'remaining_rides', 0))()

            payment_method = state.get('payment_method')
            if payment_method == 'cash' and not allow_cash:
                await query.message.reply_text("❌ هذه الجامعة لا تدعم الدفع نقداً.")
                return

            if payment_method == 'subscription':
                needed_rides = 2 if trip_type_value == 'ذهاب وعودة' else 1
                if remaining_rides < needed_rides:
                    await query.message.reply_text("❌ لا يوجد رصيد اشتراك كافي.")
                    return

            merchant_order_id = str(uuid.uuid4())
            trip_date_str = state.get('trip_date')

            def _create_reservations():
                created_ids = []

                common = {
                    'category': category,
                    'user': user_obj,
                    'passenger': passenger_obj,
                    'student_name': passenger_obj.name,
                    'trip_date': trip_date_str,
                    'phone_number': passenger_obj.phone_number,
                    'university_code': passenger_obj.university_code,
                    'paid_amount': Decimal('0.00'),
                }

                if trip_type_value in ['ذهاب', 'ذهاب وعودة']:
                    created = FormReservation.objects.create(
                        **common,
                        trip_type='ذهاب',
                        arrival_time=state['going'].get('time') or None,
                        going_city_id=state['going'].get('city_id'),
                        going_pickup_location=state['going'].get('pickup'),
                        going_dropoff_location=state['going'].get('dropoff'),
                        pickup_location=state['going'].get('pickup'),
                        total_price=Decimal('0.00') if payment_method == 'subscription' else final_price,
                        status='subscription' if payment_method == 'subscription' else payment_method,
                        merchant_order_id=merchant_order_id if payment_method == 'pending' else None,
                    )
                    created_ids.append(created.id)

                if trip_type_value in ['عودة', 'ذهاب وعودة']:
                    created = FormReservation.objects.create(
                        **common,
                        trip_type='عودة',
                        back_time=state['return'].get('time') or None,
                        return_city_id=state['return'].get('city_id'),
                        return_pickup_location=state['return'].get('pickup'),
                        return_dropoff_location=state['return'].get('dropoff'),
                        pickup_location=state['return'].get('pickup'),
                        total_price=Decimal('0.00') if payment_method == 'subscription' else final_price,
                        status='subscription' if payment_method == 'subscription' else payment_method,
                        merchant_order_id=merchant_order_id if payment_method == 'pending' else None,
                    )
                    created_ids.append(created.id)

                return created_ids

            created_ids = await sync_to_async(_create_reservations)()
            context.user_data.pop('form_reservation', None)

            if payment_method == 'pending':
                merchant_id = settings.KASHIER_ACCOUNT_KEY
                mode = settings.KASHIER_MODE
                amount_str = str(int(final_price))
                currency = 'EGP'

                def generateKashierOrderHash(order):
                    mid = merchant_id
                    amount = order['amount']
                    currency_v = order['currency']
                    order_id = order['merchantOrderId']
                    full_secret = settings.KASHIER_API_KEY
                    secret = full_secret.split('$')[-1]
                    path = f"/?payment={mid}.{order_id}.{amount}.{currency_v}"
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
                    'merchantRedirect': 'https://example.com/form_payment_success',
                    'failureRedirect': 'https://example.com/form_payment_failed',
                    'redirectMethod': 'get',
                    'hash': hash_signature,
                    'mode': mode,
                    'display': 'ar',
                }
                checkout_url = f"https://payments.kashier.io/?{urlencode(params)}"
                await query.message.reply_text(
                    "✅ تم تسجيل طلبك (في انتظار الدفع).\n"
                    f"🆔 رقم الطلب/الطلبات: {', '.join(map(str, created_ids))}\n"
                    f"🔗 رابط الدفع: {checkout_url}"
                )
                return

            await query.message.reply_text(
                "✅ تم تسجيل طلب الحجز بنجاح.\n"
                f"🆔 رقم الطلب/الطلبات: {', '.join(map(str, created_ids))}\n"
                "⏳ في انتظار تسكين الأدمن وإرسال رسالة التأكيد."
            )
            return

        except Exception as e:
            print(f"Error confirming form reservation: {e}")
            await query.message.reply_text(f"❌ حدث خطأ: {str(e)}")
            return


    await query.message.reply_text("❌ اختيار غير معروف. اكتب /reserve للبدء.")


async def handle_trip_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        telegram_user_id = query.from_user.id
        data = query.data or ""
        if not data.startswith("book_trip:"):
            return

        trip_id_str = data.split(":", 1)[1]
        trip_id = int(trip_id_str)

        passenger_obj = await sync_to_async(passenger.objects.get)(telegram_id=telegram_user_id)
        trip = await sync_to_async(Trip.objects.get)(id=trip_id)

        passenger_category = await sync_to_async(lambda: passenger_obj.category)()
        passenger_name = await sync_to_async(lambda: passenger_obj.name)()
        university_code = await sync_to_async(lambda: passenger_obj.university_code)()
        pickup_point = await sync_to_async(lambda: passenger_obj.last_selected_route)()

        if not pickup_point:
            await query.message.reply_text(
                "❌ لازم تحدد نقطة الركوب أولاً.\n"
                "ابعت اسم نقطة الركوب في رسالة (مثال: كلية تجارة / بوابة الجامعة) ثم أعد المحاولة."
            )
            return

        trip_date = await sync_to_async(lambda: trip.date)()
        start_time = await sync_to_async(lambda: trip.start_time)()
        back_time = await sync_to_async(lambda: trip.back_time)()
        trip_type_value = await sync_to_async(lambda: trip.trip_type)()

        if trip_type_value == 'one_way':
            form_trip_type = 'ذهاب'
            total_price = await sync_to_async(lambda: trip.one_way_price)()
        elif trip_type_value == 'return':
            form_trip_type = 'عودة'
            total_price = await sync_to_async(lambda: trip.return_price)()
        elif trip_type_value == 'round_trip':
            form_trip_type = 'ذهاب وعودة'
            total_price = await sync_to_async(lambda: trip.round_trip_price)()
        elif trip_type_value == 'round_differentdays':
            form_trip_type = 'ذهاب وعودة'
            dep_price = await sync_to_async(lambda: trip.departure_seat_price)()
            ret_price = await sync_to_async(lambda: trip.return_seat_price)()
            total_price = (dep_price or 0) + (ret_price or 0)
        else:
            form_trip_type = 'ذهاب'
            total_price = 0

        def _create_reservation():
            res = FormReservation.objects.create(
                university_code=university_code,
                category=passenger_category,
                passenger=passenger_obj,
                trip=trip,
                trip_date=trip_date,
                arrival_time=start_time,
                back_time=back_time,
                trip_type=form_trip_type,
                status='pending',
                total_price=total_price or 0,
                paid_amount=0,
                student_name=passenger_name or "",
                pickup_location=pickup_point,
                going_pickup_location=pickup_point,
            )
            return res.id

        reservation_id = await sync_to_async(_create_reservation)()

        await query.message.reply_text(
            "✅ تم تسجيل طلب الحجز بنجاح.\n"
            f"🆔 رقم الطلب: {reservation_id}\n"
            f"📍 نقطة الركوب: {pickup_point or 'N/A'}\n"
            "⏳ في انتظار تأكيد/تسكين الأدمن."
        )

    except passenger.DoesNotExist:
        await update.effective_message.reply_text("❌ لم يتم العثور على حسابك. أرسل كود الجامعة أولاً.")
    except Trip.DoesNotExist:
        await update.effective_message.reply_text("❌ الرحلة غير موجودة.")
    except Exception as e:
        print(f"Error in handle_trip_booking_callback: {e}")
        await update.effective_message.reply_text(f"❌ حدث خطأ: {str(e)}")

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
        app.add_handler(CommandHandler("reserve", start_form_reservation))
        app.add_handler(CommandHandler("cancelreserve", cancel_form_reservation))
        
        # Callback handlers
        app.add_handler(CallbackQueryHandler(handle_main_menu_callback, pattern=r"^menu:.*"))
        app.add_handler(CallbackQueryHandler(handle_edit_booking_callback, pattern=r"^edit:.*"))
        app.add_handler(CallbackQueryHandler(handle_complaint_callback, pattern=r"^complaint:.*"))
        app.add_handler(CallbackQueryHandler(handle_trip_booking_callback, pattern=r"^book_trip:\d+$"))
        app.add_handler(CallbackQueryHandler(handle_form_reservation_callback, pattern=r"^fr:.*"))
        
        # معالج الرسائل النصية (لكود الجامعة + الشكاوي)
        from telegram.ext import MessageHandler, filters
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_university_code))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_complaint_text))
        
        print("Bot handlers registered successfully...")
        print("Bot is running...")
        app.run_polling()
        
    except Exception as e:
        print(f"Error starting bot: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

