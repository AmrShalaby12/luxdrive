from django import template
import base64

register = template.Library()

@register.filter
def base64encode(value):
    """Encode a value into Base64."""
    if isinstance(value, bytes):
        # إذا كان `value` هو كائن bytes، قم بتشفيره مباشرة
        return base64.b64encode(value).decode('utf-8')
    elif isinstance(value, str):
        # إذا كان `value` هو نص (string)، قم بتحويله إلى bytes أولاً
        return base64.b64encode(value.encode('utf-8')).decode('utf-8')
    else:
        # في حال كان النوع غير متوقع، قم بإرجاع النص فارغ
        return ''
