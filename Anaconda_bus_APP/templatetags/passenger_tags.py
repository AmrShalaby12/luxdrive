from django import template
from ..models import passenger  # تأكد من استخدام المسار الصحيح لنموذج passenger

register = template.Library()

@register.simple_tag(takes_context=True)
def get_passenger(context):
    user = context['request'].user
    if user.is_authenticated:
        try:
            return passenger.objects.get(user=user)
        except passenger.DoesNotExist:
            return None
    return None
