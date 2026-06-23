# Main_Bus_Management/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from django.urls import re_path
from Anaconda_bus_APP import views_admin

urlpatterns = [
    # المسارات الحالية في مشروعك
    path('grappelli/', include('grappelli.urls')),

    path('admin/', admin.site.urls),
    path('allen/admin/', admin.site.urls),
    path('', include('Anaconda_bus_APP.urls')),
    
    # إضافة صفحات Telegram admin
    path('allen/admin/telegram/', views_admin.telegram_admin_dashboard, name='telegram_admin_dashboard'),
    path('allen/admin/telegram/notifications/', views_admin.telegram_notifications, name='telegram_notifications'),
    path('allen/admin/telegram/activities/', views_admin.telegram_activities, name='telegram_activities'),
    path('allen/admin/telegram/broadcast/', views_admin.send_telegram_broadcast, name='telegram_broadcast'),
    
    # هذا المسار يخدم ملفات media التي يرفعها المستخدمون
    re_path(r'^allen/media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# --- أضف هذا الجزء في نهاية الملف ---
# هذا الكود يخدم الملفات الساكنة (CSS, JS, Images) فقط في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
