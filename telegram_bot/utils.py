import secrets
from urllib.parse import quote
from Anaconda_bus_APP.models import Booking, TelegramBotToken

def generate_telegram_link(booking_id):
    """Generate Telegram bot link for booking confirmation"""
    try:
        booking = Booking.objects.get(id=booking_id)
        
        # Generate token if not exists
        if not booking.telegram_token:
            booking.telegram_token = secrets.token_urlsafe(16)
            booking.save()
        
        # Get active bot configuration
        bot_config = TelegramBotToken.objects.filter(is_active=True).first()
        if not bot_config:
            return None
        
        # Generate the link
        link = f"https://t.me/{bot_config.bot_username}?start=booking_{booking_id}_{booking.telegram_token}"
        return link
        
    except Booking.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error generating Telegram link: {str(e)}")
        return None

def setup_bot_webhook(bot_config, webhook_url):
    """Set up Telegram bot webhook"""
    try:
        import requests
        api_url = f"https://api.telegram.org/bot{bot_config.bot_token}/setWebhook"
        
        data = {
            'url': webhook_url,
            'allowed_updates': ['message', 'callback_query']
        }
        
        response = requests.post(api_url, json=data)
        return response.json()
        
    except Exception as e:
        print(f"Error setting up webhook: {str(e)}")
        return None

def get_bot_info(bot_token):
    """Get bot information"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url)
        return response.json()
        
    except Exception as e:
        print(f"Error getting bot info: {str(e)}")
        return None
