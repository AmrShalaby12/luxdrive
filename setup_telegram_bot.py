#!/usr/bin/env python3
"""
Setup script for Telegram Bot configuration
Run this script to configure the bot and set up webhook
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/home/nixos/allen_bus_project')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Main_Bus_Management.settings')
django.setup()

from Anaconda_bus_APP.models import TelegramBotToken
from telegram_bot.utils import setup_bot_webhook, get_bot_info

def setup_telegram_bot():
    """Setup Telegram bot configuration"""
    
    print("🤖 إعداد بوت Telegram...")
    
    # Bot configuration
    bot_username = "AllenTravelAi_bot"
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # Webhook URL (update this with your actual domain)
    webhook_url = "https://allen.allentravels.com/telegram/webhook/"
    
    try:
        # Check if bot configuration already exists
        existing_bot = TelegramBotToken.objects.filter(bot_username=bot_username).first()
        
        if existing_bot:
            print(f"📝 تحديث إعدادات البوت الموجود: @{bot_username}")
            existing_bot.bot_token = bot_token
            existing_bot.webhook_url = webhook_url
            existing_bot.is_active = True
            existing_bot.save()
            bot_config = existing_bot
        else:
            print(f"➕ إنشاء إعدادات بوت جديدة: @{bot_username}")
            bot_config = TelegramBotToken.objects.create(
                bot_username=bot_username,
                bot_token=bot_token,
                webhook_url=webhook_url,
                is_active=True
            )
        
        # Test bot connection
        print("🔍 اختبار اتصال البوت...")
        bot_info = get_bot_info(bot_token)
        
        if bot_info and bot_info.get('ok'):
            bot_data = bot_info['result']
            print(f"✅ البوت متصل بنجاح!")
            print(f"   اسم البوت: {bot_data.get('first_name')}")
            print(f"   يوزرنيم: @{bot_data.get('username')}")
            print(f"   يمكنه استقبال الرسائل: {bot_data.get('can_read_all_group_messages', False)}")
        else:
            print(f"❌ فشل الاتصال بالبوت: {bot_info.get('description', 'Unknown error')}")
            return False
        
        # Set up webhook
        print("🔗 إعداد Webhook...")
        webhook_result = setup_bot_webhook(bot_config, webhook_url)
        
        if webhook_result and webhook_result.get('ok'):
            print(f"✅ تم إعداد Webhook بنجاح!")
            print(f"   Webhook URL: {webhook_url}")
            result_data = webhook_result.get('result', {})
            if isinstance(result_data, dict):
                print(f"   عدد التحديثات المعلقة: {result_data.get('pending_update_count', 0)}")
        else:
            print(f"❌ فشل إعداد Webhook: {webhook_result.get('description', 'Unknown error') if isinstance(webhook_result, dict) else 'Unknown error'}")
            return False
        
        print("\n🎉 تم إعداد البوت بنجاح!")
        print(f"📱 رابط البوت: https://t.me/{bot_username}")
        print(f"🔗 Webhook: {webhook_url}")
        
        # Test link generation
        print("\n🧪 اختبار توليد الرابط...")
        from telegram_bot.utils import generate_telegram_link
        
        # Find a sample booking or create a test one
        from Anaconda_bus_APP.models import Booking
        sample_booking = Booking.objects.first()
        
        if sample_booking:
            test_link = generate_telegram_link(sample_booking.id)
            if test_link:
                print(f"✅ تم توليد رابط اختبار:")
                print(f"   {test_link}")
            else:
                print("❌ فشل توليد الرابط")
        else:
            print("ℹ️  لا توجد حجوزات لاختبار توليد الرابط")
        
        return True
        
    except Exception as e:
        print(f"❌ حدث خطأ: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = setup_telegram_bot()
    if success:
        print("\n✨ اكتمل الإعداد بنجاح!")
        sys.exit(0)
    else:
        print("\n💥 فشل الإعداد!")
        sys.exit(1)
