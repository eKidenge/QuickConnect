from django.urls import path
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from quickconnect import views

urlpatterns = [
    path('admin/', admin.site.urls),  # Default Django admin
    
    path('', views.home, name='home'),
    
    # AUTHENTICATION ROUTES
    path('api/register/', views.api_register, name='api-register'),
    path('api/login/', views.api_login, name='api-login'),
    
    # USER PROFILE & FAVORITES ROUTES
    path('api/user/profile/', views.user_profile, name='user-profile'),
    path('api/user/favorites/', views.user_favorites, name='user-favorites'),
    path('api/user/favorites/<int:professional_id>/', views.manage_favorites, name='manage-favorites'),
    
    # PROFESSIONAL ROUTES - FIXED: Use professional_detail_api
    path('api/professionals/', views.professional_list, name='professional-list'),
    path('api/professionals/<int:professional_id>/', views.professional_detail_api, name='professional-detail'),
    path('api/professional/dashboard/<int:id>/', views.professional_dashboard, name='professional-dashboard'),
    
    # PROFESSIONAL STATUS ROUTES - ADD THESE
    path('api/professional/profile/', views.professional_profile, name='professional-profile'),
    path('api/professional/profile/update/<int:professional_id>/', views.update_professional_profile, name='update-professional-profile'),
    path('api/professional/dashboard-stats/<int:professional_id>/', views.professional_dashboard_stats, name='professional-dashboard-stats'),
    path('api/professional/pending-requests/<int:professional_id>/', views.professional_pending_requests, name='professional-pending-requests'),
    path('api/professional/earnings/<int:professional_id>/', views.professional_earnings, name='professional-earnings'),
    path('api/professional/sessions/<int:professional_id>/', views.professional_sessions, name='professional-sessions'),
    path('api/professional/online-status/<int:professional_id>/', views.update_professional_online_status, name='update-professional-online-status'),
    path('api/professional/availability/<int:professional_id>/', views.update_professional_availability, name='update-professional-availability'),
    
    # SESSION ROUTES
    path('api/sessions/history/', views.session_history, name='session-history'),
    path('api/session/accept/<int:session_id>/', views.accept_session_request, name='accept-session-request'),
    path('api/session/decline/<int:session_id>/', views.decline_session_request, name='decline-session-request'),

    # ADMIN DASHBOARD ROUTES
    path('api/admin/dashboard/stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    path('api/admin/dashboard/revenue-chart/', views.revenue_chart_data, name='revenue-chart'),
    path('api/admin/dashboard/recent-activity/', views.recent_activity, name='recent-activity'),
    
    # ADMIN – PROFESSIONAL MANAGEMENT - FIXED: Use professional_detail_api
    path('api/admin/professionals/pending/', views.pending_professionals, name='pending-professionals'),
    path('api/admin/professionals/<int:professional_id>/approve/', views.approve_professional, name='approve-professional'),
    path('api/admin/professionals/<int:professional_id>/reject/', views.reject_professional, name='reject-professional'),
    path('api/admin/professionals/all/', views.all_professionals, name='all-professionals'),
    path('api/admin/professionals/<int:professional_id>/detail/', views.professional_detail_api, name='admin-professional-detail'),
    
    # ADMIN – USER MANAGEMENT
    path('api/admin/users/', views.users_list, name='users-list'),
    path('api/admin/users/<int:user_id>/', views.user_detail, name='user-detail'),
    path('api/admin/users/<int:user_id>/status/', views.update_user_status, name='update-user-status'),
    path('api/admin/users/<int:user_id>/role/', views.update_user_role, name='update-user-role'),
    path('api/admin/users/<int:user_id>/delete/', views.delete_user, name='delete-user'),
    
    # ADMIN – ANALYTICS
    path('api/admin/analytics/users/', views.user_analytics, name='user-analytics'),
    path('api/admin/analytics/sessions/', views.session_analytics, name='session-analytics'),
    path('api/admin/analytics/financial/', views.financial_analytics, name='financial-analytics'),

    # ADMIN – CATEGORIES
    path('api/admin/categories/', views.admin_categories_list, name='categories-list'),
    path('api/admin/categories/<int:category_id>/update/', views.update_category, name='update-category'),
    path('api/admin/categories/<int:category_id>/delete/', views.delete_category, name='delete-category'),

    # PUBLIC – CATEGORIES
    path('api/categories/', views.public_categories_list, name='public-categories-list'),

    # FILE UPLOAD ENDPOINTS
    path('api/upload/license/', views.upload_license_file, name='upload-license'),
    path('api/upload/profile-image/', views.upload_profile_image, name='upload-profile-image'),
    
    # SESSION & CHAT ROUTES - FIXED: Use get_session_messages_api instead of get_session_messages
    path('api/sessions/create/', views.create_session, name='create-session'),
    path('api/sessions/<int:session_id>/messages/', views.get_session_messages_api, name='session-messages'),  # FIXED THIS LINE
    path('api/sessions/<int:session_id>/end/', views.end_session_api, name='end-session'),  # Also fixed end_session to end_session_api
    path('api/sessions/<int:session_id>/', views.get_session_detail, name='session-detail'),
    path('api/messages/send/', views.send_message_api, name='send-message'),  # Fixed send_message to send_message_api
    
    # CALL FUNCTIONALITY ROUTES
    path('api/video/initiate/', views.initiate_video_call, name='initiate-video'),
    path('api/video/join/<int:session_id>/', views.join_video_call, name='join-video'),
    path('api/video/end/<int:session_id>/', views.end_video_call, name='end-video'),
    
    path('api/voice/initiate/', views.initiate_voice_call, name='initiate-voice'),
    path('api/voice/end/<int:session_id>/', views.end_voice_call, name='end-voice'),
    
    # NOTIFICATION ROUTES
    path('api/notifications/', views.get_notifications, name='get-notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark-all-notifications-read'),
    
    # ADMIN PROFESSIONALS API ROUTE - ADD THIS
    path('api/admin/professionals/', views.admin_professionals_api, name='admin-professionals-api'),
    
    # DEBUG ROUTES
    path('api/debug/professionals/', views.debug_all_professionals, name='debug-professionals'),
    path('api/debug/sessions/', views.debug_all_sessions, name='debug-sessions'),
    path('debug/professionals-direct/', views.debug_professionals_direct, name='debug-professionals-direct'),
    
    # =========================================================================
    # NEW ENDPOINTS FOR REACT NATIVE APP - ADDED BELOW
    # =========================================================================
    
	# ALGORITHM MATCHING & PROFESSIONAL SEARCH
    path('api/professionals/category/<str:category>/', views.professionals_by_category, name='professionals-by-category'),
    path('api/professionals/search/', views.search_professionals, name='search-professionals'),
    path('api/professionals/<int:professional_id>/availability/', views.check_professional_availability, name='check-professional-availability'),
    
    # LOCKING MECHANISM FOR ALGORITHM MATCHING
    path('api/locks/acquire/', views.acquire_lock, name='acquire-lock'),
    path('api/locks/release/', views.release_lock, name='release-lock'),
    
    # PAYMENT PROCESSING ENDPOINTS
    path('api/mpesa/stk-push/', views.initiate_mpesa_stk_push, name='mpesa-stk-push'),
    path('api/mpesa/callback/', views.mpesa_callback, name='mpesa-callback'),
    path('api/payments/record/', views.record_payment, name='record-payment'),
    path('api/payments/verify/<str:transaction_id>/', views.verify_payment, name='verify-payment'),
    path('api/payments/history/', views.payment_history, name='payment-history'),
    
    # SESSION MANAGEMENT ENDPOINTS
    path('api/sessions/rate/', views.rate_session, name='rate-session'),
    path('api/sessions/<int:session_id>/complete/', views.complete_session, name='complete-session'),
    path('api/sessions/<int:session_id>/update/', views.update_session_status, name='update-session-status'),
    
    # CALL MANAGEMENT ENDPOINTS
    path('api/calls/initiate-voice/', views.initiate_voice_call_api, name='initiate-voice-call-api'),
    path('api/calls/initiate-video/', views.initiate_video_call_api, name='initiate-video-call-api'),
    path('api/calls/<int:call_id>/status/', views.update_call_status, name='update-call-status'),
    
    # NOTIFICATION ENDPOINTS
    path('api/notifications/send/', views.send_notification, name='send-notification'),
    path('api/notifications/receipt/', views.send_receipt_notification, name='send-receipt-notification'),
    
    # RECEIPT & DOCUMENT GENERATION
    path('api/receipts/generate/', views.generate_receipt, name='generate-receipt'),
    path('api/receipts/<str:receipt_number>/', views.get_receipt, name='get-receipt'),
    path('api/receipts/user/', views.user_receipts, name='user-receipts'),
    
    # CLIENT DASHBOARD ENDPOINTS
    path('api/client/dashboard/stats/', views.client_dashboard_stats, name='client-dashboard-stats'),
    path('api/client/sessions/active/', views.client_active_sessions, name='client-active-sessions'),
    path('api/client/sessions/completed/', views.client_completed_sessions, name='client-completed-sessions'),
    
    # REAL-TIME AVAILABILITY CHECK
    path('api/professionals/<int:professional_id>/real-time-availability/', views.real_time_availability, name='real-time-availability'),
    
    # CATEGORY-BASED PROFESSIONAL MATCHING
    path('api/categories/<int:category_id>/professionals/', views.category_professionals, name='category-professionals'),
    path('api/categories/with-professionals/', views.categories_with_professionals, name='categories-with-professionals'),
    
    # PAYMENT GATEWAY INTEGRATION
    path('api/payments/card/initiate/', views.initiate_card_payment, name='initiate-card-payment'),
    path('api/payments/bank/initiate/', views.initiate_bank_transfer, name='initiate-bank-transfer'),
    path('api/payments/<str:payment_id>/status/', views.payment_status, name='payment-status'),
    
    # SESSION VERIFICATION ENDPOINTS
    path('api/sessions/<int:session_id>/verify/', views.verify_session_access, name='verify-session-access'),
    path('api/sessions/<int:session_id>/participants/', views.get_session_participants, name='get-session-participants'),
    
    # AI MATCHING ALGORITHM ENDPOINTS
    path('api/matching/algorithm/', views.run_matching_algorithm, name='run-matching-algorithm'),
    path('api/matching/scores/', views.calculate_matching_scores, name='calculate-matching-scores'),
    
    # USER PREFERENCES & SETTINGS
    path('api/user/preferences/', views.user_preferences, name='user-preferences'),
    path('api/user/notifications/settings/', views.notification_settings, name='notification-settings'),
    
    # SUPPORT & HELP ENDPOINTS
    path('api/support/tickets/', views.support_tickets, name='support-tickets'),
    path('api/support/contact/', views.contact_support, name='contact-support'),
    
    # ANALYTICS & REPORTING
    path('api/analytics/session-metrics/', views.session_metrics, name='session-metrics'),
    path('api/analytics/payment-metrics/', views.payment_metrics, name='payment-metrics'),
    path('api/analytics/user-engagement/', views.user_engagement, name='user-engagement'),
]

# SERVE MEDIA AND STATIC FILES IN DEVELOPMENT
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)