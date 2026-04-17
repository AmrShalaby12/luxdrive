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