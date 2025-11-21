# list_professions.py

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teleconnect.settings')
django.setup()

from quickconnect.models import Professional, Category, SubCategory

def main():
    print("\n=== PROFESSIONALS AND THEIR CATEGORIES ===\n")

    for prof in Professional.objects.all():
        username = prof.user.username if hasattr(prof.user, 'username') else str(prof.user)
        print(f"Professional: {username}")
        
        # Primary category
        primary_cat = prof.primary_category.name if prof.primary_category else "None"
        print(f"  Primary Category: {primary_cat}")

        # All categories
        categories = [c.name for c in prof.categories.all()]
        print(f"  Other Categories: {categories if categories else 'None'}")

        # All subcategories
        subcategories = [s.name for s in prof.subcategories.all()]
        print(f"  Subcategories: {subcategories if subcategories else 'None'}\n")

    print("\n=== CATEGORIES AND THEIR PROFESSIONALS ===\n")

    for cat in Category.objects.all():
        print(f"Category: {cat.name}")
        professionals = [p.user.username for p in cat.professionals.all()]
        print(f"  Professionals: {professionals if professionals else 'None'}\n")

    print("\n=== SUBCATEGORIES AND THEIR PROFESSIONALS ===\n")

    for sub in SubCategory.objects.all():
        print(f"SubCategory: {sub.name} (Category: {sub.category.name})")
        professionals = [p.user.username for p in sub.professionals.all()]
        print(f"  Professionals: {professionals if professionals else 'None'}\n")


if __name__ == "__main__":
    main()
