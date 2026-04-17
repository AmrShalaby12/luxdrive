from django.db import models
from django.contrib.auth.models import User

class TelegramUserNotification(models.Model):
    """"Store user notifications for Telegram bot"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="المستخدم")
    reservation_id = models.CharField(max_length=100, verbose_name="رقم الحجز")
    student_name = models.CharField(max_length=100, verbose_name="اسم الطالب")
    trip_type = models.CharField(max_length=50, verbose_name="نوع الرحلة")
    trip_date = models.DateField(verbose_name="تاريخ الرحلة")
    message = models.TextField(verbose_name="الرسالة")
    is_sent = models.BooleanField(default=False, verbose_name="تم الإرسال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "إشعار Telegram"
        verbose_name_plural = "إشعارات Telegram"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.student_name} - {self.reservation_id}"

class TelegramUserActivity(models.Model):
    """"Track Telegram user activities for admin dashboard"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="المستخدم")
    chat_id = models.CharField(max_length=100, verbose_name="معرف الدردشة")
    action = models.CharField(max_length=100, verbose_name="الإجراء")
    booking_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="رقم الحجز")
    details = models.TextField(blank=True, null=True, verbose_name="التفاصيل")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإجراء")
    
    class Meta:
        verbose_name = "نشاط Telegram"
        verbose_name_plural = "أنشطة Telegram"
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.action}"
