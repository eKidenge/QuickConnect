from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from .models import *

# Inline Admin Classes
class SubCategoryInline(admin.TabularInline):
    model = SubCategory
    extra = 1
    fields = ['name', 'description', 'enabled', 'created_at']
    readonly_fields = ['created_at']

class ProfessionalCategoryInline(admin.TabularInline):
    model = ProfessionalCategory
    extra = 1
    fields = ['category', 'is_primary', 'years_experience', 'rate_override', 'verified']
    autocomplete_fields = ['category']

class ProfessionalSpecializationInline(admin.TabularInline):
    model = ProfessionalSpecialization
    extra = 1
    fields = ['category', 'name', 'description']
    autocomplete_fields = ['category']

class ProfessionalAvailabilityInline(admin.TabularInline):
    model = ProfessionalAvailability
    extra = 7  # One for each day of the week
    fields = ['day_of_week', 'start_time', 'end_time', 'is_available']
    max_num = 7

class ProfessionalDocumentInline(admin.TabularInline):
    model = ProfessionalDocument
    extra = 1
    fields = ['document_type', 'file', 'verified', 'uploaded_at']
    readonly_fields = ['uploaded_at']

class SessionInline(admin.TabularInline):
    model = Session
    extra = 0
    fields = ['client_id', 'session_type', 'status', 'created_at']
    readonly_fields = ['created_at']
    show_change_link = True

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    fields = ['sender_type', 'message_type', 'message', 'timestamp', 'read']
    readonly_fields = ['timestamp']
    max_num = 5

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = ['amount', 'status', 'payment_method', 'created_at']
    readonly_fields = ['created_at']
    max_num = 1

class CallLogInline(admin.TabularInline):
    model = CallLog
    extra = 0
    fields = ['call_type', 'status', 'start_time', 'duration', 'call_quality']
    readonly_fields = ['start_time']
    max_num = 3

class CallIssueReportInline(admin.TabularInline):
    model = CallIssueReport
    extra = 0
    fields = ['issue_type', 'priority', 'title', 'resolved']
    max_num = 2

# ModelAdmin Classes
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'icon', 'base_price', 'professional_count', 
        'session_count', 'avg_response_time', 'is_featured', 
        'enabled', 'sort_order', 'created_at'
    ]
    list_filter = [
        'enabled', 'is_featured', 'created_at', 'updated_at'
    ]
    search_fields = ['name', 'description']
    list_editable = ['sort_order', 'is_featured', 'enabled']
    readonly_fields = [
        'professional_count', 'session_count', 'created_at', 
        'updated_at', 'stats_preview'
    ]
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'name', 'description', 'base_price', 'enabled'
            ]
        }),
        ('UI & Display', {
            'fields': [
                'icon', 'color', 'sort_order', 'is_featured'
            ]
        }),
        ('Statistics', {
            'fields': [
                'professional_count', 'session_count', 
                'avg_response_time', 'stats_preview'
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at', 'updated_at'
            ],
            'classes': ['collapse']
        })
    ]
    inlines = [SubCategoryInline]
    actions = ['update_statistics', 'enable_categories', 'disable_categories']

    def professional_count(self, obj):
        return obj.professionals.count()
    professional_count.short_description = "Professionals"

    def session_count(self, obj):
        return Session.objects.filter(category=obj).count()
    session_count.short_description = "Sessions"

    def stats_preview(self, obj):
        return format_html(
            "<b>Professionals:</b> {} | <b>Sessions:</b> {} | <b>Avg Response:</b> {} min",
            self.professional_count(obj), self.session_count(obj), obj.avg_response_time
        )
    stats_preview.short_description = "Current Statistics"

    def update_statistics(self, request, queryset):
        for category in queryset:
            # Update any custom statistics logic here
            pass
        self.message_user(request, f"Updated statistics for {queryset.count()} categories.")
    update_statistics.short_description = "Update selected categories statistics"

    def enable_categories(self, request, queryset):
        updated = queryset.update(enabled=True)
        self.message_user(request, f"Enabled {updated} categories.")
    enable_categories.short_description = "Enable selected categories"

    def disable_categories(self, request, queryset):
        updated = queryset.update(enabled=False)
        self.message_user(request, f"Disabled {updated} categories.")
    disable_categories.short_description = "Disable selected categories"

class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'enabled', 'created_at']
    list_filter = ['category', 'enabled', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    list_select_related = ['category']
    autocomplete_fields = ['category']

class ProfessionalAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'primary_category', 'status', 'online_status', 
        'available', 'average_rating', 'total_sessions', 
        'rate', 'created_at', 'status_badge'
    ]
    list_filter = [
        'status', 'available', 'online_status', 'primary_category',
        'created_at', 'approved_at'
    ]
    search_fields = [
        'name', 'specialization', 'email', 'phone', 
        'primary_category__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'approved_at', 'rejected_at',
        'stats_summary', 'availability_status'
    ]
    list_editable = ['status', 'available']
    
    fieldsets = [
        ('Basic Information', {
            'fields': [
                'user', 'name', 'title', 'specialization',
                'primary_category', 'subcategories'
            ]
        }),
        ('Contact Information', {
            'fields': [
                'email', 'phone', 'profile_picture'
            ]
        }),
        ('Professional Details', {
            'fields': [
                'bio', 'experience_years', 'languages',
                'education', 'certifications'
            ]
        }),
        ('Rates & Pricing', {
            'fields': [
                'rate', 'chat_rate', 'voice_rate', 'video_rate'
            ]
        }),
        ('Availability & Status', {
            'fields': [
                'status', 'available', 'online_status', 
                'max_simultaneous_sessions', 'availability_status'
            ]
        }),
        ('Statistics', {
            'fields': [
                'average_rating', 'total_sessions', 'total_reviews',
                'avg_response_time', 'total_calls', 'total_call_duration',
                'stats_summary'
            ]
        }),
        ('Approval Information', {
            'fields': [
                'approved_at', 'rejection_reason', 'rejected_at'
            ],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': [
                'created_at', 'updated_at'
            ],
            'classes': ['collapse']
        })
    ]
    
    filter_horizontal = ['subcategories']
    
    inlines = [
        ProfessionalCategoryInline,
        ProfessionalSpecializationInline,
        ProfessionalAvailabilityInline,
        ProfessionalDocumentInline,
        SessionInline
    ]
    actions = [
        'approve_professionals', 'reject_professionals', 
        'suspend_professionals', 'update_online_status'
    ]

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'suspended': 'gray'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = "Status"

    def stats_summary(self, obj):
        return format_html(
            "<b>Rating:</b> {} ⭐ | <b>Sessions:</b> {} | <b>Response Time:</b> {} min",
            obj.average_rating or 0, obj.total_sessions or 0, obj.avg_response_time or 0
        )
    stats_summary.short_description = "Performance Summary"

    def availability_status(self, obj):
        if obj.available and obj.online_status:
            return format_html('<span style="color: green;">● Available</span>')
        else:
            return format_html('<span style="color: red;">● Busy</span>')
    availability_status.short_description = "Current Availability"

    def approve_professionals(self, request, queryset):
        updated = queryset.update(
            status='approved', 
            approved_at=timezone.now(),
            rejection_reason=''
        )
        self.message_user(request, f"Approved {updated} professionals.")
    approve_professionals.short_description = "Approve selected professionals"

    def reject_professionals(self, request, queryset):
        updated = queryset.update(
            status='rejected',
            rejected_at=timezone.now()
        )
        self.message_user(request, f"Rejected {updated} professionals.")
    reject_professionals.short_description = "Reject selected professionals"

    def suspend_professionals(self, request, queryset):
        updated = queryset.update(status='suspended')
        self.message_user(request, f"Suspended {updated} professionals.")
    suspend_professionals.short_description = "Suspend selected professionals"

    def update_online_status(self, request, queryset):
        updated = queryset.update(online_status=True)
        self.message_user(request, f"Updated online status for {updated} professionals.")
    update_online_status.short_description = "Set selected professionals online"

class ProfessionalCategoryAdmin(admin.ModelAdmin):
    list_display = ['professional', 'category', 'is_primary', 'years_experience', 'verified']
    list_filter = ['is_primary', 'verified', 'category']
    search_fields = ['professional__name', 'category__name']
    autocomplete_fields = ['professional', 'category']
    list_editable = ['is_primary', 'verified']

class ProfessionalSpecializationAdmin(admin.ModelAdmin):
    list_display = ['professional', 'category', 'name']
    list_filter = ['category']
    search_fields = ['professional__name', 'name', 'category__name']
    autocomplete_fields = ['professional', 'category']

class ProfessionalAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['professional', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']
    search_fields = ['professional__name']
    autocomplete_fields = ['professional']

class ProfessionalDocumentAdmin(admin.ModelAdmin):
    list_display = ['professional', 'document_type', 'verified', 'uploaded_at']
    list_filter = ['document_type', 'verified', 'uploaded_at']
    search_fields = ['professional__name']
    readonly_fields = ['uploaded_at']
    list_editable = ['verified']

class SessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'professional', 'client_id', 'session_type', 
        'status', 'duration', 'cost', 'created_at', 'status_badge'
    ]
    list_filter = [
        'session_type', 'status', 'category', 'created_at',
        'call_quality'
    ]
    search_fields = [
        'professional__name', 'client_id', 'room_id'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'actual_start', 'ended_at',
        'session_duration', 'financial_summary'
    ]
    fieldsets = [
        ('Session Information', {
            'fields': [
                'professional', 'client_id', 'session_type', 'status',
                'category', 'room_id'
            ]
        }),
        ('Timing', {
            'fields': [
                'scheduled_start', 'actual_start', 'ended_at',
                'duration', 'call_duration', 'session_duration'
            ]
        }),
        ('Financials', {
            'fields': [
                'rate_used', 'cost', 'financial_summary'
            ]
        }),
        ('Call Quality', {
            'fields': [
                'call_quality', 'call_issues'
            ]
        }),
        ('Ratings & Reviews', {
            'fields': [
                'client_rating', 'client_review'
            ]
        }),
        ('Timestamps', {
            'fields': [
                'created_at', 'updated_at'
            ],
            'classes': ['collapse']
        })
    ]
    
    inlines = [PaymentInline, ChatMessageInline, CallLogInline]
    
    actions = ['mark_completed', 'mark_cancelled', 'export_session_data']

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'active': 'blue',
            'completed': 'green',
            'cancelled': 'red',
            'disconnected': 'purple'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = "Status"

    def session_duration(self, obj):
        if obj.actual_start and obj.ended_at:
            duration = (obj.ended_at - obj.actual_start).total_seconds() / 60
            return f"{duration:.1f} minutes"
        return "N/A"
    session_duration.short_description = "Actual Duration"

    def financial_summary(self, obj):
        return format_html(
            "<b>Rate:</b> ${}/min | <b>Total Cost:</b> ${} | <b>Duration:</b> {} min",
            obj.rate_used or 0, obj.cost or 0, obj.duration or 0
        )
    financial_summary.short_description = "Financial Summary"

    def mark_completed(self, request, queryset):
        updated = queryset.update(status='completed', ended_at=timezone.now())
        self.message_user(request, f"Marked {updated} sessions as completed.")
    mark_completed.short_description = "Mark selected sessions as completed"

    def mark_cancelled(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f"Marked {updated} sessions as cancelled.")
    mark_cancelled.short_description = "Mark selected sessions as cancelled"

    def export_session_data(self, request, queryset):
        self.message_user(request, "Export functionality would be implemented here.")
    export_session_data.short_description = "Export session data"

class SessionBookingAdmin(admin.ModelAdmin):
    list_display = ['session', 'booked_by', 'scheduled_for', 'booked_at']
    list_filter = ['scheduled_for', 'booked_at']
    search_fields = ['session__professional__name', 'booked_by']
    autocomplete_fields = ['session']
    readonly_fields = ['booked_at']

class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'session', 'amount', 'status', 'payment_method',
        'created_at', 'status_badge'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = [
        'session__professional__name', 
        'session__client_id',
        'transaction_id'
    ]
    readonly_fields = ['created_at', 'completed_at']
    list_editable = ['status']
    actions = ['mark_completed', 'mark_failed', 'process_refunds']

    def status_badge(self, obj):
        colors = {
            'pending': 'orange',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'blue'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = "Status"

    def mark_completed(self, request, queryset):
        updated = queryset.update(
            status='completed', 
            completed_at=timezone.now()
        )
        self.message_user(request, f"Marked {updated} payments as completed.")
    mark_completed.short_description = "Mark selected payments as completed"

    def mark_failed(self, request, queryset):
        updated = queryset.update(status='failed')
        self.message_user(request, f"Marked {updated} payments as failed.")
    mark_failed.short_description = "Mark selected payments as failed"

    def process_refunds(self, request, queryset):
        self.message_user(request, "Refund processing would be implemented here.")
    process_refunds.short_description = "Process refunds for selected payments"

class DisputeAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'session', 'status', 'created_by', 
        'created_at', 'status_badge'
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'session__professional__name', 'created_by']
    readonly_fields = ['created_at', 'resolved_at']
    list_editable = ['status']
    
    actions = ['resolve_disputes', 'close_disputes']

    def status_badge(self, obj):
        colors = {
            'open': 'red',
            'in_progress': 'orange',
            'resolved': 'green',
            'closed': 'gray'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display().upper()
        )
    status_badge.short_description = "Status"

    def resolve_disputes(self, request, queryset):
        updated = queryset.update(
            status='resolved',
            resolved_at=timezone.now()
        )
        self.message_user(request, f"Resolved {updated} disputes.")
    resolve_disputes.short_description = "Resolve selected disputes"

    def close_disputes(self, request, queryset):
        updated = queryset.update(status='closed')
        self.message_user(request, f"Closed {updated} disputes.")
    close_disputes.short_description = "Close selected disputes"

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'sender_type', 'message_type', 
        'timestamp', 'read', 'message_preview'
    ]
    list_filter = ['sender_type', 'message_type', 'read']  # removed timestamp
    search_fields = [
        'session__professional__name', 
        'session__client_id',
        'message'
    ]
    readonly_fields = ['timestamp', 'created_at']
    list_editable = ['read']

    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = "Message"

class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'user_type', 'phone', 'location', 
        'created_at', 'user_type_badge'
    ]
    list_filter = ['user_type', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'location']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['user_type']

    def user_type_badge(self, obj):
        colors = {
            'client': 'blue',
            'professional': 'green',
            'admin': 'red'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.user_type, 'gray'),
            obj.get_user_type_display().upper()
        )
    user_type_badge.short_description = "User Type"

class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'notification_type', 'read', 
        'priority', 'created_at', 'read_status'
    ]
    list_filter = [
        'notification_type', 'read', 'priority', 'created_at'
    ]
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']
    list_editable = ['read', 'priority']
    actions = ['mark_as_read', 'mark_as_unread']

    def read_status(self, obj):
        if obj.read:
            return format_html('<span style="color: green;">✓ Read</span>')
        else:
            return format_html('<span style="color: orange;">● Unread</span>')
    read_status.short_description = "Read Status"

    def mark_as_read(self, request, queryset):
        updated = queryset.update(read=True)
        self.message_user(request, f"Marked {updated} notifications as read.")
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(read=False)
        self.message_user(request, f"Marked {updated} notifications as unread.")
    mark_as_unread.short_description = "Mark selected as unread"

class CallLogAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'call_type', 'status', 'start_time',
        'duration_minutes', 'call_quality', 'has_technical_issues'
    ]
    list_filter = [
        'call_type', 'status', 'call_quality', 'start_time'
    ]
    search_fields = [
        'session__professional__name',
        'session__client_id'
    ]
    readonly_fields = ['start_time', 'end_time']
    inlines = [CallIssueReportInline]

    def duration_minutes(self, obj):
        if obj.duration:
            return f"{obj.duration / 60:.1f} min"
        return "N/A"
    duration_minutes.short_description = "Duration"

    def has_technical_issues(self, obj):
        return obj.call_issues.exists()
    has_technical_issues.boolean = True
    has_technical_issues.short_description = "Tech Issues"

class CallAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'professional', 'date', 'total_calls', 'completed_calls',
        'success_rate', 'average_duration', 'average_quality_score'
    ]
    list_filter = ['date', 'professional']
    search_fields = ['professional__name']
    readonly_fields = [
        'created_at', 'updated_at', 'success_rate', 
        'issue_rate', 'analytics_summary'
    ]

    def success_rate(self, obj):
        if obj.total_calls > 0:
            return f"{(obj.completed_calls / obj.total_calls) * 100:.1f}%"
        return "0%"
    success_rate.short_description = "Success Rate"

    def average_duration(self, obj):
        return f"{obj.avg_call_duration:.1f} min"
    average_duration.short_description = "Avg Duration"

    def average_quality_score(self, obj):
        return f"{obj.avg_quality_score:.1f}/5"
    average_quality_score.short_description = "Avg Quality"

    def issue_rate(self, obj):
        if obj.total_calls > 0:
            return f"{(obj.technical_issues / obj.total_calls) * 100:.1f}%"
        return "0%"
    issue_rate.short_description = "Issue Rate"

    def analytics_summary(self, obj):
        return format_html(
            "<b>Success Rate:</b> {} | <b>Avg Duration:</b> {} | <b>Issue Rate:</b> {}",
            self.success_rate(obj), self.average_duration(obj), self.issue_rate(obj)
        )
    analytics_summary.short_description = "Analytics Summary"

class CallRecordingAdmin(admin.ModelAdmin):
    list_display = [
        'session', 'status', 'duration_minutes', 
        'file_size_mb', 'client_consent', 'professional_consent',
        'created_at'
    ]
    list_filter = ['status', 'storage_location', 'created_at']
    search_fields = ['session__professional__name', 'session__client_id']
    readonly_fields = [
        'created_at', 'processed_at', 'file_size_mb', 
        'duration_minutes'
    ]
    list_editable = ['status']

    def duration_minutes(self, obj):
        if obj.duration:
            return f"{obj.duration / 60:.1f} min"
        return "N/A"
    duration_minutes.short_description = "Duration"

    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "N/A"
    file_size_mb.short_description = "File Size"

class CallIssueReportAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'session', 'issue_type', 'priority',
        'resolved', 'reported_at', 'priority_badge'
    ]
    list_filter = [
        'issue_type', 'priority', 'resolved', 'reported_at'
    ]
    search_fields = [
        'title', 'session__professional__name',
        'session__client_id'
    ]
    readonly_fields = ['reported_at', 'resolved_at']
    list_editable = ['priority', 'resolved']
    actions = ['mark_resolved', 'mark_high_priority']

    def priority_badge(self, obj):
        colors = {
            'low': 'gray',
            'medium': 'blue',
            'high': 'orange',
            'critical': 'red'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px;">{}</span>',
            colors.get(obj.priority, 'gray'),
            obj.get_priority_display().upper()
        )
    priority_badge.short_description = "Priority"

    def mark_resolved(self, request, queryset):
        updated = queryset.update(
            resolved=True,
            resolved_at=timezone.now()
        )
        self.message_user(request, f"Marked {updated} issues as resolved.")
    mark_resolved.short_description = "Mark selected issues as resolved"

    def mark_high_priority(self, request, queryset):
        updated = queryset.update(priority='high')
        self.message_user(request, f"Marked {updated} issues as high priority.")
    mark_high_priority.short_description = "Mark selected as high priority"

# Custom User Admin to include profile inline
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = UserAdmin.list_display + ('get_user_type', 'get_phone', 'get_joined_date')
    
    def get_user_type(self, obj):
        try:
            return obj.userprofile.user_type
        except UserProfile.DoesNotExist:
            return "No profile"
    get_user_type.short_description = 'User Type'
    
    def get_phone(self, obj):
        try:
            return obj.userprofile.phone
        except UserProfile.DoesNotExist:
            return "No phone"
    get_phone.short_description = 'Phone'

    def get_joined_date(self, obj):
        try:
            return obj.userprofile.created_at
        except UserProfile.DoesNotExist:
            return "No profile"
    get_joined_date.short_description = 'Profile Created'

# Register all models with custom admin
admin.site.register(Category, CategoryAdmin)
admin.site.register(SubCategory, SubCategoryAdmin)
admin.site.register(Professional, ProfessionalAdmin)
admin.site.register(ProfessionalCategory, ProfessionalCategoryAdmin)
admin.site.register(ProfessionalSpecialization, ProfessionalSpecializationAdmin)
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

# Re-register User with custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Admin site customization
admin.site.site_header = "TeleConnect Administration"
admin.site.site_title = "TeleConnect Admin Portal"
admin.site.index_title = "Welcome to TeleConnect Administration"