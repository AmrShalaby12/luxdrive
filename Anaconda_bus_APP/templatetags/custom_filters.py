from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    try:
        # تأكد أن القيم أرقام
        value = int(value)
        arg = int(arg)
        return value * arg
    except (ValueError, TypeError):
        return 0  # إعادة 0 إذا كانت القيم غير صالحة
# from django import template

# register = template.Library()

# @register.filter
# def multiply(value, arg):
#     return float(value) * float(arg)

# @register.filter
# def add_percentage(value, percentage):
#     return round(float(value) * (1 + float(percentage) / 100), 2)
