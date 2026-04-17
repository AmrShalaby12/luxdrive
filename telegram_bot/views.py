import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from Anaconda_bus_APP.models import Booking, TelegramBotToken

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """Handle incoming Telegram webhook updates"""
    try:
        data = json.loads(request.body)
        
        # Get bot configuration
        bot_config = TelegramBotToken.objects.filter(is_active=True).first()
        if not bot_config:
            logger.error("No active bot configuration found")
            return HttpResponse("No bot configuration", status=400)
        
        # Create application
        application = Application.builder().token(bot_config.bot_token).build()
        
        # Create Update object from webhook data
        update = Update.de_json(data, application.bot)
        
        # Handle the update
        if update.message and update.message.text:
            return handle_message(update, bot_config)
        elif update.callback_query:
            return handle_callback_query(update, bot_config)
        
        return HttpResponse("OK")
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON received")
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse("Error", status=500)

def handle_message(update, bot_config):
    """Handle incoming messages"""
    try:
        message_text = update.message.text
        chat_id = update.message.chat.id
        
        if message_text.startswith('/start'):
            # Extract booking info from /start command
            parts = message_text.split()
            if len(parts) >= 2:
                booking_info = parts[1]
                if booking_info.startswith('booking_'):
                    return process_booking_request(booking_info, chat_id, bot_config)
            
            # Send welcome message if no booking info
            send_message(chat_id, "مرحباً! يرجى استخدام رابط الحجز الصحيح.", bot_config)
        
        return HttpResponse("OK")
        
    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")
        return HttpResponse("Error", status=500)

def process_booking_request(booking_info, chat_id, bot_config):
    """Process booking verification request"""
    try:
        # Extract booking_id and token from booking_INFO
        # Format: booking_<booking_id>_<token>
        parts = booking_info.split('_')
        if len(parts) != 3:
            send_message(chat_id, "رابط الحجز غير صحيح.", bot_config)
            return HttpResponse("OK")
        
        booking_id = parts[1]
        token = parts[2]
        
        # Verify booking exists and token matches
        booking = get_object_or_404(Booking, id=booking_id, telegram_token=token)
        
        # Check booking status
        if booking.status == 'cancelled':
            send_message(chat_id, "هذا الحجز تم إلغاؤه بالفعل.", bot_config)
            return HttpResponse("OK")
        
        if booking.status == 'confirmed':
            send_message(chat_id, "هذا الحجز تم تأكيده بالفعل.", bot_config)
            return HttpResponse("OK")
        
        # Display booking information
        booking_info_text = format_booking_info(booking)
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد الحجز", callback_data=f"confirm_{booking.id}_{token}"),
                InlineKeyboardButton("❌ إلغاء الحجز", callback_data=f"cancel_{booking.id}_{token}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        send_message_with_keyboard(chat_id, booking_info_text, reply_markup, bot_config)
        
        return HttpResponse("OK")
        
    except Booking.DoesNotExist:
        send_message(chat_id, "الحجز غير موجود أو الرابط غير صحيح.", bot_config)
        return HttpResponse("OK")
    except Exception as e:
        logger.error(f"Booking processing error: {str(e)}")
        send_message(chat_id, "حدث خطأ أثناء معالجة الحجز.", bot_config)
        return HttpResponse("OK")

def handle_callback_query(update, bot_config):
    """Handle button callback queries"""
    try:
        callback_query = update.callback_query
        chat_id = callback_query.message.chat.id
        callback_data = callback_query.data
        
        # Parse callback data
        parts = callback_data.split('_')
        if len(parts) != 3:
            send_message(chat_id, "بيانات غير صحيحة.", bot_config)
            return HttpResponse("OK")
        
        action, booking_id, token = parts
        
        # Verify booking
        booking = get_object_or_404(Booking, id=booking_id, telegram_token=token)
        
        if action == 'confirm':
            if booking.status == 'cancelled':
                answer_callback(callback_query, "لا يمكن تأكيد حجز ملغي.", show_alert=True)
                return HttpResponse("OK")
            
            if booking.status == 'confirmed':
                answer_callback(callback_query, "الحجز مؤكد بالفعل.", show_alert=True)
                return HttpResponse("OK")
            
            # Confirm booking
            booking.status = 'confirmed'
            booking.save()
            
            answer_callback(callback_query, "تم تأكيد الحجز بنجاح!")
            send_message(chat_id, f"✅ تم تأكيد حجز رقم {booking.id} بنجاح!\n\nشكراً لاستخدامك خدمتنا.", bot_config)
            
        elif action == 'cancel':
            if booking.status == 'cancelled':
                answer_callback(callback_query, "الحجز ملغي بالفعل.", show_alert=True)
                return HttpResponse("OK")
            
            if booking.status == 'confirmed':
                answer_callback(callback_query, "لا يمكن إلغاء حجز مؤكد.", show_alert=True)
                return HttpResponse("OK")
            
            # Cancel booking
            booking.status = 'cancelled'
            booking.save()
            
            answer_callback(callback_query, "تم إلغاء الحجز بنجاح!")
            send_message(chat_id, f"❌ تم إلغاء حجز رقم {booking.id} بنجاح.", bot_config)
        
        return HttpResponse("OK")
        
    except Booking.DoesNotExist:
        answer_callback(callback_query, "الحجز غير موجود.", show_alert=True)
        return HttpResponse("OK")
    except Exception as e:
        logger.error(f"Callback handling error: {str(e)}")
        answer_callback(callback_query, "حدث خطأ.", show_alert=True)
        return HttpResponse("OK")

def format_booking_info(booking):
    """Format booking information for display"""
    seats = ", ".join([f"كرسي {seat.seat_number}" for seat in booking.seats_reserved.all()])
    
    info = f"📋 **معلومات الحجز**\n\n"
    info += f"🔢 رقم الحجز: {booking.id}\n"
    info += f"👤 اسم الراكب: {booking.passenger.name}\n"
    
    if booking.Trip:
        info += f"🚌 الرحلة: {booking.Trip.route}\n"
    
    info += f"📅 التاريخ: {booking.booking_date.strftime('%Y-%m-%d %H:%M')}\n"
    info += f"💺 المقاعد: {seats}\n"
    info += f"📊 الحالة الحالية: {booking.get_status_display()}\n"
    
    return info

def send_message(chat_id, text, bot_config):
    """Send a message to Telegram chat"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_config.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        requests.post(url, json=data)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")

def send_message_with_keyboard(chat_id, text, reply_markup, bot_config):
    """Send a message with inline keyboard"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_config.bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'reply_markup': reply_markup.to_json()
        }
        requests.post(url, json=data)
    except Exception as e:
        logger.error(f"Error sending message with keyboard: {str(e)}")

def answer_callback(callback_query, text, show_alert=False):
    """Answer callback query"""
    try:
        callback_query.answer(text=text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"Error answering callback: {str(e)}")
