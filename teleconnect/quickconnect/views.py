from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Sum, Avg, Q, F
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from datetime import timedelta
import json
import os
import uuid
import time
import random
from decimal import Decimal
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings

# ADD THIS IMPORT for token authentication
from rest_framework.authtoken.models import Token

from .models import Professional, Session, Payment, Dispute, Category, UserProfile, ChatMessage, Notification, ProfessionalCategory, SubCategory, ProfessionalAvailability, ProfessionalDocument, CallLog, CallAnalytics, CallRecording, CallIssueReport, SessionBooking

# =====================
# AUTHENTICATION VIEWS
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def api_register(request):
    """User registration API with user_type support"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'user_type']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # Validate user_type
        valid_user_types = ['client', 'professional']
        if data['user_type'] not in valid_user_types:
            return JsonResponse({
                'success': False,
                'message': f'user_type must be one of: {", ".join(valid_user_types)}'
            }, status=400)
        
        # Check if username or email already exists
        if User.objects.filter(username=data['username']).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username already exists'
            }, status=400)
            
        if User.objects.filter(email=data['email']).exists():
            return JsonResponse({
                'success': False,
                'message': 'Email already exists'
            }, status=400)
        
        # Create user
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', '')
        )
        
        # Create user profile with user_type
        user_profile = UserProfile.objects.create(
            user=user,
            user_type=data['user_type'],
            phone=data.get('phone', '')
        )
        
        # If professional, create Professional profile with proper data
        if data['user_type'] == 'professional':
            # Ensure we have a proper name
            full_name = f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
            if not full_name:
                full_name = data['username']
            
            # Create professional with proper data
            professional = Professional.objects.create(
                user=user,
                name=full_name,
                email=data['email'],
                phone=data.get('phone', ''),
                status='pending',
                rate=data.get('rate', 50),
                specialization=data.get('specialization', 'General Consulting'),
                experience_years=data.get('experience_years', 1),
                bio=data.get('bio', ''),
                available=False,
                online_status=False
            )
            
            # Add to categories if provided
            if 'category_id' in data:
                try:
                    category = Category.objects.get(id=data['category_id'])
                    professional.category = category
                    professional.primary_category = category
                    professional.save()
                    
                    # Add to categories through model
                    ProfessionalCategory.objects.create(
                        professional=professional,
                        category=category,
                        is_primary=True
                    )
                except Category.DoesNotExist:
                    pass
        
        return JsonResponse({
            'success': True,
            'message': f'{data["user_type"].title()} account created successfully',
            'user_id': user.id,
            'user_type': data['user_type']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Registration failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def api_login(request):
    """Role-based login API with user_type support AND TOKEN AUTHENTICATION"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # GET OR CREATE TOKEN FOR THE USER
            token, created = Token.objects.get_or_create(user=user)
            
            # Get user profile to determine role with user_type
            try:
                user_profile = UserProfile.objects.get(user=user)
                role = user_profile.user_type
            except UserProfile.DoesNotExist:
                # Fallback to Professional model check if no UserProfile exists
                role = 'client'
                try:
                    professional = Professional.objects.get(user=user)
                    role = 'professional'
                except Professional.DoesNotExist:
                    pass
            
            professional_data = None
            
            # Get professional data if applicable
            if role == 'professional':
                try:
                    professional = Professional.objects.get(user=user)
                    professional_data = {
                        'id': professional.id,
                        'name': professional.name,
                        'specialization': professional.specialization,
                        'category': professional.category.name if professional.category else None,
                        'category_id': professional.category.id if professional.category else None,
                        'status': professional.status,
                        'is_approved': professional.status == 'approved',
                        'rate': float(professional.rate) if professional.rate else 0,
                        'available': professional.available,
                        'online_status': professional.online_status
                    }
                except Professional.DoesNotExist:
                    pass
            
            # Check if user is staff (admin) - admin overrides other roles
            if user.is_staff:
                role = 'admin'
            
            # Get user profile data
            try:
                user_profile = UserProfile.objects.get(user=user)
                profile_data = {
                    'phone': user_profile.phone,
                    'date_of_birth': str(user_profile.date_of_birth) if user_profile.date_of_birth else None,
                    'favorite_professionals': user_profile.favorite_professionals or [],
                    'user_type': user_profile.user_type,
                    'location': user_profile.location,
                    'timezone': user_profile.timezone
                }
            except UserProfile.DoesNotExist:
                profile_data = {
                    'favorite_professionals': [],
                    'user_type': role,
                    'location': None,
                    'timezone': 'UTC'
                }
            
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': role,
                    'user_type': profile_data['user_type'],
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                },
                'professional': professional_data,
                'profile': profile_data,
                'token': token.key,
                'message': 'Login successful'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid username or password'
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Server error: {str(e)}'
        }, status=500)

# =====================
# HOME & BASIC VIEWS
# =====================

def home(request):
    """
    Landing page showing featured professionals.
    """
    return JsonResponse({
        'message': 'Welcome to TeleConnect API',
        'status': 'Server is running',
        'endpoints': {
            'admin_dashboard': '/api/admin/dashboard/stats/',
            'revenue_data': '/api/admin/dashboard/revenue-chart/',
            'recent_activity': '/api/admin/dashboard/recent-activity/',
            'professionals': '/api/professionals/',
            'categories': '/api/categories/',
            'admin_categories': '/api/admin/categories/',
            'user_profile': '/api/user/profile/',
            'user_favorites': '/api/user/favorites/',
            'register': '/api/register/',
            'login': '/api/login/',
            'sessions': '/api/sessions/create/',
            'messages': '/api/messages/send/',
            'video_call': '/api/video/initiate/',
            'voice_call': '/api/voice/initiate/',
            'professional_profile': '/api/professional/profile/',
            'update_professional_profile': '/api/professional/profile/update/{id}/',
        }
    })

# =====================
# PROFESSIONAL MANAGEMENT VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def professional_list(request):
    """Get all available professionals"""
    try:
        professionals = Professional.objects.filter(status='approved', available=True)
        
        # Filter by specialization if query param exists
        specialization = request.GET.get('specialization')
        if specialization:
            professionals = professionals.filter(specialization__icontains=specialization)

        # Filter by category if query param exists
        category_id = request.GET.get('category_id')
        if category_id:
            professionals = professionals.filter(
                Q(category_id=category_id) | 
                Q(categories__id=category_id) |
                Q(primary_category_id=category_id)
            ).distinct()

        # Check if user wants favorites info
        user_id = request.GET.get('user_id')
        user_favorites = []
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                user_profile = UserProfile.objects.get(user=user)
                user_favorites = user_profile.favorite_professionals or []
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                pass

        professionals_data = []
        for pro in professionals:
            # Get all categories for this professional
            all_categories = []
            if pro.primary_category:
                all_categories.append({
                    'id': pro.primary_category.id,
                    'name': pro.primary_category.name,
                    'is_primary': True
                })
            
            for cat in pro.categories.all():
                if cat != pro.primary_category:
                    all_categories.append({
                        'id': cat.id,
                        'name': cat.name,
                        'is_primary': False
                    })
            
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'available': pro.available,
                'online_status': pro.online_status,
                'category': pro.primary_category.name if pro.primary_category else 'General',
                'categories': all_categories,
                'average_rating': float(pro.average_rating),
                'total_sessions': pro.total_sessions,
                'experience_years': pro.experience_years,
                'email': pro.email,
                'phone': pro.phone,
                'is_favorite': pro.id in user_favorites if user_id else False,
                'avg_response_time': pro.avg_response_time
            })
            
        return JsonResponse({
            'professionals': professionals_data,
            'count': professionals.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_detail_api(request, professional_id):
    """Get detailed information about a specific professional"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Calculate detailed stats
        sessions_count = Session.objects.filter(professional=professional).count()
        completed_sessions = Session.objects.filter(professional=professional, status='completed').count()
        
        # Calculate revenue
        revenue_agg = Session.objects.filter(professional=professional, status='completed').aggregate(total_revenue=Sum('cost'))
        total_revenue = revenue_agg['total_revenue'] or 0
        
        # Get all categories
        all_categories = []
        if professional.primary_category:
            all_categories.append({
                'id': professional.primary_category.id,
                'name': professional.primary_category.name,
                'is_primary': True
            })
        
        for cat in professional.categories.all():
            if cat != professional.primary_category:
                all_categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_primary': False
                })
        
        # Recent sessions
        recent_sessions = Session.objects.filter(professional=professional).order_by('-created_at')[:10]
        sessions_data = []
        for session in recent_sessions:
            sessions_data.append({
                'id': session.id,
                'client_id': session.client_id,
                'session_type': session.session_type,
                'status': session.status,
                'duration': session.duration,
                'cost': float(session.cost),
                'created_at': session.created_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None
            })
        
        # Professional documents
        documents = ProfessionalDocument.objects.filter(professional=professional)
        documents_data = []
        for doc in documents:
            documents_data.append({
                'id': doc.id,
                'document_type': doc.document_type,
                'verified': doc.verified,
                'uploaded_at': doc.uploaded_at.isoformat()
            })
        
        response_data = {
            'id': professional.id,
            'name': professional.name,
            'specialization': professional.specialization,
            'rate': float(professional.rate),
            'status': professional.status,
            'available': professional.available,
            'online_status': professional.online_status,
            'email': professional.email,
            'phone': professional.phone,
            'category': professional.primary_category.name if professional.primary_category else 'General',
            'categories': all_categories,
            'average_rating': float(professional.average_rating),
            'total_sessions': professional.total_sessions,
            'experience_years': professional.experience_years,
            'bio': professional.bio,
            'title': professional.title,
            'languages': professional.languages,
            'education': professional.education,
            'certifications': professional.certifications,
            'approved_at': professional.approved_at.isoformat() if professional.approved_at else None,
            'rejected_at': professional.rejected_at.isoformat() if professional.rejected_at else None,
            'rejection_reason': professional.rejection_reason,
            'created_at': professional.created_at.isoformat(),
            'stats': {
                'sessions_count': sessions_count,
                'completed_sessions': completed_sessions,
                'total_revenue': float(total_revenue),
                'success_rate': round((completed_sessions / sessions_count * 100) if sessions_count > 0 else 0, 2)
            },
            'recent_sessions': sessions_data,
            'documents': documents_data
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_dashboard(request, professional_id):
    """Professional dashboard page"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Get professional stats
        total_sessions = Session.objects.filter(professional=professional).count()
        completed_sessions = Session.objects.filter(professional=professional, status='completed').count()
        
        # Calculate revenue
        revenue_agg = Session.objects.filter(professional=professional, status='completed').aggregate(total_revenue=Sum('cost'))
        total_earnings = revenue_agg['total_revenue'] or 0
        
        # Today's earnings
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_earnings_agg = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__gte=today_start
        ).aggregate(total_earnings=Sum('cost'))
        today_earnings = today_earnings_agg['total_earnings'] or 0
        
        # Recent sessions
        recent_sessions = Session.objects.filter(professional=professional).order_by('-created_at')[:5]
        sessions_data = []
        for session in recent_sessions:
            sessions_data.append({
                'id': session.id,
                'client_id': session.client_id,
                'session_type': session.session_type,
                'status': session.status,
                'duration': session.duration,
                'cost': float(session.cost),
                'created_at': session.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return JsonResponse({
            'professional': {
                'id': professional.id,
                'name': professional.name,
                'specialization': professional.specialization,
                'rate': float(professional.rate),
                'available': professional.available,
                'online_status': professional.online_status,
                'category': professional.primary_category.name if professional.primary_category else 'General',
                'average_rating': float(professional.average_rating),
                'total_sessions': professional.total_sessions
            },
            'stats': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'total_earnings': float(total_earnings),
                'today_earnings': float(today_earnings),
                'success_rate': round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2)
            },
            'recent_sessions': sessions_data
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_dashboard_stats(request, professional_id):
    """Get professional dashboard statistics"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Today's date range
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Today's earnings and sessions
        today_sessions = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__range=(today_start, today_end)
        )
        today_earnings_agg = today_sessions.aggregate(total_earnings=Sum('cost'))
        today_earnings = today_earnings_agg['total_earnings'] or 0
        
        # Monthly earnings (current month)
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sessions = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__gte=month_start
        )
        monthly_earnings_agg = monthly_sessions.aggregate(total_earnings=Sum('cost'))
        monthly_earnings = monthly_earnings_agg['total_earnings'] or 0
        
        # Total sessions and completed sessions
        total_sessions = Session.objects.filter(professional=professional).count()
        completed_sessions = Session.objects.filter(professional=professional, status='completed').count()
        
        # Average rating
        average_rating = professional.average_rating or 0
        
        # Response rate (sessions responded to within 1 minute)
        total_requests = Session.objects.filter(professional=professional).count()
        quick_responses = Session.objects.filter(
            professional=professional,
            actual_start__isnull=False,
            created_at__isnull=False
        ).annotate(
            response_time=F('actual_start') - F('created_at')
        ).filter(
            response_time__lte=timedelta(minutes=1)
        ).count()
        response_rate = (quick_responses / total_requests * 100) if total_requests > 0 else 0
        
        # Completion rate
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Pending requests (active sessions not yet completed)
        pending_requests = Session.objects.filter(
            professional=professional,
            status__in=['active', 'pending', 'in_progress']
        ).count()

        return JsonResponse({
            'today_earnings': float(today_earnings),
            'today_sessions': today_sessions.count(),
            'total_sessions': total_sessions,
            'average_rating': float(average_rating),
            'monthly_earnings': float(monthly_earnings),
            'pending_requests': pending_requests,
            'response_rate': float(response_rate),
            'completion_rate': float(completion_rate)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_pending_requests(request, professional_id):
    """Get pending session requests for a professional"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Get active sessions that are pending professional acceptance
        pending_sessions = Session.objects.filter(
            professional=professional,
            status__in=['pending', 'active']
        ).order_by('-created_at')
        
        requests_data = []
        for session in pending_sessions:
            requests_data.append({
                'id': session.id,
                'client_id': session.client_id,
                'category': professional.primary_category.name if professional.primary_category else 'General',
                'mode': session.session_type,
                'created_at': session.created_at.isoformat(),
                'client_id': session.client_id,
                'urgency': 'medium'
            })
        
        return JsonResponse({
            'requests': requests_data,
            'count': len(requests_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def accept_session_request(request, session_id):
    """Accept a session request"""
    try:
        data = json.loads(request.body)
        professional_id = data.get('professional_id')
        
        session = get_object_or_404(Session, id=session_id)
        
        # Verify the professional owns this session
        if session.professional.id != professional_id:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to session'
            }, status=403)
        
        # Update session status and start time
        session.status = 'in_progress'
        session.actual_start = timezone.now()
        session.save()
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'client_id': session.client_id,
            'mode': session.session_type,
            'message': 'Session request accepted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def decline_session_request(request, session_id):
    """Decline a session request"""
    try:
        data = json.loads(request.body)
        professional_id = data.get('professional_id')
        
        session = get_object_or_404(Session, id=session_id)
        
        # Verify the professional owns this session
        if session.professional.id != professional_id:
            return JsonResponse({
                'success': False,
                'error': 'Unauthorized access to session'
            }, status=403)
        
        # Update session status to declined
        session.status = 'declined'
        session.ended_at = timezone.now()
        session.save()
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': 'Session request declined successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def update_professional_online_status(request, professional_id):
    """Update professional online status"""
    try:
        data = json.loads(request.body)
        is_online = data.get('is_online')
        
        professional = get_object_or_404(Professional, id=professional_id)
        
        if is_online is not None:
            professional.online_status = is_online
            professional.save()
        
        return JsonResponse({
            'success': True,
            'is_online': professional.online_status,
            'message': f'Online status updated to {"online" if professional.online_status else "offline"}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def update_professional_availability(request, professional_id):
    """Update professional availability"""
    try:
        data = json.loads(request.body)
        is_available = data.get('is_available')
        
        professional = get_object_or_404(Professional, id=professional_id)
        
        if is_available is not None:
            professional.available = is_available
            professional.save()
        
        return JsonResponse({
            'success': True,
            'is_available': professional.available,
            'message': f'Availability updated to {"available" if professional.available else "unavailable"}'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_earnings(request, professional_id):
    """Get professional earnings breakdown"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Today's earnings
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_sessions = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__gte=today_start
        )
        today_earnings_agg = today_sessions.aggregate(total_earnings=Sum('cost'))
        today_earnings = today_earnings_agg['total_earnings'] or 0
        
        # Weekly earnings
        week_start = timezone.now() - timedelta(days=7)
        weekly_sessions = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__gte=week_start
        )
        weekly_earnings_agg = weekly_sessions.aggregate(total_earnings=Sum('cost'))
        weekly_earnings = weekly_earnings_agg['total_earnings'] or 0
        
        # Monthly earnings
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_sessions = Session.objects.filter(
            professional=professional,
            status='completed',
            ended_at__gte=month_start
        )
        monthly_earnings_agg = monthly_sessions.aggregate(total_earnings=Sum('cost'))
        monthly_earnings = monthly_earnings_agg['total_earnings'] or 0
        
        # Total earnings
        total_sessions = Session.objects.filter(
            professional=professional,
            status='completed'
        )
        total_earnings_agg = total_sessions.aggregate(total_earnings=Sum('cost'))
        total_earnings = total_earnings_agg['total_earnings'] or 0
        
        # Earnings by session type
        earnings_by_type = Session.objects.filter(
            professional=professional,
            status='completed'
        ).values('session_type').annotate(
            total_earnings=Sum('cost'),
            session_count=Count('id')
        )
        
        earnings_breakdown = []
        for item in earnings_by_type:
            earnings_breakdown.append({
                'session_type': item['session_type'],
                'total_earnings': float(item['total_earnings'] or 0),
                'session_count': item['session_count']
            })
        
        return JsonResponse({
            'today_earnings': float(today_earnings),
            'weekly_earnings': float(weekly_earnings),
            'monthly_earnings': float(monthly_earnings),
            'total_earnings': float(total_earnings),
            'earnings_breakdown': earnings_breakdown
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_sessions(request, professional_id):
    """Get professional session history"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Get query parameters
        status_filter = request.GET.get('status', 'all')
        session_type = request.GET.get('type', 'all')
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        sessions = Session.objects.filter(professional=professional)
        
        # Apply filters
        if status_filter != 'all':
            sessions = sessions.filter(status=status_filter)
        
        if session_type != 'all':
            sessions = sessions.filter(session_type=session_type)
        
        # Get total count before pagination
        total_count = sessions.count()
        
        # Apply pagination
        sessions = sessions.order_by('-created_at')[offset:offset + limit]
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'client_id': session.client_id,
                'session_type': session.session_type,
                'status': session.status,
                'duration': session.duration or 0,
                'cost': float(session.cost or 0),
                'created_at': session.created_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'client_name': f"Client {session.client_id}"
            })
        
        return JsonResponse({
            'sessions': sessions_data,
            'total_count': total_count,
            'has_more': (offset + limit) < total_count
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def professional_profile(request):
    """Get professional profile for the authenticated user"""
    try:
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            try:
                token = Token.objects.get(key=token_key)
                user = token.user
            except Token.DoesNotExist:
                return JsonResponse({'error': 'Invalid token'}, status=401)
        else:
            # Fallback to user_id from query params (for testing)
            user_id = request.GET.get('user_id')
            if not user_id:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            user = get_object_or_404(User, id=user_id)
        
        try:
            professional = Professional.objects.get(user=user)
        except Professional.DoesNotExist:
            return JsonResponse({'error': 'Professional profile not found'}, status=404)
        
        # Get all categories
        all_categories = []
        if professional.primary_category:
            all_categories.append({
                'id': professional.primary_category.id,
                'name': professional.primary_category.name,
                'is_primary': True
            })
        
        for cat in professional.categories.all():
            if cat != professional.primary_category:
                all_categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_primary': False
                })
        
        profile_data = {
            'id': professional.id,
            'name': professional.name,
            'email': professional.email,
            'phone': professional.phone,
            'specialization': professional.specialization,
            'category': professional.primary_category.name if professional.primary_category else None,
            'category_id': professional.primary_category.id if professional.primary_category else None,
            'categories': all_categories,
            'rate': float(professional.rate),
            'chat_rate': float(professional.chat_rate) if professional.chat_rate else None,
            'voice_rate': float(professional.voice_rate) if professional.voice_rate else None,
            'video_rate': float(professional.video_rate) if professional.video_rate else None,
            'status': professional.status,
            'is_approved': professional.status == 'approved',
            'available': professional.available,
            'online_status': professional.online_status,
            'experience_years': professional.experience_years,
            'bio': professional.bio,
            'title': professional.title,
            'languages': professional.languages,
            'education': professional.education,
            'certifications': professional.certifications,
            'created_at': professional.created_at.isoformat(),
            'approved_at': professional.approved_at.isoformat() if professional.approved_at else None
        }
        
        return JsonResponse(profile_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def update_professional_profile(request, professional_id):
    """Update professional profile"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'specialization' in data:
            professional.specialization = data['specialization']
        if 'category_id' in data:
            try:
                category = Category.objects.get(id=data['category_id'])
                professional.primary_category = category
                # Add to categories if not already there
                if category not in professional.categories.all():
                    professional.categories.add(category)
            except Category.DoesNotExist:
                return JsonResponse({'error': 'Category not found'}, status=400)
        if 'rate' in data:
            professional.rate = data['rate']
        if 'chat_rate' in data:
            professional.chat_rate = data['chat_rate']
        if 'voice_rate' in data:
            professional.voice_rate = data['voice_rate']
        if 'video_rate' in data:
            professional.video_rate = data['video_rate']
        if 'bio' in data:
            professional.bio = data['bio']
        if 'experience_years' in data:
            professional.experience_years = data['experience_years']
        if 'phone' in data:
            professional.phone = data['phone']
        if 'name' in data:
            professional.name = data['name']
        if 'email' in data:
            professional.email = data['email']
        if 'title' in data:
            professional.title = data['title']
        if 'languages' in data:
            professional.languages = data['languages']
        if 'education' in data:
            professional.education = data['education']
        if 'certifications' in data:
            professional.certifications = data['certifications']
        
        professional.save()
        
        # Get updated categories
        all_categories = []
        if professional.primary_category:
            all_categories.append({
                'id': professional.primary_category.id,
                'name': professional.primary_category.name,
                'is_primary': True
            })
        
        for cat in professional.categories.all():
            if cat != professional.primary_category:
                all_categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_primary': False
                })
        
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully',
            'professional': {
                'id': professional.id,
                'name': professional.name,
                'email': professional.email,
                'specialization': professional.specialization,
                'category': professional.primary_category.name if professional.primary_category else None,
                'category_id': professional.primary_category.id if professional.primary_category else None,
                'categories': all_categories,
                'rate': float(professional.rate),
                'chat_rate': float(professional.chat_rate) if professional.chat_rate else None,
                'voice_rate': float(professional.voice_rate) if professional.voice_rate else None,
                'video_rate': float(professional.video_rate) if professional.video_rate else None,
                'bio': professional.bio,
                'experience_years': professional.experience_years,
                'phone': professional.phone,
                'title': professional.title,
                'languages': professional.languages,
                'education': professional.education,
                'certifications': professional.certifications
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# SESSION MANAGEMENT VIEWS
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def create_session(request):
    """Create a new session"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if 'professional_id' not in data:
            return JsonResponse({
                'success': False,
                'error': 'professional_id is required'
            }, status=400)
        
        # Check if professional exists
        professional = get_object_or_404(Professional, id=data['professional_id'])
        
        session = Session.objects.create(
            professional=professional,
            client_id=data.get('client_id', 1),
            session_type=data.get('session_type', 'chat'),
            status='pending',
            category=professional.primary_category
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'professional_name': session.professional.name,
            'started_at': session.created_at.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_session_detail(request, session_id):
    """Get session details and messages"""
    try:
        session = get_object_or_404(Session, id=session_id)
        
        # Get messages for this session
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        session_data = {
            'session': {
                'id': session.id,
                'client_id': session.client_id,
                'professional_id': session.professional.id,
                'professional_name': session.professional.name,
                'category': session.professional.primary_category.name if session.professional.primary_category else 'General',
                'mode': session.session_type,
                'status': session.status,
                'duration': session.duration or 0,
                'cost': float(session.cost or 0),
                'created_at': session.created_at.isoformat(),
                'actual_start': session.actual_start.isoformat() if session.actual_start else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            },
            'messages': [
                {
                    'id': msg.id,
                    'content': msg.message,
                    'sender': msg.sender_type,
                    'timestamp': msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        }
        
        return JsonResponse(session_data)
        
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_session_messages_api(request, session_id):
    """Get messages for a session (for polling)"""
    try:
        session = get_object_or_404(Session, id=session_id)
        messages = ChatMessage.objects.filter(session=session).order_by('created_at')
        
        messages_data = {
            'messages': [
                {
                    'id': msg.id,
                    'content': msg.message,
                    'sender': msg.sender_type,
                    'timestamp': msg.created_at.isoformat(),
                }
                for msg in messages
            ]
        }
        
        return JsonResponse(messages_data)
        
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def send_message_api(request, session_id):
    """Send a message in a session"""
    try:
        data = json.loads(request.body)
        session = get_object_or_404(Session, id=session_id)
        
        # Create new message
        message = ChatMessage.objects.create(
            session=session,
            message=data['content'],
            sender_type=data.get('sender', 'professional'),
            message_type='text'
        )
        
        return JsonResponse({
            'success': True,
            'message_id': message.id
        })
        
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def end_session_api(request, session_id):
    """End a session"""
    try:
        data = json.loads(request.body)
        session = get_object_or_404(Session, id=session_id)
        
        # Update session status
        session.status = 'completed'
        session.ended_at = timezone.now()
        
        # Calculate duration and cost if not provided
        if session.actual_start and not data.get('duration'):
            duration = (session.ended_at - session.actual_start).total_seconds() / 60
            session.duration = int(duration)
        
        if not data.get('cost') and session.duration:
            # Calculate cost based on professional's rate and duration
            rate = session.professional.get_rate_for_session_type(session.session_type)
            session.cost = (session.duration / 60) * float(rate)
        
        session.save()
        
        # Update professional's current call
        professional = session.professional
        if professional.current_call == session:
            professional.current_call = None
            professional.save()
        
        return JsonResponse({'success': True, 'message': 'Session ended successfully'})
        
    except Session.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["GET"])
def session_history(request):
    """Get session history for the current user"""
    try:
        # For now, we'll return all sessions. In production, filter by authenticated user
        sessions = Session.objects.all().select_related('professional').order_by('-created_at')
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': str(session.id),
                'professional': {
                    'id': str(session.professional.id),
                    'name': session.professional.name,
                    'specialization': session.professional.specialization,
                },
                'session_type': session.session_type,
                'status': session.status,
                'duration': session.duration or 0,
                'cost': float(session.cost or 0),
                'created_at': session.created_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'client_id': session.client_id,
            })
            
        return JsonResponse({
            'sessions': sessions_data,
            'total_count': sessions.count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# VIDEO CALL MANAGEMENT
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def initiate_video_call(request):
    """Initiate a video call session"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['professional_id', 'client_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'{field} is required'
                }, status=400)
        
        # Check if professional exists and is available
        professional = get_object_or_404(Professional, id=data['professional_id'])
        
        if not professional.available or not professional.online_status:
            return JsonResponse({
                'success': False,
                'error': 'Professional is not available'
            }, status=400)
        
        # Generate a unique room ID for the video call
        room_id = f"video_room_{uuid.uuid4().hex[:8]}"
        
        # Create a new session for video call
        session = Session.objects.create(
            professional=professional,
            client_id=data['client_id'],
            session_type='video',
            status='active',
            actual_start=timezone.now(),
            room_id=room_id,
            call_started_at=timezone.now(),
            category=professional.primary_category
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'room_id': room_id,
            'professional_name': professional.name,
            'started_at': session.actual_start.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def join_video_call(request, session_id):
    """Join an existing video call"""
    try:
        session = get_object_or_404(Session, id=session_id)
        
        # Check if session is active
        if session.status != 'active':
            return JsonResponse({
                'success': False,
                'error': 'Session is not active'
            }, status=400)
        
        # Use the room_id from the session, or generate one if not exists
        room_id = session.room_id or f"video_room_{session.id}"
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'room_id': room_id,
            'professional_name': session.professional.name,
            'session_type': session.session_type
        })
        
    except Session.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def end_video_call(request, session_id):
    """End a video call session"""
    try:
        data = json.loads(request.body)
        session = get_object_or_404(Session, id=session_id)
        
        # Calculate duration
        call_end_time = timezone.now()
        if session.call_started_at:
            call_duration_seconds = (call_end_time - session.call_started_at).total_seconds()
        elif session.actual_start:
            call_duration_seconds = (call_end_time - session.actual_start).total_seconds()
        else:
            call_duration_seconds = data.get('duration', 0)
        
        # Calculate cost based on professional's rate and duration
        cost_per_minute = session.professional.get_rate_for_session_type('video')
        cost = (call_duration_seconds / 60) * float(cost_per_minute)
        
        # Update session with call fields
        session.status = 'completed'
        session.duration = int(call_duration_seconds / 60)
        session.cost = cost
        session.ended_at = call_end_time
        session.call_ended_at = call_end_time
        session.call_duration = int(call_duration_seconds)
        session.save()
        
        # Create payment record
        payment = Payment.objects.create(
            session=session,
            amount=cost,
            status='completed',
            payment_method=data.get('payment_method', 'card'),
            completed_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'total_cost': float(session.cost),
            'duration': session.call_duration,
            'ended_at': session.ended_at.isoformat(),
            'payment_id': payment.id
        })
        
    except Session.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

# =====================
# VOICE CALL MANAGEMENT
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def initiate_voice_call(request):
    """Initiate a voice call session"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['professional_id', 'client_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'error': f'{field} is required'
                }, status=400)
        
        # Check if professional exists and is available
        professional = get_object_or_404(Professional, id=data['professional_id'])
        
        if not professional.available or not professional.online_status:
            return JsonResponse({
                'success': False,
                'error': 'Professional is not available'
            }, status=400)
        
        # Generate a unique room ID for the voice call
        room_id = f"voice_room_{uuid.uuid4().hex[:8]}"
        
        # Create a new session for voice call
        session = Session.objects.create(
            professional=professional,
            client_id=data['client_id'],
            session_type='audio',
            status='active',
            actual_start=timezone.now(),
            room_id=room_id,
            call_started_at=timezone.now(),
            category=professional.primary_category
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'room_id': room_id,
            'professional_name': professional.name,
            'started_at': session.actual_start.isoformat()
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def end_voice_call(request, session_id):
    """End a voice call session"""
    try:
        data = json.loads(request.body)
        session = get_object_or_404(Session, id=session_id)
        
        # Calculate duration
        call_end_time = timezone.now()
        if session.call_started_at:
            call_duration_seconds = (call_end_time - session.call_started_at).total_seconds()
        elif session.actual_start:
            call_duration_seconds = (call_end_time - session.actual_start).total_seconds()
        else:
            call_duration_seconds = data.get('duration', 0)
        
        # Calculate cost based on professional's rate and duration
        cost_per_minute = session.professional.get_rate_for_session_type('audio')
        cost = (call_duration_seconds / 60) * float(cost_per_minute)
        
        # Update session with call fields
        session.status = 'completed'
        session.duration = int(call_duration_seconds / 60)
        session.cost = cost
        session.ended_at = call_end_time
        session.call_ended_at = call_end_time
        session.call_duration = int(call_duration_seconds)
        session.save()
        
        # Create payment record
        payment = Payment.objects.create(
            session=session,
            amount=cost,
            status='completed',
            payment_method=data.get('payment_method', 'card'),
            completed_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'total_cost': float(session.cost),
            'duration': session.call_duration,
            'ended_at': session.ended_at.isoformat(),
            'payment_id': payment.id
        })
        
    except Session.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)

# =====================
# USER PROFILE & FAVORITES VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def user_profile(request):
    """Get user profile with favorites"""
    try:
        # For now, we'll use a demo user. In production, use request.user with authentication
        user_id = request.GET.get('user_id', 1)
        user = get_object_or_404(User, id=user_id)
        
        try:
            user_profile = UserProfile.objects.get(user=user)
            favorite_professionals = user_profile.favorite_professionals or []
            user_type = user_profile.user_type
        except UserProfile.DoesNotExist:
            # Create user profile if it doesn't exist
            user_profile = UserProfile.objects.create(user=user)
            favorite_professionals = []
            user_type = 'client'
        
        # Get favorite professionals details
        favorite_pros_data = []
        for pro_id in favorite_professionals:
            try:
                professional = Professional.objects.get(id=pro_id)
                favorite_pros_data.append({
                    'id': professional.id,
                    'name': professional.name,
                    'specialization': professional.specialization,
                    'rate': float(professional.rate),
                    'available': professional.available,
                    'online_status': professional.online_status,
                    'category': professional.primary_category.name if professional.primary_category else 'General',
                    'average_rating': float(professional.average_rating),
                    'total_sessions': professional.total_sessions,
                    'email': professional.email,
                    'phone': professional.phone
                })
            except Professional.DoesNotExist:
                # Remove invalid professional ID from favorites
                favorite_professionals.remove(pro_id)
                user_profile.save()
        
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user_profile.phone,
            'date_of_birth': str(user_profile.date_of_birth) if user_profile.date_of_birth else None,
            'user_type': user_type,
            'location': user_profile.location,
            'timezone': user_profile.timezone,
            'favorite_professionals': favorite_professionals,
            'favorite_professionals_details': favorite_pros_data,
            'created_at': user.date_joined.isoformat(),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def manage_favorites(request, professional_id=None):
    """Add or remove professionals from favorites"""
    try:
        # For demo purposes, using user_id from request. In production, use request.user
        data = json.loads(request.body) if request.body else {}
        user_id = data.get('user_id', 1)
        
        user = get_object_or_404(User, id=user_id)
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        
        if user_profile.favorite_professionals is None:
            user_profile.favorite_professionals = []
        
        if request.method == "POST":
            # Add to favorites
            professional = get_object_or_404(Professional, id=professional_id)
            
            if professional_id not in user_profile.favorite_professionals:
                user_profile.favorite_professionals.append(professional_id)
                user_profile.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Added {professional.name} to favorites',
                'favorite_professionals': user_profile.favorite_professionals
            })
        
        elif request.method == "DELETE":
            # Remove from favorites
            professional = get_object_or_404(Professional, id=professional_id)
            
            if professional_id in user_profile.favorite_professionals:
                user_profile.favorite_professionals.remove(professional_id)
                user_profile.save()
            
            return JsonResponse({
                'success': True, 
                'message': f'Removed {professional.name} from favorites',
                'favorite_professionals': user_profile.favorite_professionals
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def user_favorites(request):
    """Get user's favorite professionals with full details"""
    try:
        user_id = request.GET.get('user_id', 1)
        user = get_object_or_404(User, id=user_id)
        
        try:
            user_profile = UserProfile.objects.get(user=user)
            favorite_professionals = user_profile.favorite_professionals or []
        except UserProfile.DoesNotExist:
            favorite_professionals = []
        
        # Get detailed information for each favorite professional
        favorite_pros_data = []
        for pro_id in favorite_professionals:
            try:
                professional = Professional.objects.get(id=pro_id, status='approved')
                
                # Calculate professional stats
                sessions_count = Session.objects.filter(professional=professional).count()
                completed_sessions = Session.objects.filter(professional=professional, status='completed').count()
                
                favorite_pros_data.append({
                    'id': professional.id,
                    'name': professional.name,
                    'specialization': professional.specialization,
                    'rate': float(professional.rate),
                    'available': professional.available,
                    'online_status': professional.online_status,
                    'category': professional.primary_category.name if professional.primary_category else 'General',
                    'average_rating': float(professional.average_rating),
                    'total_sessions': professional.total_sessions,
                    'email': professional.email,
                    'phone': professional.phone,
                    'stats': {
                        'sessions_count': sessions_count,
                        'completed_sessions': completed_sessions,
                        'success_rate': round((completed_sessions / sessions_count * 100) if sessions_count > 0 else 0, 2)
                    }
                })
            except Professional.DoesNotExist:
                # Remove invalid professional ID from favorites
                if user_profile:
                    user_profile.favorite_professionals.remove(pro_id)
                    user_profile.save()
        
        return JsonResponse({
            'favorites': favorite_pros_data,
            'count': len(favorite_pros_data),
            'user_id': user_id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# CATEGORIES MANAGEMENT VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def public_categories_list(request):
    """
    Public categories endpoint for React Native app
    Get all categories (enabled only for public)
    """
    try:
        # Get only enabled categories for public access
        categories = Category.objects.filter(enabled=True)
        categories_data = []
        
        for category in categories:
            # Calculate real statistics for categories
            professional_count = Professional.objects.filter(
                Q(category=category) | 
                Q(categories=category) |
                Q(primary_category=category),
                status='approved'
            ).distinct().count()
            
            session_count = Session.objects.filter(category=category).count()
            
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'base_price': float(category.base_price),
                'professional_count': professional_count,
                'session_count': session_count,
                'icon': category.icon,
                'color': category.color,
                'avg_response_time': category.avg_response_time,
                'is_featured': category.is_featured,
                'sort_order': category.sort_order,
                'created_at': category.created_at.isoformat() if category.created_at else None,
            })
        
        return JsonResponse({'categories': categories_data})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_categories_list(request):
    """
    Handle GET (list categories) and POST (create category) requests for admin
    """
    if request.method == 'GET':
        try:
            # Get all categories from database - REAL DATA
            categories = Category.objects.all()
            categories_data = []
            
            for category in categories:
                # Calculate real statistics for categories
                professional_count = Professional.objects.filter(
                    Q(category=category) | 
                    Q(categories=category) |
                    Q(primary_category=category)
                ).distinct().count()
                
                session_count = Session.objects.filter(category=category).count()
                
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'base_price': float(category.base_price),
                    'enabled': category.enabled,
                    'professional_count': professional_count,
                    'session_count': session_count,
                    'icon': category.icon,
                    'color': category.color,
                    'avg_response_time': category.avg_response_time,
                    'is_featured': category.is_featured,
                    'sort_order': category.sort_order,
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None,
                })
            
            return JsonResponse({'categories': categories_data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create new category in database - REAL DATA
            category = Category.objects.create(
                name=data.get('name', ''),
                description=data.get('description', ''),
                base_price=data.get('base_price', 0),
                enabled=data.get('enabled', True),
                icon=data.get('icon', ''),
                color=data.get('color', '#6B7280'),
                avg_response_time=data.get('avg_response_time', 5),
                is_featured=data.get('is_featured', False),
                sort_order=data.get('sort_order', 0)
            )
            
            return JsonResponse({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'base_price': float(category.base_price),
                'enabled': category.enabled,
                'professional_count': 0,
                'session_count': 0,
                'icon': category.icon,
                'color': category.color,
                'avg_response_time': category.avg_response_time,
                'is_featured': category.is_featured,
                'sort_order': category.sort_order,
                'created_at': category.created_at.isoformat(),
                'updated_at': category.updated_at.isoformat(),
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_category(request, category_id):
    """
    Handle category updates - REAL DATABASE OPERATIONS
    """
    try:
        data = json.loads(request.body)
        
        # Get category from database
        category = Category.objects.get(id=category_id)
        
        # Update fields
        if 'name' in data:
            category.name = data['name']
        if 'description' in data:
            category.description = data['description']
        if 'base_price' in data:
            category.base_price = data['base_price']
        if 'enabled' in data:
            category.enabled = data['enabled']
        if 'icon' in data:
            category.icon = data['icon']
        if 'color' in data:
            category.color = data['color']
        if 'avg_response_time' in data:
            category.avg_response_time = data['avg_response_time']
        if 'is_featured' in data:
            category.is_featured = data['is_featured']
        if 'sort_order' in data:
            category.sort_order = data['sort_order']
        
        category.save()
        
        # Calculate updated statistics
        professional_count = Professional.objects.filter(
            Q(category=category) | 
            Q(categories=category) |
            Q(primary_category=category)
        ).distinct().count()
        
        session_count = Session.objects.filter(category=category).count()
        
        return JsonResponse({
            'success': True, 
            'message': f'Category {category_id} updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'base_price': float(category.base_price),
                'enabled': category.enabled,
                'professional_count': professional_count,
                'session_count': session_count,
                'icon': category.icon,
                'color': category.color,
                'avg_response_time': category.avg_response_time,
                'is_featured': category.is_featured,
                'sort_order': category.sort_order,
            }
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_category(request, category_id):
    """
    Handle category deletion - REAL DATABASE OPERATION
    """
    try:
        category = Category.objects.get(id=category_id)
        category_name = category.name
        category.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Category "{category_name}" deleted successfully'
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# ADMIN DASHBOARD VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def admin_dashboard_stats(request):
    """Admin dashboard statistics with real database data"""
    try:
        # Professional statistics - using status field
        total_professionals = Professional.objects.count()
        pending_approvals = Professional.objects.filter(status='pending').count()
        approved_professionals = Professional.objects.filter(status='approved').count()
        
        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # Session statistics
        completed_sessions = Session.objects.filter(status='completed').count()
        total_sessions = Session.objects.count()
        active_sessions = Session.objects.filter(status='active').count()
        
        # Revenue statistics
        revenue_agg = Session.objects.filter(status='completed').aggregate(total_revenue=Sum('cost'))
        total_revenue = revenue_agg['total_revenue'] or 0
        
        # Monthly revenue (last 30 days)
        monthly_revenue_agg = Session.objects.filter(
            status='completed',
            ended_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(total_revenue=Sum('cost'))
        monthly_revenue = monthly_revenue_agg['total_revenue'] or 0
        
        # Average session value
        avg_agg = Session.objects.filter(status='completed').aggregate(avg_value=Avg('cost'))
        average_session_value = avg_agg['avg_value'] or 0
        
        # Dispute statistics
        active_disputes = Dispute.objects.filter(status='open').count()
        total_disputes = Dispute.objects.count()
        
        # Category statistics
        total_categories = Category.objects.count()
        enabled_categories = Category.objects.filter(enabled=True).count()
        
        # Monthly growth calculation
        last_month_start = timezone.now() - timedelta(days=60)
        last_month_end = timezone.now() - timedelta(days=30)
        
        last_month_revenue_agg = Session.objects.filter(
            status='completed',
            ended_at__gte=last_month_start,
            ended_at__lt=last_month_end
        ).aggregate(total_revenue=Sum('cost'))
        last_month_revenue = last_month_revenue_agg['total_revenue'] or 0
        
        if last_month_revenue > 0:
            monthly_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
        else:
            monthly_growth = 100 if monthly_revenue > 0 else 0

        return JsonResponse({
            'total_professionals': total_professionals,
            'pending_approvals': pending_approvals,
            'approved_professionals': approved_professionals,
            'total_revenue': float(total_revenue),
            'active_disputes': active_disputes,
            'monthly_growth': round(monthly_growth, 2),
            'completed_sessions': completed_sessions,
            'total_users': total_users,
            'active_users': active_users,
            'monthly_revenue': float(monthly_revenue),
            'average_session_value': float(average_session_value),
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_disputes': total_disputes,
            'total_categories': total_categories,
            'enabled_categories': enabled_categories,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def revenue_chart_data(request):
    """Revenue chart data from actual payment records"""
    try:
        # Get revenue data for the last 6 months
        months = []
        revenue_data = []
        
        for i in range(5, -1, -1):
            month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            target_month = month_start - timedelta(days=30*i)
            
            month_revenue_agg = Session.objects.filter(
                status='completed',
                ended_at__year=target_month.year,
                ended_at__month=target_month.month
            ).aggregate(total_revenue=Sum('cost'))
            month_revenue = month_revenue_agg['total_revenue'] or 0
            
            months.append(target_month.strftime('%b %Y'))
            revenue_data.append(float(month_revenue))
        
        return JsonResponse({
            'labels': months,
            'data': revenue_data
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def recent_activity(request):
    """Recent activities from actual database events"""
    try:
        activities = []
        
        # Recent professional approvals (using approved_at field)
        recent_approvals = Professional.objects.filter(
            status='approved',
            approved_at__isnull=False
        ).order_by('-approved_at')[:5]
        
        for approval in recent_approvals:
            activities.append({
                'id': f"approval_{approval.id}",
                'type': 'approval',
                'message': f'Professional "{approval.name}" approved',
                'timestamp': approval.approved_at.isoformat(),
            })
        
        # Recent sessions
        recent_sessions = Session.objects.all().order_by('-created_at')[:5]
        for session in recent_sessions:
            activities.append({
                'id': f"session_{session.id}",
                'type': 'session',
                'message': f'New {session.session_type} session with {session.professional.name}',
                'timestamp': session.created_at.isoformat(),
            })
        
        # Recent disputes
        recent_disputes = Dispute.objects.all().order_by('-created_at')[:3]
        for dispute in recent_disputes:
            activities.append({
                'id': f"dispute_{dispute.id}",
                'type': 'dispute',
                'message': f'New dispute: {dispute.title}',
                'timestamp': dispute.created_at.isoformat(),
            })
        
        # Recent user registrations
        recent_users = User.objects.all().order_by('-date_joined')[:3]
        for user in recent_users:
            activities.append({
                'id': f"user_{user.id}",
                'type': 'registration',
                'message': f'New user registered: {user.username}',
                'timestamp': user.date_joined.isoformat(),
            })
        
        # Sort all activities by timestamp (newest first)
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Return only the 10 most recent activities
        return JsonResponse({'activities': activities[:10]})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def admin_professionals_api(request):
    """Admin professionals API endpoint"""
    try:
        professionals = Professional.objects.all()
        data = [{
            'id': prof.id,
            'name': prof.name,
            'email': prof.email,
            'specialization': prof.specialization,
            'is_online': prof.online_status,
            'is_available': prof.available,
            'status': prof.status,
            'rate': float(prof.rate) if prof.rate else 0,
            'category': prof.primary_category.name if prof.primary_category else 'General'
        } for prof in professionals]
        
        return JsonResponse({'professionals': data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# PROFESSIONAL APPROVAL VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def pending_professionals(request):
    """Get all pending professional approvals from database"""
    try:
        pending_pros = Professional.objects.filter(status='pending')
        professionals_data = []
        
        for pro in pending_pros:
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'email': pro.email,
                'phone': pro.phone,
                'created_at': pro.created_at.isoformat(),
                'category': pro.primary_category.name if pro.primary_category else 'Not specified',
                'experience_years': pro.experience_years,
                'bio': pro.bio
            })
            
        return JsonResponse({
            'professionals': professionals_data,
            'count': pending_pros.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def approve_professional(request, professional_id):
    """Approve a professional in database"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        professional.status = 'approved'
        professional.approved_at = timezone.now()
        professional.available = True
        professional.save()
        
        return JsonResponse({
            "message": f"Professional {professional.name} approved successfully",
            "professional_id": professional_id,
            "status": "approved"
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def reject_professional(request, professional_id):
    """Reject a professional with reason"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        professional_name = professional.name
        
        # Get rejection reason from request body
        data = json.loads(request.body)
        rejection_reason = data.get('reason', 'No reason provided')
        
        # Mark as rejected and store reason
        professional.status = 'rejected'
        professional.rejection_reason = rejection_reason
        professional.rejected_at = timezone.now()
        professional.available = False
        professional.save()
        
        return JsonResponse({
            "message": f"Professional {professional_name} rejected",
            "professional_id": professional_id,
            "reason": rejection_reason,
            "status": "rejected"
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def all_professionals(request):
    """Get all professionals with filters"""
    try:
        # Get query parameters
        status_filter = request.GET.get('status', 'all')
        search_query = request.GET.get('search', '')
        
        professionals = Professional.objects.all()
        
        # Apply filters using status field
        if status_filter == 'approved':
            professionals = professionals.filter(status='approved')
        elif status_filter == 'pending':
            professionals = professionals.filter(status='pending')
        elif status_filter == 'rejected':
            professionals = professionals.filter(status='rejected')
        
        if search_query:
            professionals = professionals.filter(
                Q(name__icontains=search_query) |
                Q(specialization__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        professionals_data = []
        for pro in professionals:
            # Calculate real stats for each professional
            sessions_count = Session.objects.filter(professional=pro).count()
            completed_sessions = Session.objects.filter(professional=pro, status='completed').count()

            revenue_agg = Session.objects.filter(professional=pro, status='completed').aggregate(total_revenue=Sum('cost'))
            total_revenue = revenue_agg['total_revenue'] or 0
            
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'status': pro.status,
                'available': pro.available,
                'online_status': pro.online_status,
                'email': pro.email,
                'phone': pro.phone,
                'category': pro.primary_category.name if pro.primary_category else 'General',
                'average_rating': float(pro.average_rating),
                'total_sessions': pro.total_sessions,
                'sessions_count': sessions_count,
                'completed_sessions': completed_sessions,
                'total_revenue': float(total_revenue),
                'created_at': pro.created_at.isoformat(),
            })
        
        return JsonResponse({
            'professionals': professionals_data,
            'total_count': professionals.count(),
            'approved_count': Professional.objects.filter(status='approved').count(),
            'pending_count': Professional.objects.filter(status='pending').count(),
            'rejected_count': Professional.objects.filter(status='rejected').count(),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# ANALYTICS VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def user_analytics(request):
    """User analytics data"""
    try:
        # Total users and active users
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # New users in different time periods
        new_users_7_days = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        new_users_30_days = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # User growth percentage
        total_users_30_days_ago = User.objects.filter(
            date_joined__lt=timezone.now() - timedelta(days=30)
        ).count()
        
        if total_users_30_days_ago > 0:
            growth_percentage_30_days = ((total_users - total_users_30_days_ago) / total_users_30_days_ago * 100)
        else:
            growth_percentage_30_days = 100 if total_users > 0 else 0
        
        return JsonResponse({
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'new_users_7_days': new_users_7_days,
            'new_users_30_days': new_users_30_days,
            'growth_percentage_30_days': round(growth_percentage_30_days, 2),
            'active_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 2),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def session_analytics(request):
    """Session analytics data"""
    try:
        # Session statistics
        total_sessions = Session.objects.count()
        completed_sessions = Session.objects.filter(status='completed').count()
        active_sessions = Session.objects.filter(status='active').count()
        cancelled_sessions = Session.objects.filter(status='cancelled').count()
        
        # Session types distribution
        chat_sessions = Session.objects.filter(session_type='chat').count()
        audio_sessions = Session.objects.filter(session_type='audio').count()
        video_sessions = Session.objects.filter(session_type='video').count()
        
        # Average session duration
        avg_duration_agg = Session.objects.aggregate(avg_duration=Avg('duration'))
        avg_duration = avg_duration_agg['avg_duration'] or 0
        
        # Session completion rate
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        return JsonResponse({
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'active_sessions': active_sessions,
            'cancelled_sessions': cancelled_sessions,
            'session_types': {
                'chat': chat_sessions,
                'audio': audio_sessions,
                'video': video_sessions
            },
            'average_duration_minutes': round(avg_duration, 2),
            'completion_rate': round(completion_rate, 2),
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def financial_analytics(request):
    """Financial analytics data"""
    try:
        # Revenue statistics
        revenue_agg = Session.objects.filter(status='completed').aggregate(total_revenue=Sum('cost'))
        total_revenue = revenue_agg['total_revenue'] or 0
        
        monthly_revenue_agg = Session.objects.filter(
            status='completed',
            ended_at__gte=timezone.now() - timedelta(days=30)
        ).aggregate(total_revenue=Sum('cost'))
        monthly_revenue = monthly_revenue_agg['total_revenue'] or 0
        
        weekly_revenue_agg = Session.objects.filter(
            status='completed',
            ended_at__gte=timezone.now() - timedelta(days=7)
        ).aggregate(total_revenue=Sum('cost'))
        weekly_revenue = weekly_revenue_agg['total_revenue'] or 0
        
        # Average transaction value
        avg_agg = Session.objects.filter(status='completed').aggregate(avg_value=Avg('cost'))
        average_transaction_value = avg_agg['avg_value'] or 0
        
        # Payment status distribution
        completed_payments = Payment.objects.filter(status='completed').count()
        pending_payments = Payment.objects.filter(status='pending').count()
        failed_payments = Payment.objects.filter(status='failed').count()
        
        return JsonResponse({
            'total_revenue': float(total_revenue),
            'monthly_revenue': float(monthly_revenue),
            'weekly_revenue': float(weekly_revenue),
            'average_transaction_value': float(average_transaction_value),
            'payment_status': {
                'completed': completed_payments,
                'pending': pending_payments,
                'failed': failed_payments
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# USER MANAGEMENT VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def users_list(request):
    """Get paginated list of all users with filters"""
    try:
        # Get query parameters
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        status_filter = request.GET.get('status', 'all')
        role_filter = request.GET.get('role', 'all')
        search_query = request.GET.get('search', '')
        
        # Start with all users
        users = User.objects.all().select_related('userprofile')
        
        # Apply status filter
        if status_filter != 'all':
            if status_filter == 'active':
                users = users.filter(is_active=True)
            elif status_filter == 'inactive':
                users = users.filter(is_active=False)
        
        # Apply search filter
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Calculate pagination
        total_count = users.count()
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_users = users[start_index:end_index]
        
        users_data = []
        for user in paginated_users:
            # Get user profile if exists
            user_profile = getattr(user, 'userprofile', None)
            
            # Calculate user statistics
            sessions_count = Session.objects.filter(client_id=user.id).count()
            
            # Calculate total spent
            total_spent_agg = Session.objects.filter(
                client_id=user.id, 
                status='completed'
            ).aggregate(total_spent=Sum('cost'))
            total_spent = total_spent_agg['total_spent'] or 0
            
            # Determine user role using user_type from UserProfile
            user_role = 'client'
            user_type = 'client'
            if user_profile:
                user_type = user_profile.user_type
                user_role = user_profile.user_type
            
            # Check if user is staff (admin) - admin overrides other roles
            if user.is_staff:
                user_role = 'admin'
            
            users_data.append({
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'phone': user_profile.phone if user_profile else '',
                'role': user_role,
                'user_type': user_type,
                'status': 'active' if user.is_active else 'inactive',
                'created_at': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'location': getattr(user_profile, 'location', '') if user_profile else '',
                'session_count': sessions_count,
                'total_spent': float(total_spent),
                'is_verified': getattr(user_profile, 'is_verified', False) if user_profile else False,
                'date_joined': user.date_joined.isoformat(),
            })
        
        return JsonResponse({
            'users': users_data,
            'total_count': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def user_detail(request, user_id):
    """Get detailed information about a specific user"""
    try:
        user = get_object_or_404(User, id=user_id)
        user_profile = getattr(user, 'userprofile', None)
        
        # Calculate detailed user statistics
        sessions_count = Session.objects.filter(client_id=user.id).count()
        completed_sessions = Session.objects.filter(client_id=user.id, status='completed').count()
        
        # Calculate total spent
        total_spent_agg = Session.objects.filter(
            client_id=user.id, 
            status='completed'
        ).aggregate(total_spent=Sum('cost'))
        total_spent = total_spent_agg['total_spent'] or 0
        
        # Recent sessions
        recent_sessions = Session.objects.filter(client_id=user.id).order_by('-created_at')[:10]
        sessions_data = []
        for session in recent_sessions:
            sessions_data.append({
                'id': session.id,
                'professional_id': session.professional.id,
                'professional_name': session.professional.name,
                'session_type': session.session_type,
                'status': session.status,
                'duration': session.duration,
                'cost': float(session.cost),
                'created_at': session.created_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None
            })
        
        # Determine user role using user_type from UserProfile
        user_role = 'client'
        user_type = 'client'
        if user_profile:
            user_type = user_profile.user_type
            user_role = user_profile.user_type
        
        # Check if user is staff (admin) - admin overrides other roles
        if user.is_staff:
            user_role = 'admin'
        
        response_data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'phone': user_profile.phone if user_profile else '',
            'role': user_role,
            'user_type': user_type,
            'status': 'active' if user.is_active else 'inactive',
            'created_at': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'location': getattr(user_profile, 'location', '') if user_profile else '',
            'session_count': sessions_count,
            'completed_sessions': completed_sessions,
            'total_spent': float(total_spent),
            'is_verified': getattr(user_profile, 'is_verified', False) if user_profile else False,
            'date_joined': user.date_joined.isoformat(),
            'stats': {
                'sessions_count': sessions_count,
                'completed_sessions': completed_sessions,
                'total_spent': float(total_spent),
                'success_rate': round((completed_sessions / sessions_count * 100) if sessions_count > 0 else 0, 2)
            },
            'recent_sessions': sessions_data
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_user_status(request, user_id):
    """Update user status (active/inactive)"""
    try:
        user = get_object_or_404(User, id=user_id)
        data = json.loads(request.body)
        status = data.get('status', '').lower()
        
        if status == 'active':
            user.is_active = True
            message = f"User {user.username} activated successfully"
        elif status == 'inactive':
            user.is_active = False
            message = f"User {user.username} deactivated successfully"
        elif status == 'suspended':
            user.is_active = False
            message = f"User {user.username} suspended successfully"
        else:
            return JsonResponse({'error': 'Invalid status'}, status=400)
        
        user.save()
        
        return JsonResponse({
            "message": message,
            "user_id": user_id,
            "status": status,
            "username": user.username
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_user_role(request, user_id):
    """Update user role (user/professional/admin)"""
    try:
        user = get_object_or_404(User, id=user_id)
        data = json.loads(request.body)
        role = data.get('role', '').lower()
        
        # This is a simplified role update
        if role == 'admin':
            user.is_staff = True
            user.is_superuser = True
            message = f"User {user.username} promoted to admin"
        elif role == 'professional':
            user.is_staff = False
            user.is_superuser = False
            # Update user profile user_type
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.user_type = 'professional'
            user_profile.save()
            message = f"User {user.username} set as professional"
        elif role == 'client':
            user.is_staff = False
            user.is_superuser = False
            # Update user profile user_type
            user_profile, created = UserProfile.objects.get_or_create(user=user)
            user_profile.user_type = 'client'
            user_profile.save()
            message = f"User {user.username} set as regular user"
        else:
            return JsonResponse({'error': 'Invalid role'}, status=400)
        
        user.save()
        
        return JsonResponse({
            "message": message,
            "user_id": user_id,
            "role": role,
            "username": user.username
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_user(request, user_id):
    """Delete a user account"""
    try:
        user = get_object_or_404(User, id=user_id)
        username = user.username
        
        # You might want to soft delete instead of hard delete
        user.delete()
        
        return JsonResponse({
            "message": f"User {username} deleted successfully",
            "user_id": user_id,
            "username": username
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# FILE UPLOAD VIEWS
# =====================

@csrf_exempt
@require_POST
def upload_license_file(request):
    """
    Handle license file uploads for professional registration
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)

        uploaded_file = request.FILES['file']

        # Validate file size (max 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File size too large. Maximum 10MB allowed.'}, status=400)

        # Validate file type
        allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid file type. Only PDF, JPEG, and PNG files are allowed.'}, status=400)

        # Generate unique filename
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"licenses/{uuid.uuid4()}{file_extension}"

        # Save file
        file_path = default_storage.save(unique_filename, ContentFile(uploaded_file.read()))

        # Return file URL
        file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)

        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size
        })

    except Exception as e:
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def upload_profile_image(request):
    """
    Handle profile image uploads
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)

        uploaded_file = request.FILES['file']

        # Validate file size (max 5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return JsonResponse({'error': 'File size too large. Maximum 5MB allowed.'}, status=400)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg', 'image/gif']
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid file type. Only image files are allowed.'}, status=400)

        # Generate unique filename
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"profile_images/{uuid.uuid4()}{file_extension}"

        # Save file
        file_path = default_storage.save(unique_filename, ContentFile(uploaded_file.read()))

        # Return file URL
        file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)
        
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size
        })

    except Exception as e:
        return JsonResponse({'error': f'Upload failed: {str(e)}'}, status=500)

# =====================
# NOTIFICATION VIEWS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def get_notifications(request):
    """Get user notifications"""
    try:
        user_id = request.GET.get('user_id', 1)
        notifications = Notification.objects.filter(user_id=user_id).order_by('-created_at')[:20]
        
        notifications_data = []
        for notification in notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'is_read': notification.read,
                'created_at': notification.created_at.isoformat(),
                'data': getattr(notification, 'data', {})
            })
        
        return JsonResponse({
            'notifications': notifications_data,
            'unread_count': Notification.objects.filter(user_id=user_id, read=False).count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    try:
        notification = get_object_or_404(Notification, id=notification_id)
        notification.read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all user notifications as read"""
    try:
        user_id = request.GET.get('user_id', 1)
        Notification.objects.filter(user_id=user_id, read=False).update(read=True)
        
        return JsonResponse({
            'success': True,
            'message': 'All notifications marked as read'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# DEBUG & FIX ENDPOINTS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def debug_all_professionals(request):
    """Debug endpoint to see all professionals"""
    try:
        professionals = Professional.objects.all()
        professionals_data = []
        
        for pro in professionals:
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'email': pro.email,
                'status': pro.status,
                'available': pro.available,
                'online_status': pro.online_status,
                'specialization': pro.specialization,
                'rate': float(pro.rate) if pro.rate else 0,
                'category': pro.primary_category.name if pro.primary_category else 'None'
            })
        
        return JsonResponse({
            'professionals': professionals_data,
            'total_count': professionals.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def debug_all_sessions(request):
    """Debug endpoint to see all sessions"""
    try:
        sessions = Session.objects.all().select_related('professional')
        sessions_data = []
        
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'professional_id': session.professional.id,
                'professional_name': session.professional.name,
                'client_id': session.client_id,
                'session_type': session.session_type,
                'status': session.status,
                'created_at': session.created_at.isoformat()
            })
        
        return JsonResponse({
            'sessions': sessions_data,
            'total_count': sessions.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def debug_professionals_direct(request):
    """Direct debug endpoint to check professionals"""
    try:
        professionals = Professional.objects.all()
        
        data = {
            'total_count': professionals.count(),
            'professionals': []
        }
        
        for pro in professionals:
            data['professionals'].append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'status': pro.status,
                'available': pro.available,
                'online_status': pro.online_status,
                'locked_by': pro.locked_by,
                'average_rating': float(pro.average_rating),
                'total_sessions': pro.total_sessions,
            })

        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def debug_users_and_professionals(request):
    """Debug endpoint to check all users and professionals"""
    try:
        users = User.objects.all()
        professionals = Professional.objects.all()
        user_profiles = UserProfile.objects.all()
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat()
            })
        
        professionals_data = []
        for pro in professionals:
            professionals_data.append({
                'id': pro.id,
                'user_id': pro.user.id if pro.user else None,
                'name': pro.name,
                'email': pro.email,
                'status': pro.status,
                'specialization': pro.specialization,
                'rate': float(pro.rate) if pro.rate else 0
            })
        
        user_profiles_data = []
        for profile in user_profiles:
            user_profiles_data.append({
                'id': profile.id,
                'user_id': profile.user.id,
                'user_type': profile.user_type,
                'phone': profile.phone
            })
        
        return JsonResponse({
            'users': users_data,
            'professionals': professionals_data,
            'user_profiles': user_profiles_data,
            'user_count': users.count(),
            'professional_count': professionals.count(),
            'user_profile_count': user_profiles.count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status = 500)

# =========================================================================
# NEW VIEWS FOR REACT NATIVE APP - ADDED BELOW
# =========================================================================

# =====================
# ALGORITHM MATCHING & PROFESSIONAL SEARCH
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def professionals_by_category(request, category):
    """Get professionals by category for algorithm matching"""
    try:
        # Get professionals in the specified category
        professionals = Professional.objects.filter(
            Q(primary_category__name__iexact=category) |
            Q(categories__name__iexact=category) |
            Q(specialization__icontains=category),
            status='approved',
            available=True
        ).distinct()
        
        professionals_data = []
        for pro in professionals:
            # Calculate availability score
            availability_score = calculate_availability_score(pro)
            rating_score = calculate_bayesian_rating_score(pro)
            response_score = calculate_response_time_score(pro)
            experience_score = calculate_experience_score(pro)
            
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'available': pro.available,
                'online_status': pro.online_status,
                'category': pro.primary_category.name if pro.primary_category else 'General',
                'average_rating': float(pro.average_rating),
                'total_sessions': pro.total_sessions,
                'experience_years': pro.experience_years,
                'email': pro.email,
                'phone': pro.phone,
                'response_time': pro.avg_response_time,
                'success_rate': pro.success_rate if hasattr(pro, 'success_rate') else 95,
                'current_workload': getattr(pro, 'current_workload', 0),
                'max_workload': getattr(pro, 'max_workload', 10),
                'last_active': pro.last_active.isoformat() if hasattr(pro, 'last_active') else timezone.now().isoformat(),
                'skills': get_professional_skills(pro),
                'ai_scores': {
                    'availability': availability_score,
                    'rating': rating_score,
                    'response_time': response_score,
                    'experience': experience_score
                }
            })
        
        return JsonResponse({
            'professionals': professionals_data,
            'count': professionals.count(),
            'category': category
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def search_professionals(request):
    """Search professionals with advanced filters"""
    try:
        query = request.GET.get('q', '')
        category = request.GET.get('category', '')
        min_rating = float(request.GET.get('min_rating', 0))
        max_rate = float(request.GET.get('max_rate', 1000))
        available_only = request.GET.get('available_only', 'false').lower() == 'true'
        online_only = request.GET.get('online_only', 'false').lower() == 'true'
        
        professionals = Professional.objects.filter(status='approved')
        
        # Apply filters
        if query:
            professionals = professionals.filter(
                Q(name__icontains=query) |
                Q(specialization__icontains=query) |
                Q(bio__icontains=query)
            )
        
        if category:
            professionals = professionals.filter(
                Q(primary_category__name__iexact=category) |
                Q(categories__name__iexact=category)
            )
        
        if min_rating > 0:
            professionals = professionals.filter(average_rating__gte=min_rating)
        
        if max_rate < 1000:
            professionals = professionals.filter(rate__lte=max_rate)
        
        if available_only:
            professionals = professionals.filter(available=True)
        
        if online_only:
            professionals = professionals.filter(online_status=True)
        
        professionals_data = []
        for pro in professionals:
            professionals_data.append({
                'id': pro.id,
                'name': pro.name,
                'specialization': pro.specialization,
                'rate': float(pro.rate),
                'available': pro.available,
                'online_status': pro.online_status,
                'category': pro.primary_category.name if pro.primary_category else 'General',
                'average_rating': float(pro.average_rating),
                'total_sessions': pro.total_sessions,
                'experience_years': pro.experience_years,
                'response_time': pro.avg_response_time,
                'success_rate': getattr(pro, 'success_rate', 95)
            })
        
        return JsonResponse({
            'professionals': professionals_data,
            'count': professionals.count(),
            'filters': {
                'query': query,
                'category': category,
                'min_rating': min_rating,
                'max_rate': max_rate,
                'available_only': available_only,
                'online_only': online_only
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def check_professional_availability(request, professional_id):
    """Check real-time availability of a professional"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        
        # Check if professional is currently in a session
        current_session = Session.objects.filter(
            professional=professional,
            status__in=['active', 'in_progress']
        ).first()
        
        # Calculate workload
        current_workload = Session.objects.filter(
            professional=professional,
            status__in=['active', 'pending']
        ).count()
        
        max_workload = getattr(professional, 'max_workload', 5)
        workload_ratio = current_workload / max_workload if max_workload > 0 else 0
        
        availability_data = {
            'available': professional.available and professional.online_status,
            'online_status': professional.online_status,
            'in_session': current_session is not None,
            'current_session_id': current_session.id if current_session else None,
            'current_workload': current_workload,
            'max_workload': max_workload,
            'workload_percentage': round(workload_ratio * 100, 2),
            'can_accept_new': (professional.available and 
                             professional.online_status and 
                             workload_ratio < 0.8 and 
                             current_session is None),
            'estimated_wait_time': calculate_estimated_wait_time(professional, current_workload),
            'last_active': professional.last_active.isoformat() if hasattr(professional, 'last_active') else None
        }
        
        return JsonResponse(availability_data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# LOCKING MECHANISM
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def acquire_lock(request):
    """Acquire a lock for resource protection"""
    try:
        data = json.loads(request.body)
        resource = data.get('resource')
        ttl = data.get('ttl', 30000)  # Default 30 seconds
        
        # Simple in-memory lock implementation
        # In production, use Redis or database-based locking
        current_time = timezone.now()
        lock_expiry = current_time + timedelta(milliseconds=ttl)
        
        # Check if lock exists and is still valid
        existing_lock = getattr(acquire_lock, 'locks', {}).get(resource)
        if existing_lock and existing_lock['expires'] > current_time:
            return JsonResponse({
                'success': False,
                'is_locked': True,
                'locked_by': existing_lock['locked_by'],
                'locked_until': existing_lock['expires'].isoformat()
            })
        
        # Acquire lock
        if not hasattr(acquire_lock, 'locks'):
            acquire_lock.locks = {}
        
        acquire_lock.locks[resource] = {
            'locked_by': 'current_session',
            'expires': lock_expiry,
            'acquired_at': current_time
        }
        
        return JsonResponse({
            'success': True,
            'is_locked': True,
            'locked_by': 'current_session',
            'locked_until': lock_expiry.isoformat()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def release_lock(request):
    """Release a previously acquired lock"""
    try:
        data = json.loads(request.body)
        resource = data.get('resource')
        
        if hasattr(release_lock, 'locks') and resource in release_lock.locks:
            del release_lock.locks[resource]
        
        return JsonResponse({
            'success': True,
            'message': f'Lock released for {resource}'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# PAYMENT PROCESSING
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def initiate_mpesa_stk_push(request):
    """Initiate M-Pesa STK push payment"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['phoneNumber', 'amount', 'professionalId']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # Simulate M-Pesa STK push initiation
        # In production, integrate with actual M-Pesa API
        transaction_id = f"MPESA_{uuid.uuid4().hex[:8].upper()}"
        checkout_request_id = f"ws_CO_{timezone.now().strftime('%Y%m%d%H%M%S')}_{transaction_id}"
        
        # Simulate API call to M-Pesa
        # This would be replaced with actual M-Pesa API integration
        mpesa_response = {
            'success': True,
            'transaction_id': transaction_id,
            'checkout_request_id': checkout_request_id,
            'message': 'STK push initiated successfully. Check your phone to complete payment.',
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse(mpesa_response)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to initiate M-Pesa payment: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def mpesa_callback(request):
    """Handle M-Pesa payment callback"""
    try:
        data = json.loads(request.body)
        
        # Process M-Pesa callback
        # This would handle the actual M-Pesa callback data
        callback_data = {
            'success': True,
            'message': 'Callback received successfully',
            'data': data
        }
        
        return JsonResponse(callback_data)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Callback processing failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def record_payment(request):
    """Record a payment transaction"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['amount', 'professionalId', 'sessionId']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # Create payment record
        payment = Payment.objects.create(
            session_id=data['sessionId'],
            amount=data['amount'],
            payment_method=data.get('paymentMethod', 'mpesa'),
            status='completed',
            transaction_id=data.get('transactionId', f"TXN_{uuid.uuid4().hex[:8]}"),
            completed_at=timezone.now()
        )
        
        # Update session payment status
        session = Session.objects.get(id=data['sessionId'])
        session.cost = data['amount']
        session.save()
        
        return JsonResponse({
            'success': True,
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': float(payment.amount),
            'status': payment.status,
            'completed_at': payment.completed_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to record payment: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def verify_payment(request, transaction_id):
    """Verify payment status"""
    try:
        payment = get_object_or_404(Payment, transaction_id=transaction_id)
        
        return JsonResponse({
            'success': True,
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': float(payment.amount),
            'status': payment.status,
            'payment_method': payment.payment_method,
            'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
            'session_id': payment.session_id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Payment verification failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def payment_history(request):
    """Get user payment history"""
    try:
        user_id = request.GET.get('user_id', 1)
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Get payments for user's sessions
        payments = Payment.objects.filter(
            session__client_id=user_id
        ).select_related('session').order_by('-created_at')[offset:offset + limit]
        
        payments_data = []
        for payment in payments:
            payments_data.append({
                'id': payment.id,
                'transaction_id': payment.transaction_id,
                'amount': float(payment.amount),
                'status': payment.status,
                'payment_method': payment.payment_method,
                'created_at': payment.created_at.isoformat(),
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'session': {
                    'id': payment.session.id,
                    'professional_name': payment.session.professional.name,
                    'session_type': payment.session.session_type,
                    'duration': payment.session.duration
                }
            })
        
        return JsonResponse({
            'payments': payments_data,
            'total_count': Payment.objects.filter(session__client_id=user_id).count(),
            'has_more': (offset + limit) < Payment.objects.filter(session__client_id=user_id).count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# SESSION MANAGEMENT
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def rate_session(request):
    """Rate a completed session"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['sessionId', 'professionalId', 'rating']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        session = get_object_or_404(Session, id=data['sessionId'])
        professional = get_object_or_404(Professional, id=data['professionalId'])
        
        # Update session rating
        session.rating = data['rating']
        session.review = data.get('review', '')
        session.save()
        
        # Update professional's average rating
        update_professional_rating(professional)
        
        return JsonResponse({
            'success': True,
            'message': 'Session rated successfully',
            'session_id': session.id,
            'rating': session.rating,
            'review': session.review
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to rate session: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def complete_session(request, session_id):
    """Mark session as complete"""
    try:
        session = get_object_or_404(Session, id=session_id)
        
        session.status = 'completed'
        session.ended_at = timezone.now()
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session completed successfully',
            'session_id': session.id,
            'ended_at': session.ended_at.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to complete session: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_session_status(request, session_id):
    """Update session status"""
    try:
        data = json.loads(request.body)
        session = get_object_or_404(Session, id=session_id)
        
        if 'status' in data:
            session.status = data['status']
        
        if 'duration' in data:
            session.duration = data['duration']
        
        if 'cost' in data:
            session.cost = data['cost']
        
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Session updated successfully',
            'session_id': session.id,
            'status': session.status,
            'duration': session.duration,
            'cost': float(session.cost) if session.cost else 0
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to update session: {str(e)}'
        }, status=500)

# =====================
# CALL MANAGEMENT
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def initiate_voice_call_api(request):
    """Initiate voice call session"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['professionalId', 'clientId']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        professional = get_object_or_404(Professional, id=data['professionalId'])
        
        # Create session for voice call
        session = Session.objects.create(
            professional=professional,
            client_id=data['clientId'],
            session_type='audio',
            status='active',
            actual_start=timezone.now(),
            room_id=f"voice_{uuid.uuid4().hex[:8]}",
            call_started_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'room_id': session.room_id,
            'professional_name': professional.name,
            'started_at': session.actual_start.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to initiate voice call: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def initiate_video_call_api(request):
    """Initiate video call session"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['professionalId', 'clientId']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        professional = get_object_or_404(Professional, id=data['professionalId'])
        
        # Create session for video call
        session = Session.objects.create(
            professional=professional,
            client_id=data['clientId'],
            session_type='video',
            status='active',
            actual_start=timezone.now(),
            room_id=f"video_{uuid.uuid4().hex[:8]}",
            call_started_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'room_id': session.room_id,
            'professional_name': professional.name,
            'started_at': session.actual_start.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to initiate video call: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_call_status(request, call_id):
    """Update call status"""
    try:
        data = json.loads(request.body)
        call = get_object_or_404(CallLog, id=call_id)
        
        if 'status' in data:
            call.status = data['status']
        
        if 'duration' in data:
            call.duration = data['duration']
        
        call.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Call status updated successfully',
            'call_id': call.id,
            'status': call.status,
            'duration': call.duration
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to update call status: {str(e)}'
        }, status=500)

# =====================
# NOTIFICATION MANAGEMENT
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def send_notification(request):
    """Send notification to user"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['userId', 'title', 'message']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        notification = Notification.objects.create(
            user_id=data['userId'],
            title=data['title'],
            message=data['message'],
            notification_type=data.get('type', 'general'),
            data=data.get('data', {})
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification sent successfully',
            'notification_id': notification.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to send notification: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def send_receipt_notification(request):
    """Send receipt notification"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['receiptData', 'clientId']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # Send receipt via email/SMS
        # This would integrate with your email/SMS service
        receipt_data = data['receiptData']
        
        return JsonResponse({
            'success': True,
            'message': 'Receipt notification sent successfully',
            'receipt_number': receipt_data.get('receiptNumber'),
            'sent_via': ['email', 'sms'] if data.get('sendEmail') and data.get('sendSMS') else ['email'] if data.get('sendEmail') else ['sms']
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to send receipt notification: {str(e)}'
        }, status=500)

# =====================
# RECEIPT GENERATION
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def generate_receipt(request):
    """Generate payment receipt"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['sessionId', 'amount']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        session = get_object_or_404(Session, id=data['sessionId'])
        
        # Generate receipt data
        receipt_data = {
            'receipt_number': f"RCP{timezone.now().strftime('%Y%m%d%H%M%S')}",
            'date': timezone.now().strftime('%Y-%m-%d'),
            'time': timezone.now().strftime('%H:%M:%S'),
            'client_name': f"Client {session.client_id}",
            'professional_name': session.professional.name,
            'service': f"{session.session_type} Consultation",
            'amount': float(data['amount']),
            'transaction_id': data.get('transactionId', f"TXN_{uuid.uuid4().hex[:8]}"),
            'payment_method': data.get('paymentMethod', 'mpesa')
        }
        
        return JsonResponse({
            'success': True,
            'receipt': receipt_data,
            'session_id': session.id
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to generate receipt: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_receipt(request, receipt_number):
    """Get receipt by receipt number"""
    try:
        # This would fetch from your receipt storage
        # For now, return mock data
        receipt_data = {
            'receipt_number': receipt_number,
            'date': timezone.now().strftime('%Y-%m-%d'),
            'time': timezone.now().strftime('%H:%M:%S'),
            'client_name': 'John Doe',
            'professional_name': 'Professional Name',
            'service': 'Consultation Service',
            'amount': 1000.00,
            'transaction_id': f"TXN_{uuid.uuid4().hex[:8]}",
            'payment_method': 'mpesa'
        }
        
        return JsonResponse({
            'success': True,
            'receipt': receipt_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get receipt: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def user_receipts(request):
    """Get user's receipts"""
    try:
        user_id = request.GET.get('user_id', 1)
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        # Get user's sessions with payments
        sessions = Session.objects.filter(
            client_id=user_id,
            payment__isnull=False
        ).select_related('payment', 'professional').order_by('-created_at')[offset:offset + limit]
        
        receipts_data = []
        for session in sessions:
            receipts_data.append({
                'receipt_number': f"RCP{session.created_at.strftime('%Y%m%d%H%M%S')}",
                'date': session.created_at.strftime('%Y-%m-%d'),
                'time': session.created_at.strftime('%H:%M:%S'),
                'professional_name': session.professional.name,
                'service': f"{session.session_type} Consultation",
                'amount': float(session.cost) if session.cost else 0,
                'transaction_id': session.payment.transaction_id if hasattr(session, 'payment') else f"TXN_{session.id}",
                'payment_method': session.payment.payment_method if hasattr(session, 'payment') else 'unknown'
            })
        
        return JsonResponse({
            'receipts': receipts_data,
            'total_count': Session.objects.filter(client_id=user_id, payment__isnull=False).count(),
            'has_more': (offset + limit) < Session.objects.filter(client_id=user_id, payment__isnull=False).count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# CLIENT DASHBOARD
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def client_dashboard_stats(request):
    """Get client dashboard statistics"""
    try:
        user_id = request.GET.get('user_id', 1)
        
        # Session statistics
        total_sessions = Session.objects.filter(client_id=user_id).count()
        completed_sessions = Session.objects.filter(client_id=user_id, status='completed').count()
        active_sessions = Session.objects.filter(client_id=user_id, status='active').count()
        
        # Total spent
        total_spent_agg = Session.objects.filter(
            client_id=user_id, 
            status='completed'
        ).aggregate(total_spent=Sum('cost'))
        total_spent = total_spent_agg['total_spent'] or 0
        
        # Favorite professionals count
        try:
            user_profile = UserProfile.objects.get(user_id=user_id)
            favorite_count = len(user_profile.favorite_professionals or [])
        except UserProfile.DoesNotExist:
            favorite_count = 0
        
        return JsonResponse({
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'active_sessions': active_sessions,
            'total_spent': float(total_spent),
            'favorite_professionals': favorite_count,
            'success_rate': round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 2)
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def client_active_sessions(request):
    """Get client's active sessions"""
    try:
        user_id = request.GET.get('user_id', 1)
        
        active_sessions = Session.objects.filter(
            client_id=user_id,
            status__in=['active', 'in_progress', 'pending']
        ).select_related('professional').order_by('-created_at')
        
        sessions_data = []
        for session in active_sessions:
            sessions_data.append({
                'id': session.id,
                'professional_name': session.professional.name,
                'professional_id': session.professional.id,
                'session_type': session.session_type,
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'actual_start': session.actual_start.isoformat() if session.actual_start else None,
                'duration': session.duration or 0,
                'category': session.professional.primary_category.name if session.professional.primary_category else 'General'
            })
        
        return JsonResponse({
            'sessions': sessions_data,
            'count': active_sessions.count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def client_completed_sessions(request):
    """Get client's completed sessions"""
    try:
        user_id = request.GET.get('user_id', 1)
        limit = int(request.GET.get('limit', 20))
        offset = int(request.GET.get('offset', 0))
        
        completed_sessions = Session.objects.filter(
            client_id=user_id,
            status='completed'
        ).select_related('professional').order_by('-created_at')[offset:offset + limit]
        
        sessions_data = []
        for session in completed_sessions:
            sessions_data.append({
                'id': session.id,
                'professional_name': session.professional.name,
                'professional_id': session.professional.id,
                'session_type': session.session_type,
                'status': session.status,
                'created_at': session.created_at.isoformat(),
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                'duration': session.duration or 0,
                'cost': float(session.cost) if session.cost else 0,
                'rating': session.rating,
                'review': session.review,
                'category': session.professional.primary_category.name if session.professional.primary_category else 'General'
            })
        
        return JsonResponse({
            'sessions': sessions_data,
            'total_count': Session.objects.filter(client_id=user_id, status='completed').count(),
            'has_more': (offset + limit) < Session.objects.filter(client_id=user_id, status='completed').count()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# REAL-TIME AVAILABILITY CHECK
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def real_time_availability(request, professional_id):
    """Real-time availability check"""
    try:
        professional = get_object_or_404(Professional, id=professional_id)
        return check_professional_availability(request, professional_id)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def category_professionals(request, category_id):
    """Get professionals by category ID"""
    try:
        category = get_object_or_404(Category, id=category_id)
        return professionals_by_category(request, category.name)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def categories_with_professionals(request):
    """Get categories with professional counts"""
    try:
        categories = Category.objects.filter(enabled=True)
        categories_data = []
        
        for category in categories:
            professional_count = Professional.objects.filter(
                Q(primary_category=category) | Q(categories=category),
                status='approved',
                available=True
            ).distinct().count()
            
            if professional_count > 0:
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'professional_count': professional_count,
                    'icon': category.icon,
                    'color': category.color,
                    'base_price': float(category.base_price)
                })
        
        return JsonResponse({'categories': categories_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# =====================
# PAYMENT GATEWAY INTEGRATION
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def initiate_card_payment(request):
    """Initiate card payment processing"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['amount', 'session_id', 'card_details']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # Extract card details (in production, use proper PCI-compliant processing)
        card_details = data['card_details']
        amount = data['amount']
        session_id = data['session_id']
        
        # Validate session exists
        session = get_object_or_404(Session, id=session_id)
        
        # Simulate card payment processing
        # In production, integrate with payment gateway like Stripe, PayPal, etc.
        transaction_id = f"card_{uuid.uuid4().hex[:8]}_{int(timezone.now().timestamp())}"
        
        # Create pending payment record
        payment = Payment.objects.create(
            session=session,
            amount=amount,
            payment_method='card',
            status='pending',
            transaction_id=transaction_id
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Card payment initiated successfully',
            'payment_reference': transaction_id,
            'payment_id': payment.id,
            'next_step': '3d_secure_verification',
            'amount': float(amount)
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to initiate card payment: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def initiate_bank_transfer(request):
    """Initiate bank transfer payment"""
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['amount', 'session_id', 'bank_details']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        amount = data['amount']
        session_id = data['session_id']
        bank_details = data['bank_details']
        
        # Validate session exists
        session = get_object_or_404(Session, id=session_id)
        
        # Generate bank transfer reference
        transfer_reference = f"BANK{timezone.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        
        # Create pending payment record
        payment = Payment.objects.create(
            session=session,
            amount=amount,
            payment_method='bank_transfer',
            status='pending',
            transaction_id=transfer_reference
        )
        
        # Bank transfer details (would be specific to your bank)
        bank_info = {
            'bank_name': 'Your Bank Name',
            'account_number': '1234567890',
            'account_name': 'TeleConnect Services',
            'branch_code': '123456',
            'reference': transfer_reference,
            'amount': float(amount)
        }
        
        return JsonResponse({
            'success': True,
            'message': 'Bank transfer initiated successfully',
            'transfer_reference': transfer_reference,
            'payment_id': payment.id,
            'bank_details': bank_info,
            'instructions': 'Please transfer the exact amount with the reference provided'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to initiate bank transfer: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def payment_status(request, payment_id):
    """Check payment status"""
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        return JsonResponse({
            'success': True,
            'payment_id': payment.id,
            'transaction_id': payment.transaction_id,
            'amount': float(payment.amount),
            'status': payment.status,
            'payment_method': payment.payment_method,
            'created_at': payment.created_at.isoformat(),
            'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
            'session_id': payment.session_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get payment status: {str(e)}'
        }, status=500)

# =====================
# SESSION VERIFICATION ENDPOINTS
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def verify_session_access(request, session_id):
    """Verify if user has access to session"""
    try:
        user_id = request.GET.get('user_id')
        user_type = request.GET.get('user_type', 'client')
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'User ID is required'
            }, status=400)
        
        session = get_object_or_404(Session, id=session_id)
        
        # Check access based on user type
        has_access = False
        if user_type == 'client':
            has_access = (session.client_id == int(user_id))
        elif user_type == 'professional':
            has_access = (session.professional.id == int(user_id))
        elif user_type == 'admin':
            has_access = True  # Admins have access to all sessions
        
        return JsonResponse({
            'success': True,
            'has_access': has_access,
            'session_id': session_id,
            'user_id': user_id,
            'user_type': user_type,
            'session_status': session.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Verification failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_session_participants(request, session_id):
    """Get session participants information"""
    try:
        session = get_object_or_404(Session, id=session_id)
        
        participants = {
            'professional': {
                'id': session.professional.id,
                'name': session.professional.name,
                'email': session.professional.email,
                'phone': session.professional.phone,
                'specialization': session.professional.specialization,
                'online_status': session.professional.online_status
            },
            'client': {
                'id': session.client_id,
                'name': f"Client {session.client_id}",  # In production, get from User model
                'email': f"client{session.client_id}@example.com"  # Placeholder
            }
        }
        
        return JsonResponse({
            'success': True,
            'session_id': session_id,
            'participants': participants,
            'session_type': session.session_type,
            'session_status': session.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get participants: {str(e)}'
        }, status=500)

# =====================
# AI MATCHING ALGORITHM ENDPOINTS
# =====================

@csrf_exempt
@require_http_methods(["POST"])
def run_matching_algorithm(request):
    """Run AI matching algorithm to find best professionals"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['category_id', 'client_id']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        category_id = data['category_id']
        client_id = data['client_id']
        preferences = data.get('preferences', {})
        
        # Get category
        category = get_object_or_404(Category, id=category_id)
        
        # Get available professionals in this category
        professionals = Professional.objects.filter(
            Q(primary_category=category) | Q(categories=category),
            status='approved',
            available=True
        ).distinct()
        
        # Calculate matching scores for each professional
        matched_professionals = []
        for professional in professionals:
            score = calculate_matching_score(professional, preferences)
            
            matched_professionals.append({
                'professional': {
                    'id': professional.id,
                    'name': professional.name,
                    'specialization': professional.specialization,
                    'rate': float(professional.rate),
                    'available': professional.available,
                    'online_status': professional.online_status,
                    'average_rating': float(professional.average_rating),
                    'total_sessions': professional.total_sessions,
                    'experience_years': professional.experience_years,
                    'response_time': professional.avg_response_time
                },
                'matching_score': score['total_score'],
                'score_breakdown': score['breakdown'],
                'recommendation_reason': score['reason']
            })
        
        # Sort by matching score (descending)
        matched_professionals.sort(key=lambda x: x['matching_score'], reverse=True)
        
        return JsonResponse({
            'success': True,
            'category': category.name,
            'matched_professionals': matched_professionals[:10],  # Top 10 matches
            'total_matches': len(matched_professionals),
            'algorithm_version': 'v1.0'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Matching algorithm failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def calculate_matching_scores(request):
    """Calculate matching scores for professionals"""
    try:
        professional_ids = request.GET.get('professional_ids', '').split(',')
        category_id = request.GET.get('category_id')
        client_preferences = request.GET.get('preferences', '{}')
        
        if not professional_ids or professional_ids == ['']:
            return JsonResponse({
                'success': False,
                'message': 'Professional IDs are required'
            }, status=400)
        
        preferences = json.loads(client_preferences)
        
        scores_data = []
        for pro_id in professional_ids:
            try:
                professional = Professional.objects.get(id=pro_id)
                score = calculate_matching_score(professional, preferences)
                
                scores_data.append({
                    'professional_id': professional.id,
                    'professional_name': professional.name,
                    'matching_score': score['total_score'],
                    'score_breakdown': score['breakdown']
                })
            except Professional.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'scores': scores_data,
            'preferences_used': preferences
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to calculate scores: {str(e)}'
        }, status=500)

def calculate_matching_score(professional, preferences):
    """Calculate matching score for a professional based on preferences"""
    breakdown = {}
    total_score = 0
    
    # Availability score (30%)
    availability_score = 0
    if professional.online_status:
        availability_score += 0.7
    if professional.available:
        availability_score += 0.3
    breakdown['availability'] = availability_score
    total_score += availability_score * 0.3
    
    # Rating score (25%)
    rating_score = (professional.average_rating / 5.0) if professional.average_rating else 0.5
    breakdown['rating'] = rating_score
    total_score += rating_score * 0.25
    
    # Experience score (20%)
    experience_score = min((professional.experience_years or 1) / 10.0, 1.0)
    breakdown['experience'] = experience_score
    total_score += experience_score * 0.2
    
    # Response time score (15%)
    response_time_map = {
        '< 1 hour': 1.0,
        '< 2 hours': 0.9,
        '< 4 hours': 0.7,
        '< 8 hours': 0.5,
        '< 24 hours': 0.3
    }
    response_score = response_time_map.get(professional.avg_response_time or '< 4 hours', 0.2)
    breakdown['response_time'] = response_score
    total_score += response_score * 0.15
    
    # Price match score (10%)
    preferred_rate = preferences.get('max_rate')
    if preferred_rate and professional.rate:
        price_score = max(0, 1 - (professional.rate / preferred_rate))
        breakdown['price_match'] = price_score
        total_score += price_score * 0.1
    else:
        breakdown['price_match'] = 0.5
        total_score += 0.05
    
    # Generate recommendation reason
    reason = generate_recommendation_reason(professional, breakdown)
    
    return {
        'total_score': round(total_score, 3),
        'breakdown': breakdown,
        'reason': reason
    }

def generate_recommendation_reason(professional, breakdown):
    """Generate human-readable recommendation reason"""
    reasons = []
    
    if breakdown['availability'] >= 0.8:
        reasons.append("Highly available")
    elif breakdown['availability'] >= 0.5:
        reasons.append("Good availability")
    
    if breakdown['rating'] >= 0.9:
        reasons.append("Excellent ratings")
    elif breakdown['rating'] >= 0.7:
        reasons.append("Great reviews")
    
    if breakdown['experience'] >= 0.8:
        reasons.append("Extensive experience")
    elif breakdown['experience'] >= 0.5:
        reasons.append("Good experience level")
    
    if breakdown['response_time'] >= 0.8:
        reasons.append("Quick responder")
    
    if not reasons:
        reasons.append("Good overall match")
    
    return ", ".join(reasons)

# =====================
# USER PREFERENCES & SETTINGS
# =====================

@csrf_exempt
@require_http_methods(["GET", "POST", "PUT"])
def user_preferences(request):
    """Get, create, or update user preferences"""
    try:
        user_id = request.GET.get('user_id') or json.loads(request.body).get('user_id') if request.body else None
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'User ID is required'
            }, status=400)
        
        if request.method == 'GET':
            # Get user preferences
            try:
                user_profile = UserProfile.objects.get(user_id=user_id)
                preferences = getattr(user_profile, 'preferences', {})
            except UserProfile.DoesNotExist:
                preferences = {}
            
            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'preferences': preferences
            })
        
        elif request.method in ['POST', 'PUT']:
            # Update user preferences
            data = json.loads(request.body)
            preferences = data.get('preferences', {})
            
            user_profile, created = UserProfile.objects.get_or_create(user_id=user_id)
            user_profile.preferences = preferences
            user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Preferences updated successfully',
                'user_id': user_id,
                'preferences': user_profile.preferences
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Preferences operation failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def notification_settings(request):
    """Get or update notification settings"""
    try:
        user_id = request.GET.get('user_id') or json.loads(request.body).get('user_id') if request.body else None
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'User ID is required'
            }, status=400)
        
        if request.method == 'GET':
            # Get notification settings
            try:
                user_profile = UserProfile.objects.get(user_id=user_id)
                notification_settings = getattr(user_profile, 'notification_settings', {
                    'email_notifications': True,
                    'push_notifications': True,
                    'sms_notifications': False,
                    'session_reminders': True,
                    'promotional_emails': False
                })
            except UserProfile.DoesNotExist:
                notification_settings = {
                    'email_notifications': True,
                    'push_notifications': True,
                    'sms_notifications': False,
                    'session_reminders': True,
                    'promotional_emails': False
                }
            
            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'notification_settings': notification_settings
            })
        
        elif request.method == 'POST':
            # Update notification settings
            data = json.loads(request.body)
            settings = data.get('notification_settings', {})
            
            user_profile, created = UserProfile.objects.get_or_create(user_id=user_id)
            user_profile.notification_settings = settings
            user_profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Notification settings updated successfully',
                'user_id': user_id,
                'notification_settings': user_profile.notification_settings
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Notification settings operation failed: {str(e)}'
        }, status=500)

# =====================
# SUPPORT & HELP ENDPOINTS
# =====================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def support_tickets(request):
    """Get or create support tickets"""
    try:
        user_id = request.GET.get('user_id') or json.loads(request.body).get('user_id') if request.body else None
        
        if request.method == 'GET':
            # Get user's support tickets
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User ID is required'
                }, status=400)
            
            # In a real implementation, you'd have a SupportTicket model
            # For now, return mock data
            tickets = [
                {
                    'id': 1,
                    'subject': 'Payment Issue',
                    'status': 'resolved',
                    'created_at': '2024-01-15T10:30:00Z',
                    'last_updated': '2024-01-16T14:20:00Z'
                },
                {
                    'id': 2,
                    'subject': 'Session Connection Problem',
                    'status': 'in_progress',
                    'created_at': '2024-01-20T09:15:00Z',
                    'last_updated': '2024-01-20T11:45:00Z'
                }
            ]
            
            return JsonResponse({
                'success': True,
                'user_id': user_id,
                'tickets': tickets
            })
        
        elif request.method == 'POST':
            # Create new support ticket
            data = json.loads(request.body)
            
            required_fields = ['user_id', 'subject', 'message']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'success': False,
                        'message': f'{field} is required'
                    }, status=400)
            
            # In a real implementation, create SupportTicket object
            ticket_data = {
                'id': int(timezone.now().timestamp()),
                'subject': data['subject'],
                'message': data['message'],
                'category': data.get('category', 'general'),
                'priority': data.get('priority', 'medium'),
                'status': 'open',
                'created_at': timezone.now().isoformat(),
                'user_id': data['user_id']
            }
            
            return JsonResponse({
                'success': True,
                'message': 'Support ticket created successfully',
                'ticket_id': ticket_data['id'],
                'ticket': ticket_data
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Support tickets operation failed: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def contact_support(request):
    """Contact support directly"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['name', 'email', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False,
                    'message': f'{field} is required'
                }, status=400)
        
        # In production, this would send an email to support
        contact_data = {
            'name': data['name'],
            'email': data['email'],
            'subject': data['subject'],
            'message': data['message'],
            'category': data.get('category', 'general'),
            'user_id': data.get('user_id'),
            'timestamp': timezone.now().isoformat()
        }
        
        return JsonResponse({
            'success': True,
            'message': 'Your message has been sent to support. We will respond within 24 hours.',
            'reference_id': f"SUP{timezone.now().strftime('%Y%m%d%H%M%S')}",
            'contact_data': contact_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Contact support failed: {str(e)}'
        }, status=500)

# =====================
# ANALYTICS & REPORTING
# =====================

@csrf_exempt
@require_http_methods(["GET"])
def session_metrics(request):
    """Get session metrics and analytics"""
    try:
        time_range = request.GET.get('time_range', '30d')  # 7d, 30d, 90d, 1y
        
        # Calculate time range
        if time_range == '7d':
            start_date = timezone.now() - timedelta(days=7)
        elif time_range == '90d':
            start_date = timezone.now() - timedelta(days=90)
        elif time_range == '1y':
            start_date = timezone.now() - timedelta(days=365)
        else:  # 30d default
            start_date = timezone.now() - timedelta(days=30)
        
        # Session statistics
        total_sessions = Session.objects.filter(created_at__gte=start_date).count()
        completed_sessions = Session.objects.filter(status='completed', created_at__gte=start_date).count()
        active_sessions = Session.objects.filter(status='active', created_at__gte=start_date).count()
        cancelled_sessions = Session.objects.filter(status='cancelled', created_at__gte=start_date).count()
        
        # Session types distribution
        session_types = Session.objects.filter(created_at__gte=start_date).values('session_type').annotate(
            count=Count('id')
        )
        
        # Average session duration
        avg_duration = Session.objects.filter(
            status='completed', 
            created_at__gte=start_date
        ).aggregate(avg_duration=Avg('duration'))['avg_duration'] or 0
        
        # Completion rate
        completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        return JsonResponse({
            'success': True,
            'time_range': time_range,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
            'metrics': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'active_sessions': active_sessions,
                'cancelled_sessions': cancelled_sessions,
                'completion_rate': round(completion_rate, 2),
                'average_duration_minutes': round(avg_duration, 2)
            },
            'session_types': {item['session_type']: item['count'] for item in session_types},
            'summary': {
                'total_sessions': total_sessions,
                'success_rate': round(completion_rate, 2),
                'avg_session_duration': round(avg_duration, 2)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get session metrics: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def payment_metrics(request):
    """Get payment metrics and analytics"""
    try:
        time_range = request.GET.get('time_range', '30d')
        
        # Calculate time range
        if time_range == '7d':
            start_date = timezone.now() - timedelta(days=7)
        elif time_range == '90d':
            start_date = timezone.now() - timedelta(days=90)
        elif time_range == '1y':
            start_date = timezone.now() - timedelta(days=365)
        else:  # 30d default
            start_date = timezone.now() - timedelta(days=30)
        
        # Payment statistics
        total_revenue = Session.objects.filter(
            status='completed',
            created_at__gte=start_date
        ).aggregate(total_revenue=Sum('cost'))['total_revenue'] or 0
        
        successful_payments = Payment.objects.filter(
            status='completed',
            created_at__gte=start_date
        ).count()
        
        failed_payments = Payment.objects.filter(
            status='failed',
            created_at__gte=start_date
        ).count()
        
        pending_payments = Payment.objects.filter(
            status='pending',
            created_at__gte=start_date
        ).count()
        
        # Payment methods distribution
        payment_methods = Payment.objects.filter(created_at__gte=start_date).values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        )
        
        # Average transaction value
        avg_transaction = Payment.objects.filter(
            status='completed',
            created_at__gte=start_date
        ).aggregate(avg_amount=Avg('amount'))['avg_amount'] or 0
        
        return JsonResponse({
            'success': True,
            'time_range': time_range,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
            'metrics': {
                'total_revenue': float(total_revenue),
                'successful_payments': successful_payments,
                'failed_payments': failed_payments,
                'pending_payments': pending_payments,
                'success_rate': round((successful_payments / (successful_payments + failed_payments) * 100) if (successful_payments + failed_payments) > 0 else 0, 2),
                'average_transaction_value': float(avg_transaction)
            },
            'payment_methods': [
                {
                    'method': item['payment_method'],
                    'count': item['count'],
                    'total_amount': float(item['total_amount'] or 0)
                }
                for item in payment_methods
            ],
            'summary': {
                'total_revenue': float(total_revenue),
                'transaction_count': successful_payments,
                'avg_transaction_value': float(avg_transaction)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get payment metrics: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def user_engagement(request):
    """Get user engagement metrics"""
    try:
        time_range = request.GET.get('time_range', '30d')
        
        # Calculate time range
        if time_range == '7d':
            start_date = timezone.now() - timedelta(days=7)
        elif time_range == '90d':
            start_date = timezone.now() - timedelta(days=90)
        elif time_range == '1y':
            start_date = timezone.now() - timedelta(days=365)
        else:  # 30d default
            start_date = timezone.now() - timedelta(days=30)
        
        # User statistics
        total_users = User.objects.filter(date_joined__gte=start_date).count()
        active_users = User.objects.filter(
            last_login__gte=start_date
        ).count()
        
        # New registrations
        new_registrations = User.objects.filter(date_joined__gte=start_date).count()
        
        # Session per user
        sessions_per_user = Session.objects.filter(
            created_at__gte=start_date
        ).values('client_id').annotate(session_count=Count('id'))
        
        avg_sessions_per_user = sessions_per_user.aggregate(avg=Avg('session_count'))['avg'] or 0
        
        # User retention (simplified)
        returning_users = User.objects.filter(
            last_login__gte=start_date,
            date_joined__lt=start_date
        ).count()
        
        return JsonResponse({
            'success': True,
            'time_range': time_range,
            'start_date': start_date.isoformat(),
            'end_date': timezone.now().isoformat(),
            'metrics': {
                'total_users': total_users,
                'active_users': active_users,
                'new_registrations': new_registrations,
                'returning_users': returning_users,
                'avg_sessions_per_user': round(avg_sessions_per_user, 2),
                'activation_rate': round((active_users / total_users * 100) if total_users > 0 else 0, 2)
            },
            'engagement_metrics': {
                'daily_active_users': active_users,  # Simplified
                'monthly_active_users': active_users,  # Simplified
                'user_growth_rate': round((new_registrations / total_users * 100) if total_users > 0 else 0, 2)
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Failed to get user engagement metrics: {str(e)}'
        }, status=500)

# =====================
# HELPER FUNCTIONS
# =====================

def calculate_availability_score(professional):
    """Calculate availability score for professional"""
    score = 0
    if professional.online_status:
        score += 0.4
    if professional.available:
        score += 0.3
    if hasattr(professional, 'last_active'):
        hours_since_active = (timezone.now() - professional.last_active).total_seconds() / 3600
        if hours_since_active < 1:
            score += 0.3
        elif hours_since_active < 4:
            score += 0.2
        elif hours_since_active < 12:
            score += 0.1
    return min(score, 1.0)

def calculate_bayesian_rating_score(professional):
    """Calculate Bayesian rating score"""
    bayesian_constant = 10
    average_rating = 4.0
    reviews = professional.total_sessions or 1
    
    bayesian_score = (professional.average_rating * reviews + average_rating * bayesian_constant) / (reviews + bayesian_constant)
    return (bayesian_score - 1) / 4  # Normalize to 0-1

def calculate_response_time_score(professional):
    """Calculate response time score"""
    response_times = {
        '< 1 hour': 1.0,
        '< 2 hours': 0.9,
        '< 4 hours': 0.7,
        '< 8 hours': 0.5,
        '< 24 hours': 0.3
    }
    avg_response = professional.avg_response_time or '< 4 hours'
    return response_times.get(avg_response, 0.2)

def calculate_experience_score(professional):
    """Calculate experience score"""
    experience = professional.experience_years or 1
    return min(experience / 10.0, 1.0)  # Cap at 10 years

def get_professional_skills(professional):
    """Extract skills from professional data"""
    skills = []
    if professional.specialization:
        skills.append(professional.specialization)
    if professional.bio:
        # Simple keyword extraction from bio
        bio_keywords = ['consulting', 'advice', 'expert', 'specialist', 'professional']
        for keyword in bio_keywords:
            if keyword in professional.bio.lower():
                skills.append(keyword.title())
    return skills[:5]  # Return max 5 skills

def calculate_estimated_wait_time(professional, current_workload):
    """Calculate estimated wait time for professional"""
    base_wait_time = 5  # minutes
    workload_multiplier = current_workload * 2
    return base_wait_time + workload_multiplier

def update_professional_rating(professional):
    """Update professional's average rating"""
    sessions = Session.objects.filter(professional=professional, rating__isnull=False)
    if sessions.exists():
        avg_rating = sessions.aggregate(avg_rating=Avg('rating'))['avg_rating']
        professional.average_rating = avg_rating
        professional.save()