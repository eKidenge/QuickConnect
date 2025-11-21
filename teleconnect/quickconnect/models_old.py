from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Category
import json

@csrf_exempt
@require_http_methods(["GET", "POST"])
def categories_list(request):
    """
    Handle GET (list categories) and POST (create category) requests
    """
    if request.method == 'GET':
        try:
            # Get all categories from database
            categories = Category.objects.all()
            categories_data = []
            
            for category in categories:
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'base_price': float(category.base_price),
                    'enabled': category.enabled,
                    'professional_count': category.professional_count,
                    'session_count': category.session_count,
                    'created_at': category.created_at.isoformat() if category.created_at else None,
                    'updated_at': category.updated_at.isoformat() if category.updated_at else None,
                })
            
            return JsonResponse({'categories': categories_data})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create new category in database
            category = Category.objects.create(
                name=data.get('name', ''),
                description=data.get('description', ''),
                base_price=data.get('base_price', 0),
                enabled=data.get('enabled', True),
                professional_count=0,
                session_count=0,
            )
            
            return JsonResponse({
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'base_price': float(category.base_price),
                'enabled': category.enabled,
                'professional_count': category.professional_count,
                'session_count': category.session_count,
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
    Handle category updates
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
        
        category.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Category {category_id} updated successfully',
            'category': {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'base_price': float(category.base_price),
                'enabled': category.enabled,
                'professional_count': category.professional_count,
                'session_count': category.session_count,
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
    Handle category deletion
    """
    try:
        category = Category.objects.get(id=category_id)
        category.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Category {category_id} deleted successfully'
        })
        
    except Category.DoesNotExist:
        return JsonResponse({'error': 'Category not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)