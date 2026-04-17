from django import forms
from .models import Booking  # استبدل Booking باسم نموذج الحجز الخاص بك
from .models import WeeklySchedule, WeeklyBooking

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking  # استبدل Booking بالنموذج المناسب للحجز
        fields = ['seats_reserved', 'payment_method', 'transfer_message', 'trip_type']  # أضف الحقول المناسبة هنا
        labels = {
            'seats_reserved': 'Seat Number',
            'payment_method': 'Payment Method',
            'transfer_message': 'Transfer Confirmation Message',
        }
        widgets = {
            'seats_reserved': forms.TextInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'transfer_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),


        }
from django import forms
from django.contrib.auth.models import User
from .models import passenger, Category  # استيراد الفئات اللازمة
from datetime import timedelta
from django import forms
from django.contrib.auth.models import User
from .models import passenger, Category

from django import forms
from django.contrib.auth.models import User
from .models import Category, passenger
from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from .models import passenger, Category

from django import forms
from django.core.validators import RegexValidator
from django.contrib.auth.models import User
from .models import passenger, Category

class SignupForm(forms.ModelForm):
    USER_TYPE_CHOICES = [
        ('student', 'طالب جامعي'),
        ('regular', 'مستخدم عادي'),
    ]

    username = forms.RegexField(
        regex=r'^[\w.@+-]+$',
        max_length=150,
        label="اسم المستخدم",
        error_messages={'invalid': "يمكنك استخدام الحروف الإنجليزية والأرقام والرموز @/./+/-/_ فقط."}
    )


    user_type = forms.ChoiceField(
        choices=USER_TYPE_CHOICES,
        label="نوع المستخدم",
        widget=forms.RadioSelect(attrs={'class': 'user-type-buttons'})
    )

    university_id = forms.CharField(max_length=100, label="كود الجامعة", required=False)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), label="الجامعة", required=False)
    phone_number = forms.CharField(max_length=20, label="رقم الهاتف")
    parent_number = forms.CharField(max_length=20, label=" رقم ولي الامر", required=False)  # ⬅ اجعله غير مطلوب

    class Meta:
        model = User
        fields = ['username', 'password', 'user_type', 'university_id', 'phone_number', 'parent_number', 'category']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_phone_number(self):
        number = self.cleaned_data.get("phone_number", "")
        if number and not number.startswith('+20'):
            number = '+20' + number.lstrip('0')
        return number
    def clean_parent_number(self):
        """ التحقق من أن رقم ولي الأمر مطلوب فقط للطلاب الجامعيين + إضافة +20 """
        user_type = self.cleaned_data.get("user_type")
        parent_number = self.cleaned_data.get("parent_number", "")

        if user_type == "student":
            if not parent_number:
                raise forms.ValidationError("رقم ولي الأمر مطلوب للطلاب الجامعيين.")
            if not parent_number.startswith('+20'):
                parent_number = '+20' + parent_number.lstrip('0')

        return parent_number


    def clean_university_id(self):
        """ التحقق من أن كود الجامعة غير مكرر إذا كان المستخدم طالبًا """
        university_id = self.cleaned_data.get("university_id")
        user_type = self.cleaned_data.get("user_type")

        if user_type == "student" and university_id:
            if passenger.objects.filter(university_code=university_id).exists():
                raise forms.ValidationError("كود الجامعه مسجل قبل كده، تأكد من إدخال الكود الخاص بك.")

        return university_id

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user_type = self.cleaned_data['user_type']
        university_id = self.cleaned_data['university_id'] if user_type == 'student' else None
        category = self.cleaned_data['category'] if user_type == 'student' else Category.objects.get(name="رحلة")
        phone_number = self.cleaned_data['phone_number']
        parent_number = self.cleaned_data['parent_number'] if user_type == 'student' else None  # ⬅ اجعل الحقل None للمستخدم العادي

        if commit:
            user.save()
            passenger.objects.create(
                user=user,
                name=user.username,
                university_code=university_id,  # None إذا كان مستخدم عادي
                phone_number=phone_number,
                subscription_duration=0,
                category=category,  # الجامعة أو "رحلة" إذا كان مستخدم عادي
                user_type=user_type,  # ✅ إضافة نوع المستخدم هنا
                parent_number=parent_number  # ⬅ سيتم تخزين None إذا كان مستخدم عادي
            )
        return user


#
# class SignupForm(forms.ModelForm):
#     university_code = forms.CharField(max_length=20, label="الكود الجامعي")
#     category = forms.ModelChoiceField(queryset=Category.objects.all(), label="الجامعة")
#     student_name = forms.CharField(max_length=64, label="اسم الطالب")

#     class Meta:
#         model = User
#         fields = ['username', 'password']
#         widgets = {
#             'password': forms.PasswordInput(),
#         }

#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.set_password(self.cleaned_data['password'])  # تعيين كلمة المرور

#         if commit:
#             user.save()
#             # إنشاء عنصر جديد في passenger وربطه بالمستخدم
#             passenger.objects.create(
#                 user=user,
#                 university_code=self.cleaned_data['university_code'],
#                 category=self.cleaned_data['category'],
#                 name=self.cleaned_data['student_name']
#             )
#         return user
from django import forms
from django.contrib.auth.forms import AuthenticationForm

from django import forms
from django.contrib.auth.models import User

# فورم مخصص لتسجيل الدخول
class CustomUserLoginForm(forms.Form):
    username = forms.CharField(
        label='اسم المستخدم',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'اسم المستخدم'})
    )
    password = forms.CharField(
        label='كلمة المرور',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'كلمة المرور'})
    )

# فورم مخصص لتسجيل الحساب الجديد
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class CustomUserSignupForm(UserCreationForm):
    name = forms.CharField(
        label='الاسم',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'الاسم الكامل'})
    )
    phone_number = forms.CharField(
        label='رقم الهاتف',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'رقم الهاتف'})
    )

    class Meta:
        model = User
        fields = ['username', 'phone_number', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('name')
        user.phone_number = self.cleaned_data.get('phone_number')  # Assuming a custom field for phone_number
        if commit:
            user.save()
        return user
from django import forms
from .models import SubscriptionBooking

from django import forms
from .models import SubscriptionBooking
from django import forms
from django import forms

class WhatsAppMessageForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea, label="الرسالة")
    passenger_ids = forms.MultipleChoiceField(
        choices=[],  # سيتم تعيين القيم في الـ view
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

class SubscriptionBookingForm(forms.ModelForm):
    class Meta:
        model = SubscriptionBooking
        fields = ['transaction_code', 'account_info', 'payment_proof']
        widgets = {
            'transaction_code': forms.TextInput(attrs={'placeholder': 'أدخل كود المعاملة'}),
            'account_info': forms.TextInput(attrs={'placeholder': 'اسم أو رقم الحساب المحول منه'}),
            'payment_proof': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'transaction_code': 'كود المعاملة',
            'account_info': 'اسم أو رقم الحساب المحول منه',
            'payment_proof': 'صورة التحويل',
        }
from django import forms
from .models import CarBooking

class CarBookingForm(forms.ModelForm):
    class Meta:
        model = CarBooking
        fields = ['customer_name', 'phone_number', 'go_date', 'return_date','go_time','back_time'] 
        widgets = {
            'go_date': forms.DateInput(attrs={'type': 'date'}),
            'return_date': forms.DateInput(attrs={'type': 'date'}),
            'go_time': forms.TimeInput(attrs={'type': 'time'}),  # ✅ هنا
            'back_time': forms.TimeInput(attrs={'type': 'time'}),  # ✅ هنا

        }
from .models import FormReservation, PickupLocation
# forms.py

from django import forms
from .models import FormReservation, PickupLocation, City
from django import forms
from .models import FormReservation, PickupLocation

from django import forms
from .models import FormReservation, PickupLocation
import datetime
from django import forms
from .models import FormReservation, PickupLocation
import datetime
import datetime
from django import forms
from .models import FormReservation, Trip, PickupLocation

import datetime
from django import forms
from .models import FormReservation, Trip, PickupLocation
from django import forms
from .models import FormReservation, Round, PickupLocation, City
import datetime
from django import forms
import datetime
from .models import FormReservation, Round, PickupLocation
from django import forms
from .models import FormReservation
import datetime
from django import forms
from .models import FormReservation
import datetime
# forms.py (لا تغييرات هنا)

from django import forms
import datetime
from .models import FormReservation, Round

from django import forms
from .models import FormReservation, Round
import datetime


from .models import FormReservation, Seat


class FormReservationForm(forms.ModelForm):
    price = forms.DecimalField(widget=forms.HiddenInput(), required=False)
    
    trip_date = forms.DateField(
        label="تاريخ الرحلة",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'min': datetime.date.today().strftime('%Y-%m-%d')
        })
    )

    arrival_time = forms.ChoiceField(
        label="وقت الذهاب",
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    back_time = forms.ChoiceField(
        label="وقت العودة",
        choices=[],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = FormReservation
        fields = [
            "trip_date", "trip_type", "arrival_time", "back_time", 
            "price", "phone_number", "university_code"
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.category = kwargs.pop("category", None)
        super().__init__(*args, **kwargs)

        # تحديث خيارات الأوقات
        rounds = Round.objects.filter(category=self.category)
        
        # أوقات الذهاب
        arrival_choices = [
            (r.start_time.strftime('%H:%M:%S'), f"{r.name} - {r.start_time.strftime('%I:%M %p')}")
            for r in rounds if r.start_time
        ]
        self.fields["arrival_time"].choices = [('', '--- اختر وقت الذهاب ---')] + arrival_choices

        # أوقات العودة
        back_choices = [
            (r.back_time.strftime('%H:%M:%S'), f"{r.name} - {r.back_time.strftime('%I:%M %p')}")
            for r in rounds if r.back_time
        ]
        self.fields["back_time"].choices = [('', '--- اختر وقت العودة ---')] + back_choices

    def clean(self):
        cleaned_data = super().clean()
        trip_type = cleaned_data.get("trip_type")
        arrival_time = cleaned_data.get("arrival_time")
        back_time = cleaned_data.get("back_time")

        if trip_type == "ذهاب":
            if not arrival_time:
                self.add_error('arrival_time', 'يجب تحديد وقت الذهاب لرحلات الذهاب')
            cleaned_data["back_time"] = None

        elif trip_type == "عودة":
            if not back_time:
                self.add_error('back_time', 'يجب تحديد وقت العودة لرحلات العودة')
            cleaned_data["arrival_time"] = None

        elif trip_type == "ذهاب وعودة":
            if not arrival_time:
                self.add_error('arrival_time', 'يجب تحديد وقت الذهاب')
            if not back_time:
                self.add_error('back_time', 'يجب تحديد وقت العودة')

        return cleaned_data


from .models import FormReservation, Seat

class FormReservationAdminForm(forms.ModelForm):
    class Meta:
        model = FormReservation
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.trip:
            trip = self.instance.trip
            reserved_seats = FormReservation.objects.filter(trip=trip).exclude(seat__isnull=True).values_list('seat_id', flat=True)
            available_seats = Seat.objects.filter(bus=trip.bus, is_reserved=False).exclude(id__in=reserved_seats)

            self.fields['seat'].queryset = available_seats
from django import forms

class SuggestionApplyForm(forms.Form):
    apply_suggestion = forms.BooleanField(
        label='تطبيق الاقتراح',
        required=False,
        initial=True
    )
    suggestion_value = forms.CharField(
        label='الاقتراح',
        widget=forms.TextInput(attrs={'readonly': 'readonly', 'style': 'width: 300px;'}),
        required=False
    )

class QuickAssignForm(forms.Form):
    trip = forms.ModelChoiceField(
        queryset=Trip.objects.none(),
        label='اختر الرحلة'
    )
    reservations = forms.ModelMultipleChoiceField(
        queryset=FormReservation.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        label='الحجوزات المحددة'
    )
    
    
# Anaconda_bus_APP/forms.py

from django import forms
from .models import Trip, Category, Bus

class RenewTripForm(forms.Form):
    # حقول لتعديل بيانات الرحلة الأساسية
    trip_name = forms.CharField(label="اسم الرحلة الجديد", max_length=100, required=True)
    start_time = forms.TimeField(label="وقت الانطلاق الجديد", widget=forms.TimeInput(format='%H:%M'))
    
    # حقول لاختيار الحافلة الجديدة
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        label="اختر الجامعة (لتصفية الحافلات)",
        required=True,
        widget=forms.Select(attrs={'id': 'id_category_filter'}) # ID مهم لـ JavaScript
    )
    bus = forms.ModelChoiceField(
        queryset=Bus.objects.none(), # نبدأ بدون أي حافلات
        label="اختر الحافلة الجديدة",
        required=True,
        widget=forms.Select(attrs={'id': 'id_bus_select'}) # ID مهم لـ JavaScript
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إذا تم اختيار جامعة بالفعل، نقوم بفلترة الحافلات
        if 'category' in self.data:
            try:
                category_id = int(self.data.get('category'))
                self.fields['bus'].queryset = Bus.objects.filter(category_id=category_id).order_by('name')
            except (ValueError, TypeError):
                pass


# Weekly Booking Forms
class WeeklyBookingForm(forms.ModelForm):
    """نموذج الحجز الأسبوعي للمستخدمين"""
    
    DAYS_CHOICES = [
        ('saturday', 'السبت'),
        ('sunday', 'الأحد'),
        ('monday', 'الإثنين'),
        ('tuesday', 'الثلاثاء'),
        ('wednesday', 'الأربعاء'),
        ('thursday', 'الخميس'),
        ('friday', 'الجمعة'),
    ]
    
    departure_days = forms.CharField(
        widget=forms.HiddenInput(),
        label="أيام الذهاب",
        required=False
    )
    
    return_days = forms.CharField(
        widget=forms.HiddenInput(),
        label="أيام العودة",
        required=False
    )
    
    departure_time = forms.CharField(
        widget=forms.HiddenInput(),
        label="وقت الذهاب",
        required=False
    )
    
    return_time = forms.CharField(
        widget=forms.HiddenInput(),
        label="وقت العودة",
        required=False
    )
    
    pickup_location = forms.CharField(
        widget=forms.HiddenInput(),
        label="نقطة الالتقاط",
        required=False
    )
    
    dropoff_location = forms.CharField(
        widget=forms.HiddenInput(),
        label="نقطة النزول",
        required=False
    )
    
    class Meta:
        model = WeeklyBooking
        fields = ['departure_days', 'departure_time', 'return_days', 'return_time', 'pickup_location', 'dropoff_location']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # إذا كان هناك حجز موجود، نعرض القيم الحالية
        if self.instance and self.instance.pk:
            self.fields['departure_days'].initial = self.instance.departure_days
            self.fields['return_days'].initial = self.instance.return_days
    
    def clean(self):
        cleaned_data = super().clean()
        departure_days = cleaned_data.get('departure_days')
        return_days = cleaned_data.get('return_days')
        
        # التحقق من اختيار يوم واحد على الأقل
        if not departure_days and not return_days:
            raise forms.ValidationError("يجب اختيار يوم واحد على الأقل للذهاب أو العودة")
        
        return cleaned_data


class WeeklyScheduleForm(forms.ModelForm):
    """نموذج إدارة الجداول الزمنية للأدمن"""
    
    class Meta:
        model = WeeklySchedule
        fields = ['category', 'day_of_week', 'trip_type', 'time', 'is_active']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'day_of_week': forms.Select(attrs={'class': 'form-control'}),
            'trip_type': forms.Select(attrs={'class': 'form-control'}),
            'time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
