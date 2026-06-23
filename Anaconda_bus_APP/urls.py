from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    signup, user_profile, generate_qr,
    mark_attendance_university_code, update_payment_status,
    form_bookings_day_view,
    get_form_bookings_api,
)
from .views import booking_success
from .views import mark_attendance

from .views import mark_attendance, confirm_attendance
from .views import update_payment_status , cancel_booking
from .views import generate_general_qr, scan_qr
from .views import scan_qr_attendance, confirm_attendance, trip_paymentgateway ,update_ip
from .views import update_esp_ip ,receive_esp_data , show_dashboard , subscription_detail
from .views import subscription_payment_success, subscription_payment_failed ,load_pickup_locations_filtered ,load_cities_by_round_filtered
from telegram_bot import views as telegram_bot_views
from .views import weekly_booking_view, get_weekly_schedules_api, weekly_bookings_day_view, send_whatsapp_weekly_notifications
from . import views_admin
from . import views , dashboard_views
from .views import bus_report_view, renew_trip_view, load_buses_ajax
dashboard_patterns = [
    path('home/', dashboard_views.dashboard_home, name='home'),
    
    # إدارة الرحلات
    path('trips/', dashboard_views.trips_list, name='trips_list'),
    path('trips/<int:trip_id>/', dashboard_views.trip_detail, name='trip_detail'),
    path('trips/<int:trip_id>/bookings/', dashboard_views.trip_bookings, name='trip_bookings'),
    path('trips/<int:trip_id>/pdf/', dashboard_views.generate_trip_pdf, name='trip_pdf'),
    path('trips/renew/', dashboard_views.renew_trips, name='renew_trips'),
    path('trips/<int:trip_id>/toggle-active/', dashboard_views.toggle_trip_active, name='toggle_trip_active'),
    
    # إدارة الركاب
    path('passengers/', dashboard_views.passengers_list, name='passengers_list'),
    path('passengers/<int:passenger_id>/', dashboard_views.passenger_detail, name='passenger_detail'),
    path('passengers/send-whatsapp/', dashboard_views.send_whatsapp_bulk, name='send_whatsapp_bulk'),
    
    # التقارير
    path('reports/', dashboard_views.reports_home, name='reports_home'),
    path('reports/category/<int:category_id>/', dashboard_views.category_report, name='category_report'),
    path('reports/send/', dashboard_views.send_trip_report_view, name='send_report'),
    
    # الفئات والحافلات
    path('categories/', dashboard_views.categories_list, name='categories_list'),
    path('buses/', dashboard_views.buses_list, name='buses_list'),
    
    # AJAX endpoints
    path('ajax/load-buses/', dashboard_views.load_buses_ajax, name='load_buses'),
    path('ajax/trip-stats/<int:trip_id>/', dashboard_views.get_trip_stats, name='trip_stats'),
]
urlpatterns = [
    path('allen/dashboard/', include((dashboard_patterns, 'dashboard'), namespace='dashboard')),
    path('allen/installment/<int:installment_id>/pay/', views.pay_installment, name='pay_installment'),
    path('allen/forgot-password/', views.send_otp_whatsapp, name="send_otp_whatsapp"),
    path('allen/verify-otp/', views.verify_otp, name="verify_otp"),
    path('allen/reset-password/', views.reset_password, name="reset_password"),
    path('allen/ask-gpt/', views.ask_gpt, name="ask_gpt"),
    path('allen/ask-gemini/', views.ask_gemini, name="ask_gemini"),
    path('allen/ask-gemini-page/', views.ask_gemini_page, name="ask_gemini_page"),
    path('allen/api/trips/active/', views.get_active_trips, name='api-get-active-trips'),
    path('allen/api/trips/<int:id>/', views.TripDetailView.as_view(), name='api-trip-detail'),
    path('allen/api/bookings/create/', views.BookingCreateView.as_view(), name='api-booking-create'),
    path('allen/api/bookings/<int:id>/cancel/', views.BookingCancelView.as_view(), name='api-booking-cancel'),
    path('allen/api/admin/booking-notifications/', views.admin_booking_notifications, name='admin_booking_notifications'),
    path('allen/api/passengers/by-phone/', views.get_passenger_by_phone, name='api-get-passenger-by-phone'),
    path('allen/api/stats/bookings/', views.get_booking_stats, name='api-get-booking-stats'),
    path('allen/api/buses/<int:id>/location/', views.BusLiveLocationView.as_view(), name='api-bus-live-location'),
    path('allen/api/buses/<int:id>/status/', views.BusStatusUpdateView.as_view(), name='api-bus-status-update'),
    path('allen/api/trips/check_student_trips/', views.check_student_trips, name="check_student_trips"),
    path('allen/api/maps/search/', views.map_search, name='map_search'),
    path('allen/api/maps/reverse/', views.map_reverse, name='map_reverse'),
    path('allen/api/maps/route/', views.map_route, name='map_route'),
    path('allen/update-payment-status/<int:booking_id>/', update_payment_status, name='update_payment_status'),
    path('allen/trip/<int:trip_id>/notify/', views.notify_trip_departure, name='notify_trip_departure'),
    path('allen/scan_qr_attendance/', scan_qr_attendance, name="scan_qr_attendance"),
    path('allen/confirm_attendance/', confirm_attendance, name='confirm_attendance'),
    path('allen/trip/paymentgateway/', trip_paymentgateway, name='trip_paymentgateway'),
    path('allen/payment/success/', views.kashier_payment_success, name='kashier_payment_success'),
    path('allen/car/payment/success/', views.car_payment_success, name="car_payment_success"),
    path('allen/car/payment/failed/', views.car_payment_success, name="car_payment_failed"),
    path('allen/update_ip/', views.update_ip, name='update_ip'),
    path('allen/api/update_esp_ip', update_esp_ip, name='update_esp_ip'),
    path('allen/ajax/load-dropoff-locations/', views.load_dropoff_locations, name="ajax_load_dropoff_locations"),
    path('allen/ajax/get-available-trips/', views.get_available_trips_for_edit, name='ajax_get_available_trips'),
    path('allen/change-booking/<int:booking_id>/<int:new_trip_id>/', views.change_booking_trip, name='change_booking_trip'),
    
    # ✅ --- بداية الإضافة: إضافة الروابط المخصصة للأدمن هنا --- ✅
    path('allen/admin/bus-report/', bus_report_view, name='bus_report'),
    path('allen/admin/trip/<int:old_trip_id>/renew/', renew_trip_view, name='renew_trip'),
    path('allen/admin/ajax/load-buses/', load_buses_ajax, name='ajax_load_buses'),
    # ✅ --- نهاية الإضافة --- ✅
    path('allen/trip/<int:trip_id>/pdf/', views.generate_pdf_view, name="trip_pdf"),
    path('allen/ajax/load-cities-by-round-filtered/', views.load_cities_by_round_filtered, name='ajax_load_cities_by_round_filtered'),
    path('allen/ajax/load-pickup-locations-filtered/', views.load_pickup_locations_filtered, name='ajax_load_pickup_locations_filtered'),
    path('allen/trip/store-session/', views.store_booking_session, name='store_booking_session'),
    path('allen/general_qr/', generate_general_qr, name='general_qr'),
    path('allen/scan_qr/', scan_qr, name='scan_qr'),
    path('allen/admin/bus-report/', views.bus_report_view, name='bus_report'),
    path('allen/mark-attendance/<int:booking_id>/', views.mark_attendance, name='mark_attendance'),
    path('allen/end-trip/<int:trip_id>/', views.end_trip, name='end_trip'),
    path('allen/success/', views.success_page, name='success_page'),
    path('allen/check-trip-code/', views.check_trip_code, name='check_trip_code'),
    path('allen/update-bus-location/<int:bus_id>/', views.update_bus_location, name='update_bus_location'),
    path('allen/user-data/', user_profile, name='user_data'),
    path('allen/repeat-last-reservation/', views.repeat_last_reservation, name="repeat_last_reservation"),
    path('allen/face-scan/', views.face_scan_page, name="face_scan_page"),
    path('allen/upload-face/', views.upload_face, name="upload_face"),
    path('allen/my-buses/', views.my_buses, name='my_buses'),
    path('allen/register_student/', views.signup, name='register_student'),
    path('allen/search/', views.search_routes, name='search_routes'),
    path('allen/', views.index, name='index'),  # الصفحة الرئيسية
    path('allen/book/<int:schedule_id>/', views.book_seat, name='book_seat'),
    path('allen/cancel_booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('allen/bookings/', views.user_bookings, name='user_bookings'),
    path('allen/signup/', signup, name='signup'),
    path('allen/sucess_form/', signup, name='sucess_form'),
    path('allen/subscriptions/', views.subscriptions_view, name='subscriptions'),
    path('allen/login/', views.login_view, name='login'),
    path('allen/logout/', views.logout_view, name='logout'),
    path('allen/mark_attendance_university_code/', mark_attendance_university_code, name='mark_attendance_university_code'),
    path('allen/new-login/', views.new_login_signup_view, name='new_login'),
    path('allen/subscription/<int:subscription_id>/<int:passenger_id>/', views.subscription_detail, name='subscription_detail'),
    # path('allen/car-rental/', book_car, name='book_car'),
    path('allen/car-booking-success/', booking_success, name='booking_success'),
    # path('allen/cars/', book_car, name='car_booking'),
    path('allen/select-seat/<int:reservation_id>/', views.select_seat, name='select_seat'),
    path('allen/cars/', views.car_list, name='car_list'),
    path('allen/car/<int:car_id>/', views.car_detail, name='car_detail'),
    path('allen/subscriptions/<int:passenger_id>/', views.subscriptions_view, name='subscriptions'),
    path('allen/form-reservation/<int:category_id>/', views.form_reservation, name='form_reservation'),
    path('allen/choose-trip/<str:passenger_ids>/', views.choose_trip, name='choose_trip'),
    path('allen/ajax/load-cities-by-round/', views.load_cities_by_round, name='ajax_load_cities_by_round'),
    path('allen/ajax/load-round-times/', views.ajax_load_round_times, name='ajax_load_round_times'),
    path('allen/ajax/load-pickup-locations/', views.load_pickup_locations, name='ajax_load_pickup_locations'),
    path('allen/create_car_payment/', views.create_car_payment, name='create_car_payment'),
    path('allen/verify-payment/', views.payment_verify, name='payment_verify'),
    path('allen/round-trip/payment/success/', views.round_trip_payment_success, name='round_trip_payment_success'),
    path('allen/get_trip_pickup_points/<int:trip_id>/', views.get_trip_pickup_points, name='get_trip_pickup_points'),
    path('allen/ajax/get-trips-by-destination/', views.get_trips_by_destination, name="get_trips_by_destination"),
    path('allen/esp32-data/', views.receive_esp_data),
    path('allen/track/<int:bus_id>/', views.track_bus_view, name='track_bus_view'),
    path('allen/api/mark-attendance/', views.mark_attendance, name='mark_attendance'),

    # ✅ مسار الـ API الذي سيستخدمه JavaScript لجلب التحديثات
    path('allen/api/get-location/<int:bus_id>/', views.get_live_location_data, name='get_live_location_data'),
    path('allen/passenger/<int:passenger_id>/installments/', views.installments_list, name="installments_list"),
    path('allen/ajax/get-plan-details/<int:plan_id>/', views.get_installment_plan_details, name='get_installment_plan_details'),
    path('allen/get_installment_plan_details/<int:plan_id>/', views.get_installment_plan_details, name="get_installment_plan_details"),
    path('allen/dashboard/', views.show_dashboard, name='dashboard'),
    path('allen/form/payment/success/', views.form_payment_success, name="form_payment_success"),
    path('allen/form/payment/failed/', views.form_payment_failed, name="form_payment_failed"),
    path('allen/subscription/<int:subscription_id>/<int:passenger_id>/', subscription_detail, name='subscription_detail'),
    path('allen/subscription/payment/success/', subscription_payment_success, name='subscription_payment_success'),
    path('allen/subscription/payment/failed/', subscription_payment_failed, name='subscription_payment_failed'),
    path('allen/api/update-location/<int:bus_id>/', views.update_bus_location, name='update_bus_location'),
    path('allen/api/session/start/<int:bus_id>/', views.start_location_session, name='start_location_session'),
    path('allen/api/session/stop/<int:bus_id>/', views.stop_location_session, name='stop_location_session'),
    path('allen/api/get-location/<int:bus_id>/', views.get_live_tracking_data, name='get_live_tracking_data'),
    path('allen/track/<int:bus_id>/', views.track_bus_view, name='track_bus_view'),
    path('allen/round-trip/', views.round_trip_booking, name='round_trip_booking'),
    # مسار تعديل حجز الرحلة العادي (افترضه موجوداً)
    
    # --- المسار الجديد لتعديل حجز الفورم ---
    path('allen/change-form-booking/<int:form_booking_id>/<int:new_trip_id>/', views.change_form_booking_trip, name='change_form_booking_trip'),
    
    # --- المسار الذي يجلب الرحلات المتاحة عبر AJAX ---
    path('allen/edit-form-reservation/<int:booking_id>/', views.edit_form_reservation, name='edit_form_reservation'),
    path('allen/cancel-form-reservation/<int:booking_id>/', views.cancel_form_reservation, name='cancel_form_reservation'),
    path('allen/upload/<str:esp_id>/', views.upload_frame, name='upload_frame'),
    path('allen/stream/<str:esp_id>/', views.latest_frame, name='latest_frame'),
    path('allen/latest-frame/<str:esp_id>/', views.latest_frame),

    path('allen/viewer/', views.viewer_page, name='viewer_page'),
    path('allen/get_trip_seats/<int:trip_id>/', views.get_trip_seats, name='get_trip_seats'),
    
    # Weekly Booking Routes
    path('allen/weekly-booking/<int:category_id>/', views.weekly_booking_view, name='weekly_booking'),
    path('allen/weekly-booking-new/<int:category_id>/', views.weekly_booking_view_new, name='weekly_booking_new'),
    path('allen/api/weekly-schedules/<int:category_id>/', views.get_weekly_schedules_api, name='get_weekly_schedules_api'),
    path('allen/api/pickup-locations/<int:city_id>/', views.get_pickup_locations_api, name='get_pickup_locations_api'),
    path('allen/admin/weekly-bookings/<str:date>/', views.weekly_bookings_day_view, name='weekly_bookings_day'),
    path('allen/api/send-whatsapp-notifications/<str:date>/', views.send_whatsapp_weekly_notifications, name='send_whatsapp_weekly_notifications'),
    
    # Form booking URLs
    path('allen/admin/form-bookings/<str:date>/', views.form_bookings_day_view, name='form_bookings_day'),
    path('allen/api/form-bookings/<str:date>/', views.get_form_bookings_api, name='get_form_bookings_api'),
    
    # Admin Telegram Management URLs
    path('allen/admin/telegram/', views_admin.telegram_admin_dashboard, name='telegram_admin_dashboard'),
    path('allen/admin/telegram/notifications/', views_admin.telegram_notifications, name='telegram_notifications'),
    path('allen/admin/telegram/activities/', views_admin.telegram_activities, name='telegram_activities'),
    path('allen/admin/telegram/broadcast/', views_admin.send_telegram_broadcast, name='telegram_broadcast'),
    path('allen/admin/telegram/link/', views_admin.link_telegram_account, name='link_telegram_account'),
    
    # Admin Weekly Booking Management URLs
    path('allen/admin/weekly-booking-trips-manager/', views_admin.weekly_booking_trips_manager, name='weekly_booking_trips_manager'),
    path('allen/admin/assign-passenger-to-trip/', views_admin.assign_passenger_to_trip, name='assign_passenger_to_trip'),
    path('allen/admin/get-booking-details/<int:booking_id>/', views_admin.get_booking_details, name='get_booking_details'),
    path('allen/admin/get-trip-details/<int:trip_id>/', views_admin.get_trip_details, name='get_trip_details'),
    
    # Telegram Bot Webhook
    path('allen/telegram/webhook/', telegram_bot_views.telegram_webhook, name='telegram_webhook'),
    
    # Telegram Success Page
    path('allen/telegram/success/', views.telegram_success_page, name='telegram_success_page'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
