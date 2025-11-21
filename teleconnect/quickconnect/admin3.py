from django.contrib import admin
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.http import HttpResponse
import csv
from datetime import datetime, timedelta
from .models import *

class CustomAdminSite(AdminSite):
    site_header = "Professional Consultation Platform Administration"
    site_title = "Admin Portal"
    index_title = "Welcome to Consultation Platform Admin"

admin_site = CustomAdminSite(name='custom_admin')

# Custom actions
def approve_professionals(modeladmin, request, queryset):
    updated = queryset.update(status='approved', approved_at=timezone.now())
    modeladmin.message_user(request, f"{updated} professionals approved successfully.")
approve_professionals.short_description = "Approve selected professionals"

def mark_as_busy(modeladmin, request, queryset):
    updated = queryset.update(available=False)
    modeladmin.message_user(request, f"{updated} professionals marked as busy.")
mark_as_busy.short_description = "Mark as busy (not available)"

def mark_as_available(modeladmin, request, queryset):
    updated = queryset.update(available=True)
    modeladmin.message_user(request, f"{updated} professionals marked as available.")
mark_as_available.short_description = "Mark as available"

def complete_sessions(modeladmin, request, queryset):
    updated = queryset.update(status='completed', ended_at=timezone.now())
    modeladmin.message_user(request, f"{updated} sessions marked as completed.")
complete_sessions.short_description = "Mark sessions as completed"

def cancel_sessions(modeladmin, request, queryset):
    updated = queryset.update(status='cancelled')
    modeladmin.message_user(request, f"{updated} sessions cancelled.")
cancel_sessions.short_description = "Cancel selected sessions"

def resolve_issues(modeladmin, request, queryset):
    updated = queryset.update(resolved=True, resolved_by=request.user.username, resolved_at=timezone.now())
    modeladmin.message_user(request, f"{updated} issues marked as resolved.")
resolve_issues.short_description = "Mark selected issues as resolved"

def export_to_csv(modeladmin, request, queryset):
    model = modeladmin.model
    model_name = model._meta.verbose_name_plural
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{model_name}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv"'
    
    writer = csv.writer(response)
    
    # Get field names
    field_names = [field.name for field in model._meta.fields]
    writer.writerow(field_names)
    
    # Write data rows
    for obj in queryset:
        row = [getattr(obj, field) for field in field_names]
        writer.writerow(row)
    
    return response
export_to_csv.short_description = "Export selected items to CSV"

@admin.register(Category, site=admin_site)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'base_price', 'enabled', 'professional_count', 'session_count', 'created_at']
    list_filter = ['enabled', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['enabled', 'base_price']
    ordering = ['name']
    list_per_page = 20

@admin.register(Professional, site=admin_site)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'specialization', 'category', 'rate', 'status', 
        'available', 'online_status', 'average_rating', 'total_sessions', 
        'earnings_today', 'earnings_this_month', 'response_rate', 'completion_rate',
        'created_at'
    ]
    list_filter = ['status', 'available', 'online_status', 'category', 'created_at']
    search_fields = ['name', 'email', 'specialization', 'phone']
    list_editable = ['status', 'available', 'rate']
    readonly_fields = [
        'created_at', 'updated_at', 'total_calls', 'total_call_duration',
        'average_rating', 'current_call', 'total_sessions',
        'earnings_today', 'earnings_this_month', 'total_earnings',
        'response_rate', 'completion_rate',
        'today_sessions', 'monthly_sessions', 'active_sessions_count',
        'average_call_duration_display'
    ]
    actions = [approve_professionals, mark_as_busy, mark_as_available, export_to_csv]
    list_per_page = 20
    
    def earnings_today(self, obj):
        """Calculate today's earnings"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        today_sessions = Session.objects.filter(
            professional=obj,
            status='completed',
            ended_at__range=(today_start, today_end)
        )
        today_earnings = today_sessions.aggregate(total=Sum('cost'))['total'] or 0
        return f"KSH {today_earnings:.2f}"
    earnings_today.short_description = "Today's Earnings"
    
    def earnings_this_month(self, obj):
        """Calculate this month's earnings"""
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_sessions = Session.objects.filter(
            professional=obj,
            status='completed',
            ended_at__gte=month_start
        )
        monthly_earnings = monthly_sessions.aggregate(total=Sum('cost'))['total'] or 0
        return f"KSH {monthly_earnings:.2f}"
    earnings_this_month.short_description = "Monthly Earnings"
    
    def total_earnings(self, obj):
        """Calculate total lifetime earnings"""
        total_sessions = Session.objects.filter(
            professional=obj,
            status='completed'
        )
        total_earnings = total_sessions.aggregate(total=Sum('cost'))['total'] or 0
        return f"KSH {total_earnings:.2f}"
    total_earnings.short_description = "Total Earnings"
    
    def response_rate(self, obj):
        """Calculate response rate (sessions responded to within 1 minute)"""
        from django.db.models import F, ExpressionWrapper, DurationField
        
        total_requests = Session.objects.filter(professional=obj).count()
        if total_requests == 0:
            return "0%"
        
        quick_responses = Session.objects.filter(
            professional=obj,
            actual_start__isnull=False,
            created_at__isnull=False
        ).annotate(
            response_time=ExpressionWrapper(
                F('actual_start') - F('created_at'),
                output_field=DurationField()
            )
        ).filter(
            response_time__lte=timedelta(minutes=1)
        ).count()
        
        rate = (quick_responses / total_requests) * 100
        return f"{rate:.1f}%"
    response_rate.short_description = "Response Rate"
    
    def completion_rate(self, obj):
        """Calculate session completion rate"""
        total_sessions = Session.objects.filter(professional=obj).count()
        if total_sessions == 0:
            return "0%"
        
        completed_sessions = Session.objects.filter(
            professional=obj, 
            status='completed'
        ).count()
        
        rate = (completed_sessions / total_sessions) * 100
        return f"{rate:.1f}%"
    completion_rate.short_description = "Completion Rate"
    
    def today_sessions(self, obj):
        """Count today's sessions"""
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        today_count = Session.objects.filter(
            professional=obj,
            status='completed',
            ended_at__range=(today_start, today_end)
        ).count()
        return today_count
    today_sessions.short_description = "Today's Sessions"
    
    def monthly_sessions(self, obj):
        """Count this month's sessions"""
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        monthly_count = Session.objects.filter(
            professional=obj,
            status='completed',
            ended_at__gte=month_start
        ).count()
        return monthly_count
    monthly_sessions.short_description = "Monthly Sessions"
    
    def active_sessions_count(self, obj):
        """Count active sessions"""
        active_count = Session.objects.filter(
            professional=obj,
            status__in=['active', 'in_progress']
        ).count()
        return active_count
    active_sessions_count.short_description = "Active Sessions"
    
    def average_call_duration_display(self, obj):
        return f"{obj.average_call_duration} min"
    average_call_duration_display.short_description = 'Avg Call Duration'
    
    def get_queryset(self, request):
        """Optimize queryset for performance"""
        queryset = super().get_queryset(request)
        return queryset.select_related('category').prefetch_related('sessions')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'specialization', 'category', 'email', 'phone')
        }),
        ('Professional Details', {
            'fields': ('rate', 'available', 'online_status', 'experience_years', 'bio', 'locked_by')
        }),
        ('Real-time Statistics', {
            'fields': (
                ('average_rating', 'total_sessions'),
                ('today_sessions', 'monthly_sessions'),
                ('active_sessions_count', 'response_rate'),
                ('completion_rate', 'total_calls'),
                ('average_call_duration_display',)
            )
        }),
        ('Financial Overview', {
            'fields': (
                ('earnings_today', 'earnings_this_month'),
                ('total_earnings',)
            )
        }),
        ('Call Management', {
            'fields': ('current_call', 'total_call_duration'),
            'classes': ('collapse',)
        }),
        ('Status Management', {
            'fields': ('status', 'approved_at', 'rejection_reason', 'rejected_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ProfessionalAvailability, site=admin_site)
class ProfessionalAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['professional', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available', 'professional']
    search_fields = ['professional__name']
    list_per_page = 20

@admin.register(ProfessionalDocument, site=admin_site)
class ProfessionalDocumentAdmin(admin.ModelAdmin):
    list_display = ['professional', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['professional__name']
    list_per_page = 20

@admin.register(Session, site=admin_site)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'professional', 'client_id', 'session_type', 'status', 
        'duration', 'call_duration_display', 'cost', 'call_quality', 
        'created_at', 'has_call_issues_display'
    ]
    list_filter = ['session_type', 'status', 'call_quality', 'created_at', 'professional']
    search_fields = ['professional__name', 'client_id', 'room_id']
    readonly_fields = [
        'created_at', 'updated_at', 'call_duration', 'call_started_at', 
        'call_ended_at', 'duration', 'total_duration', 'call_duration_minutes',
        'has_call_issues'
    ]
    actions = [complete_sessions, cancel_sessions, export_to_csv]
    list_per_page = 20
    
    def call_duration_display(self, obj):
        if obj.call_duration:
            minutes = obj.call_duration // 60
            seconds = obj.call_duration % 60
            return f"{minutes}m {seconds}s"
        return "No call"
    call_duration_display.short_description = 'Call Duration'
    
    def has_call_issues_display(self, obj):
        if obj.has_call_issues:
            return "⚠️ Yes"
        return "✅ No"
    has_call_issues_display.short_description = 'Call Issues'
    
    def total_duration(self, obj):
        return f"{obj.total_duration:.1f} min"
    total_duration.short_description = 'Total Duration'
    
    def call_duration_minutes(self, obj):
        return f"{obj.call_duration_minutes:.1f} min"
    call_duration_minutes.short_description = 'Call Duration (Min)'
    
    fieldsets = (
        ('Session Information', {
            'fields': ('professional', 'client_id', 'session_type', 'status', 'room_id')
        }),
        ('Call Management', {
            'fields': (
                'call_started_at', 'call_ended_at', 'call_duration',
                'call_quality', 'call_issues'
            )
        }),
        ('Timing', {
            'fields': ('scheduled_start', 'actual_start', 'ended_at')
        }),
        ('Financials & Duration', {
            'fields': ('duration', 'cost', 'total_duration', 'call_duration_minutes')
        }),
        ('Ratings & Reviews', {
            'fields': ('client_rating', 'client_review'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(SessionBooking, site=admin_site)
class SessionBookingAdmin(admin.ModelAdmin):
    list_display = ['session', 'booked_by', 'scheduled_for', 'booked_at']
    list_filter = ['scheduled_for', 'booked_at']
    search_fields = ['booked_by', 'session__professional__name']
    list_per_page = 20

@admin.register(Payment, site=admin_site)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'amount', 'status', 'payment_method', 'created_at', 'is_successful_display']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'session__professional__name']
    readonly_fields = ['created_at', 'completed_at']
    list_per_page = 20
    
    def is_successful_display(self, obj):
        if obj.is_successful:
            return "✅ Yes"
        return "❌ No"
    is_successful_display.short_description = 'Successful'

@admin.register(Dispute, site=admin_site)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['title', 'session', 'status', 'created_by', 'created_at', 'time_to_resolve_display']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'created_by', 'session__professional__name']
    readonly_fields = ['created_at', 'resolved_at', 'time_to_resolve', 'time_to_resolve_display']
    list_per_page = 20
    
    def time_to_resolve(self, obj):
        """Calculate time to resolve in hours"""
        if obj.resolved_at and obj.created_at:
            return (obj.resolved_at - obj.created_at).total_seconds() / 3600  # in hours
        return None
    
    def time_to_resolve_display(self, obj):
        """Display formatted time to resolve"""
        time_to_resolve = self.time_to_resolve(obj)
        if time_to_resolve is not None:
            if time_to_resolve < 1:
                return f"{round(time_to_resolve * 60)} minutes"
            elif time_to_resolve < 24:
                return f"{round(time_to_resolve, 1)} hours"
            else:
                return f"{round(time_to_resolve / 24, 1)} days"
        return "Not resolved"
    time_to_resolve_display.short_description = 'Time to Resolve'
    
    fieldsets = (
        ('Dispute Information', {
            'fields': ('session', 'title', 'description', 'status', 'created_by')
        }),
        ('Resolution', {
            'fields': ('resolution', 'resolved_at')
        }),
        ('Timing Information', {
            'fields': ('time_to_resolve_display',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ChatMessage, site=admin_site)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'sender_type', 'message_type', 'timestamp', 'read', 'created_at', 'message_preview']
    list_filter = ['sender_type', 'message_type', 'timestamp', 'read', 'created_at']
    search_fields = ['message', 'session__professional__name']
    readonly_fields = ['timestamp', 'created_at']
    list_per_page = 20
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message Preview'
    
    fieldsets = (
        ('Message Information', {
            'fields': ('session', 'message_id', 'message', 'sender_type', 'message_type')
        }),
        ('Status & Timing', {
            'fields': ('read', 'timestamp', 'created_at')
        }),
    )

@admin.register(UserProfile, site=admin_site)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'phone', 'date_of_birth', 'created_at', 'favorites_count']
    list_filter = ['user_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at', 'updated_at', 'favorites_count']
    list_per_page = 20
    
    def favorites_count(self, obj):
        return len(obj.favorite_professionals or [])
    favorites_count.short_description = 'Favorite Pros'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_type', 'phone', 'date_of_birth', 'avatar')
        }),
        ('Favorites', {
            'fields': ('favorite_professionals', 'favorites_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Notification, site=admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'read', 'created_at', 'title_preview']
    list_filter = ['notification_type', 'read', 'created_at']
    search_fields = ['title', 'user__username']
    list_per_page = 20
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title Preview'

@admin.register(CallLog, site=admin_site)
class CallLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'session', 'call_type', 'status', 'start_time', 
        'end_time', 'duration_display', 'call_quality', 'has_technical_issues_display'
    ]
    list_filter = ['call_type', 'status', 'call_quality', 'start_time']
    search_fields = ['session__professional__name', 'session__client_id']
    readonly_fields = ['start_time', 'end_time', 'duration', 'created_at', 'has_technical_issues', 'duration_minutes']
    list_per_page = 20
    
    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes}m {seconds}s"
        return "Ongoing"
    duration_display.short_description = 'Duration'
    
    def has_technical_issues_display(self, obj):
        if obj.has_technical_issues:
            return "⚠️ Yes"
        return "✅ No"
    has_technical_issues_display.short_description = 'Tech Issues'
    
    def duration_minutes(self, obj):
        return f"{obj.duration_minutes:.1f} min"
    duration_minutes.short_description = 'Duration (Min)'
    
    fieldsets = (
        ('Call Information', {
            'fields': ('session', 'call_type', 'status', 'call_quality')
        }),
        ('Timing', {
            'fields': ('start_time', 'end_time', 'duration', 'duration_minutes')
        }),
        ('Technical Details', {
            'fields': ('connection_quality', 'audio_issues', 'video_issues', 'has_technical_issues'),
            'classes': ('collapse',)
        }),
        ('Device & Network', {
            'fields': ('client_device', 'professional_device', 'network_conditions'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(CallAnalytics, site=admin_site)
class CallAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'professional', 'date', 'total_calls', 'completed_calls', 
        'success_rate_display', 'average_duration_display', 'issue_rate_display',
        'total_duration_minutes_display'
    ]
    list_filter = ['date', 'professional']
    readonly_fields = [
        'professional', 'date', 'total_calls', 'completed_calls', 
        'failed_calls', 'missed_calls', 'total_duration', 'average_duration',
        'average_quality_score', 'calls_with_issues', 'success_rate',
        'issue_rate', 'total_duration_minutes'
    ]
    list_per_page = 20
    
    def average_duration_display(self, obj):
        if obj.average_duration:
            return f"{obj.average_duration:.1f}s"
        return "N/A"
    average_duration_display.short_description = 'Avg Duration'
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Success Rate'
    
    def issue_rate_display(self, obj):
        return f"{obj.issue_rate:.1f}%"
    issue_rate_display.short_description = 'Issue Rate'
    
    def total_duration_minutes_display(self, obj):
        return f"{obj.total_duration_minutes:.1f} min"
    total_duration_minutes_display.short_description = 'Total Duration'

@admin.register(CallRecording, site=admin_site)
class CallRecordingAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'status', 'duration_minutes', 'file_size_mb', 
        'available_for_download', 'client_consent', 'professional_consent',
        'created_at'
    ]
    list_filter = ['status', 'available_for_download', 'created_at']
    search_fields = ['session__professional__name', 'session__client_id']
    readonly_fields = ['created_at', 'processed_at', 'file_size', 'duration', 'file_size_mb', 'duration_minutes']
    list_per_page = 20
    
    fieldsets = (
        ('Recording Information', {
            'fields': ('session', 'call_log', 'status', 'storage_location')
        }),
        ('File Details', {
            'fields': ('file_path', 'file_size', 'duration', 'file_size_mb', 'duration_minutes')
        }),
        ('Consent & Access', {
            'fields': ('client_consent', 'professional_consent', 'available_for_download')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(CallIssueReport, site=admin_site)
class CallIssueReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'session', 'issue_type', 'priority', 'resolved', 
        'reported_by', 'reported_at', 'time_to_resolve_display'
    ]
    list_filter = ['issue_type', 'priority', 'resolved', 'reported_at']
    search_fields = ['title', 'session__professional__name', 'reported_by']
    readonly_fields = ['reported_at', 'resolved_at', 'time_to_resolve', 'time_to_resolve_display']
    actions = [resolve_issues, export_to_csv]
    list_per_page = 20
    
    def time_to_resolve_display(self, obj):
        time_to_resolve = obj.time_to_resolve
        if time_to_resolve is not None:
            if time_to_resolve < 1:
                return f"{round(time_to_resolve * 60)} minutes"
            elif time_to_resolve < 24:
                return f"{round(time_to_resolve, 1)} hours"
            else:
                return f"{round(time_to_resolve / 24, 1)} days"
        return "Not resolved"
    time_to_resolve_display.short_description = 'Time to Resolve'
    
    fieldsets = (
        ('Issue Overview', {
            'fields': ('session', 'call_log', 'issue_type', 'priority', 'title')
        }),
        ('Issue Details', {
            'fields': ('description', 'steps_to_reproduce', 'expected_behavior', 'actual_behavior')
        }),
        ('Reporting Info', {
            'fields': ('reported_by', 'reported_at')
        }),
        ('Resolution', {
            'fields': ('resolved', 'resolution_notes', 'resolved_by', 'resolved_at', 'time_to_resolve_display'),
            'classes': ('collapse',)
        }),
    )

# Register all models with the default admin site as well
admin.site.register(Category, CategoryAdmin)
admin.site.register(Professional, ProfessionalAdmin)
admin.site.register(ProfessionalAvailability, ProfessionalAvailabilityAdmin)
admin.site.register(ProfessionalDocument, ProfessionalDocumentAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(SessionBooking, SessionBookingAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Dispute, DisputeAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(CallLog, CallLogAdmin)
admin.site.register(CallAnalytics, CallAnalyticsAdmin)
admin.site.register(CallRecording, CallRecordingAdmin)
admin.site.register(CallIssueReport, CallIssueReportAdmin)