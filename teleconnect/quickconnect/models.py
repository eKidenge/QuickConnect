from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enabled = models.BooleanField(default=True)
    professional_count = models.IntegerField(default=0)
    session_count = models.IntegerField(default=0)
    
    # Enhanced fields for better UI and filtering
    icon = models.CharField(max_length=50, blank=True, null=True)
    color = models.CharField(max_length=7, default='#6B7280')
    avg_response_time = models.IntegerField(default=5)
    is_featured = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['sort_order', 'name']
    
    def update_stats(self):
        """Update calculated statistics for this category"""
        # Update professional count
        self.professional_count = Professional.objects.filter(
            Q(category=self) | Q(categories=self) | Q(primary_category=self),
            status='approved'
        ).distinct().count()
        
        # Update session count
        self.session_count = Session.objects.filter(category=self).count()
        
        # Calculate average response time
        if self.session_count > 0:
            if self.session_count > 100:
                self.avg_response_time = 1
            elif self.session_count > 50:
                self.avg_response_time = 2
            elif self.session_count > 20:
                self.avg_response_time = 3
            else:
                self.avg_response_time = 5
        else:
            self.avg_response_time = 5
            
        self.save()


class SubCategory(models.Model):
    """Subcategories for more specific professional classification"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "SubCategories"
        unique_together = ['category', 'name']
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class Professional(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]
    
    # User relationship
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    
    # Category relationships
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='professionals')
    categories = models.ManyToManyField(Category, through='ProfessionalCategory', related_name='multi_category_professionals', blank=True)
    primary_category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='primary_professionals')
    subcategories = models.ManyToManyField(SubCategory, blank=True, related_name='professionals')
    
    # Rates and pricing
    rate = models.DecimalField(max_digits=6, decimal_places=2, default=50.00)
    
    # Session-specific rates
    chat_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    voice_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    video_rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Availability and status
    available = models.BooleanField(default=True)
    online_status = models.BooleanField(default=False)
    locked_by = models.CharField(max_length=100, null=True, blank=True)
    
    # Enhanced locking with timeout
    locked_until = models.DateTimeField(null=True, blank=True)
    max_simultaneous_sessions = models.IntegerField(default=1)
    
    # Status management
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Contact info
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Professional details
    experience_years = models.IntegerField(default=0)
    bio = models.TextField(blank=True, null=True)
    
    # Enhanced professional details
    title = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='professional_profiles/', blank=True, null=True)
    languages = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    
    # Ratings and stats
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_sessions = models.IntegerField(default=0)
    total_reviews = models.IntegerField(default=0)
    
    # Response time tracking
    avg_response_time = models.CharField(max_length=20, default='< 4 hours')
    
    # NEW FIELDS FROM VIEWS:
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=95.00)  # Percentage
    current_workload = models.IntegerField(default=0)
    max_workload = models.IntegerField(default=10)
    last_active = models.DateTimeField(auto_now=True)
    
    # Call tracking fields
    total_calls = models.IntegerField(default=0)
    total_call_duration = models.IntegerField(default=0)
    current_call = models.ForeignKey('Session', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_professional_call')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        # Ensure primary category is set if not provided
        if not self.primary_category and self.category:
            self.primary_category = self.category
        
        # Ensure the professional is in their primary category
        if self.primary_category and self.primary_category not in self.categories.all():
            self.categories.add(self.primary_category)
            
        super().save(*args, **kwargs)
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_available_for_session(self):
        """Check if professional can accept new sessions"""
        if not self.available or not self.online_status:
            return False
        
        # Check if professional is locked
        if self.locked_until and self.locked_until > timezone.now():
            return False
        
        # Check current session count
        active_sessions = self.sessions.filter(
            status__in=['active', 'in_progress', 'pending']
        ).count()
        
        return active_sessions < self.max_simultaneous_sessions
    
    @property
    def display_rate(self):
        """Get display rate for UI"""
        return self.rate
    
    def get_rate_for_session_type(self, session_type):
        """Get rate for specific session type"""
        rates = {
            'chat': self.chat_rate or self.rate,
            'audio': self.voice_rate or self.rate,
            'video': self.video_rate or self.rate,
        }
        return rates.get(session_type, self.rate)
    
    def lock_for_session(self, client_id, duration_minutes=5):
        """Lock professional for a session"""
        if self.is_available_for_session:
            self.locked_by = client_id
            self.locked_until = timezone.now() + timezone.timedelta(minutes=duration_minutes)
            self.save()
            return True
        return False
    
    def release_lock(self):
        """Release professional lock"""
        self.locked_by = None
        self.locked_until = None
        self.save()
    
    @property
    def average_call_duration(self):
        """Average call duration in minutes"""
        if self.total_calls > 0 and self.total_call_duration > 0:
            return round(self.total_call_duration / self.total_calls / 60, 1)
        return 0


class ProfessionalCategory(models.Model):
    """Through model for professional-category relationship with additional data"""
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    
    # Category-specific professional details
    is_primary = models.BooleanField(default=False)
    years_experience = models.IntegerField(default=0)
    certification = models.CharField(max_length=200, blank=True, null=True)
    verified = models.BooleanField(default=False)
    
    # Rates for this specific category
    rate_override = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['professional', 'category']
        verbose_name_plural = "Professional Categories"
    
    def __str__(self):
        return f"{self.professional.name} - {self.category.name}"


class ProfessionalSpecialization(models.Model):
    """Professional's specializations within categories"""
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='specializations')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['professional', 'category', 'name']
    
    def __str__(self):
        return f"{self.professional.name} - {self.category.name}: {self.name}"


class ProfessionalAvailability(models.Model):
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='availability')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.professional.name} - {self.get_day_of_week_display()}"


class ProfessionalDocument(models.Model):
    DOCUMENT_TYPES = [
        ('license', 'Professional License'),
        ('certificate', 'Certificate'),
        ('id_proof', 'ID Proof'),
        ('resume', 'Resume'),
        ('other', 'Other'),
    ]
    
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    file = models.FileField(upload_to='professional_docs/')
    verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.professional.name} - {self.get_document_type_display()}"


class Session(models.Model):
    SESSION_TYPES = [
        ('chat', 'Chat'),
        ('audio', 'Audio Call'),
        ('video', 'Video Call'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('disconnected', 'Disconnected'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('declined', 'Declined'),
        ('in_progress', 'In Progress'),
    ]
    
    CALL_QUALITY_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('failed', 'Failed'),
    ]
    
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='sessions')
    client_id = models.IntegerField()  # Changed from CharField to IntegerField to match views usage
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES, default='chat')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='pending')
    
    # Category relationship for better filtering
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='sessions')
    
    # Timing
    scheduled_start = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Financials
    duration = models.IntegerField(default=0)
    cost = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Rate tracking
    rate_used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    # Ratings - CHANGED: Using simpler field names to match views
    rating = models.IntegerField(
        null=True, 
        blank=True, 
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    review = models.TextField(blank=True, null=True)
    
    # Enhanced Call-specific fields
    room_id = models.CharField(max_length=100, blank=True, null=True)
    call_started_at = models.DateTimeField(null=True, blank=True)
    call_ended_at = models.DateTimeField(null=True, blank=True)
    call_duration = models.IntegerField(default=0)
    
    # Call quality tracking
    call_quality = models.CharField(max_length=10, choices=CALL_QUALITY_CHOICES, null=True, blank=True)
    call_issues = models.JSONField(default=list, blank=True)
    
    # NEW FIELDS FROM VIEWS:
    urgency = models.CharField(max_length=20, default='medium', choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')])
    mode = models.CharField(max_length=20, blank=True, null=True)  # Alias for session_type in some views
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.professional.name} - {self.client_id} - {self.session_type}"
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Auto-set category from professional if not set
        if not self.category and self.professional.primary_category:
            self.category = self.professional.primary_category
        
        # Auto-set rate used
        if not self.rate_used and self.professional:
            self.rate_used = self.professional.get_rate_for_session_type(self.session_type)
        
        # Set mode to session_type if not set
        if not self.mode:
            self.mode = self.session_type
            
        super().save(*args, **kwargs)
    
    @property
    def is_active(self):
        return self.status in ['active', 'in_progress']
    
    @property
    def total_duration(self):
        if self.actual_start and self.ended_at:
            return (self.ended_at - self.actual_start).total_seconds() / 60
        return self.duration
    
    @property
    def call_duration_minutes(self):
        return round(self.call_duration / 60, 1) if self.call_duration else 0
    
    @property
    def has_call_issues(self):
        return len(self.call_issues) > 0 if self.call_issues else False


class SessionBooking(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='booking')
    booked_by = models.CharField(max_length=100)
    booked_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Booking for {self.session}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('wallet', 'Digital Wallet'),
        ('mpesa', 'M-Pesa'),  # ADDED: For Kenyan mobile payments
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # NEW FIELDS FROM VIEWS:
    checkout_request_id = models.CharField(max_length=100, blank=True, null=True)  # For M-Pesa
    phone_number = models.CharField(max_length=20, blank=True, null=True)  # For M-Pesa
    receipt_number = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment #{self.id} - ${self.amount}"
    
    @property
    def is_successful(self):
        return self.status == 'completed'


class Dispute(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='disputes')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='open')
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Dispute: {self.title}"
    
    @property
    def time_to_resolve(self):
        if self.resolved_at and self.created_at:
            return (self.resolved_at - self.created_at).total_seconds() / 3600
        return None


class ChatMessage(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('system', 'System'),
    ]
    
    SENDER_TYPES = [
        ('client', 'Client'),
        ('professional', 'Professional'),
        ('system', 'System'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    message_id = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField()
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPES)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    
    # CHANGED: Using created_at instead of timestamp to match views
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    
    # NEW FIELD FROM VIEWS:
    content = models.TextField(blank=True)  # Alias for message in some views
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender_type}: {self.message[:50]}..."
    
    def save(self, *args, **kwargs):
        # Set content to message if not set
        if not self.content and self.message:
            self.content = self.message
        super().save(*args, **kwargs)
    
    @property
    def text(self):
        return self.message
    
    @property
    def sender(self):
        return self.sender_type
    
    @property
    def timestamp(self):
        return self.created_at


class UserProfile(models.Model):
    USER_TYPE_CHOICES = [
        ('client', 'Client'),
        ('professional', 'Professional'),
        ('admin', 'Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    favorite_professionals = models.JSONField(default=list)
    
    # Enhanced user profile fields
    location = models.CharField(max_length=100, blank=True, null=True)
    timezone = models.CharField(max_length=50, default='UTC')
    notification_preferences = models.JSONField(default=dict, blank=True)
    
    # NEW FIELDS FROM VIEWS:
    preferences = models.JSONField(default=dict, blank=True)  # User preferences for matching
    notification_settings = models.JSONField(default=dict, blank=True)  # Notification settings
    is_verified = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile: {self.user.username}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('session_request', 'Session Request'),
        ('session_accepted', 'Session Accepted'),
        ('session_rejected', 'Session Rejected'),
        ('payment_received', 'Payment Received'),
        ('session_reminder', 'Session Reminder'),
        ('system', 'System Notification'),
        ('call_started', 'Call Started'),
        ('call_ended', 'Call Ended'),
        ('call_quality_alert', 'Call Quality Alert'),
        ('professional_approved', 'Professional Approved'),  # ADDED
        ('professional_rejected', 'Professional Rejected'),  # ADDED
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=25, choices=NOTIFICATION_TYPES)  # fixed
    title = models.CharField(max_length=200)
    message = models.TextField()
    read = models.BooleanField(default=False)
    related_session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True)
    
    # Enhanced notification fields
    data = models.JSONField(default=dict, blank=True)
    priority = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    action_url = models.CharField(max_length=500, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"


class CallLog(models.Model):
    CALL_TYPES = [
        ('audio', 'Audio Call'),
        ('video', 'Video Call'),
    ]
    
    CALL_STATUS_CHOICES = [
        ('initiated', 'Initiated'),
        ('connected', 'Connected'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
    ]
    
    CALL_QUALITY_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('failed', 'Failed'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='call_logs')
    call_type = models.CharField(max_length=10, choices=CALL_TYPES)
    status = models.CharField(max_length=10, choices=CALL_STATUS_CHOICES, default='initiated')
    
    # Timing
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)
    
    # Quality metrics
    call_quality = models.CharField(max_length=10, choices=CALL_QUALITY_CHOICES, null=True, blank=True)
    connection_quality = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    audio_issues = models.JSONField(default=list, blank=True)
    video_issues = models.JSONField(default=list, blank=True)
    
    # Technical details
    client_device = models.CharField(max_length=100, blank=True, null=True)
    professional_device = models.CharField(max_length=100, blank=True, null=True)
    network_conditions = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Call {self.id} - {self.session} - {self.status}"
    
    @property
    def duration_minutes(self):
        return round(self.duration / 60, 1) if self.duration else 0
    
    @property
    def has_technical_issues(self):
        return len(self.audio_issues) > 0 or len(self.video_issues) > 0


class CallAnalytics(models.Model):
    professional = models.ForeignKey(Professional, on_delete=models.CASCADE, related_name='call_analytics')
    date = models.DateField()
    
    # Call statistics
    total_calls = models.IntegerField(default=0)
    completed_calls = models.IntegerField(default=0)
    failed_calls = models.IntegerField(default=0)
    missed_calls = models.IntegerField(default=0)
    
    # Duration statistics
    total_duration = models.IntegerField(default=0)
    average_duration = models.FloatField(default=0)
    
    # Quality metrics
    average_quality_score = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    calls_with_issues = models.IntegerField(default=0)
    
    # Performance metrics
    success_rate = models.FloatField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['professional', 'date']
        ordering = ['-date']
        verbose_name_plural = 'Call Analytics'
    
    def __str__(self):
        return f"Analytics - {self.professional.name} - {self.date}"
    
    @property
    def issue_rate(self):
        if self.total_calls > 0:
            return round((self.calls_with_issues / self.total_calls) * 100, 1)
        return 0
    
    @property
    def total_duration_minutes(self):
        return round(self.total_duration / 60, 1)


class CallRecording(models.Model):
    RECORDING_STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('deleted', 'Deleted'),
    ]
    
    session = models.OneToOneField(Session, on_delete=models.CASCADE, related_name='recording')
    call_log = models.ForeignKey(CallLog, on_delete=models.CASCADE, related_name='recordings')
    
    # File information
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.BigIntegerField(default=0)
    duration = models.IntegerField(default=0)
    
    # Status and permissions
    status = models.CharField(max_length=10, choices=RECORDING_STATUS_CHOICES, default='processing')
    storage_location = models.CharField(max_length=100, default='local')
    
    # Privacy and access control
    client_consent = models.BooleanField(default=False)
    professional_consent = models.BooleanField(default=False)
    available_for_download = models.BooleanField(default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recording - {self.session} - {self.status}"
    
    @property
    def file_size_mb(self):
        return round(self.file_size / (1024 * 1024), 2) if self.file_size else 0
    
    @property
    def duration_minutes(self):
        return round(self.duration / 60, 1) if self.duration else 0


class CallIssueReport(models.Model):
    ISSUE_TYPES = [
        ('audio', 'Audio Issue'),
        ('video', 'Video Issue'),
        ('connection', 'Connection Issue'),
        ('lag', 'Lag/Latency'),
        ('other', 'Other Issue'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='issue_reports')
    call_log = models.ForeignKey(CallLog, on_delete=models.CASCADE, related_name='issue_reports')
    
    # Issue details
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Technical details
    steps_to_reproduce = models.TextField(blank=True, null=True)
    expected_behavior = models.TextField(blank=True, null=True)
    actual_behavior = models.TextField(blank=True, null=True)
    
    # Reporting info
    reported_by = models.CharField(max_length=100)
    reported_at = models.DateTimeField(auto_now_add=True)
    
    # Resolution tracking
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank = True, null = True)
    resolved_by = models.CharField(max_length=100, blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-reported_at']
    
    def __str__(self):
        return f"Issue: {self.title} - {self.session}"
    
    @property
    def time_to_resolve(self):
        if self.resolved and self.resolved_at and self.reported_at:
            return (self.resolved_at - self.reported_at).total_seconds() / 3600
        return None


# NEW MODELS FROM VIEWS:

class Receipt(models.Model):
    """Receipt model for payment receipts"""
    receipt_number = models.CharField(max_length=100, unique=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='receipts')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='receipts')
    
    # Receipt details
    client_name = models.CharField(max_length=200)
    professional_name = models.CharField(max_length=200)
    service_type = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=50)
    
    # Timestamps
    issue_date = models.DateField(auto_now_add=True)
    issue_time = models.TimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-issue_date', '-issue_time']
    
    def __str__(self):
        return f"Receipt {self.receipt_number} - {self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f"RCP{timezone.now().strftime('%Y%m%d%H%M%S')}"
        super().save(*args, **kwargs)


class SupportTicket(models.Model):
    """Support ticket model for user support"""
    TICKET_STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    CATEGORY_CHOICES = [
        ('technical', 'Technical Issue'),
        ('billing', 'Billing/Payment'),
        ('session', 'Session Related'),
        ('account', 'Account Issue'),
        ('general', 'General Inquiry'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=12, choices=TICKET_STATUS_CHOICES, default='open')
    
    # Related objects
    related_session = models.ForeignKey(Session, on_delete=models.SET_NULL, null=True, blank=True)
    related_payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket #{self.id} - {self.subject}"


# Signals to maintain data integrity
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q, Count, Sum, Avg

@receiver(post_save, sender=Professional)
def update_professional_categories(sender, instance, created, **kwargs):
    """Ensure professional is in their categories and update stats"""
    if instance.primary_category and instance.primary_category not in instance.categories.all():
        instance.categories.add(instance.primary_category)
    
    # Update category stats
    if instance.primary_category:
        instance.primary_category.update_stats()

@receiver(post_save, sender=Session)
@receiver(post_delete, sender=Session)
def update_category_session_stats(sender, instance, **kwargs):
    """Update category session statistics"""
    if instance.category:
        instance.category.update_stats()

@receiver(post_save, sender=ProfessionalCategory)
@receiver(post_delete, sender=ProfessionalCategory)
def update_category_professional_stats(sender, instance, **kwargs):
    """Update category professional statistics"""
    instance.category.update_stats()

@receiver(post_save, sender=Session)
def update_professional_session_stats(sender, instance, **kwargs):
    """Update professional session statistics"""
    if instance.professional:
        professional = instance.professional
        # Update total sessions
        professional.total_sessions = professional.sessions.count()
        
        # Update average rating if session has rating
        if instance.rating:
            avg_rating = professional.sessions.filter(
                rating__isnull=False
            ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
            professional.average_rating = avg_rating
        
        professional.save()

@receiver(post_save, sender=Payment)
def update_session_payment_status(sender, instance, **kwargs):
    """Update session cost when payment is completed"""
    if instance.status == 'completed' and instance.session.cost == 0:
        instance.session.cost = instance.amount
        instance.session.save()