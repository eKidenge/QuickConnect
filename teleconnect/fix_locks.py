# fix_locks.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teleconnect.settings')
django.setup()

from quickconnect.models import Professional

def fix_professional_locks():
    print("🔧 Fixing professional locking inconsistencies...")
    
    # Fix professionals that are locked but marked as available
    inconsistent = Professional.objects.filter(locked_by__isnull=False, available=True)
    print(f"Found {inconsistent.count()} professionals with inconsistent locks")
    
    for pro in inconsistent:
        pro.available = False
        pro.save()
        print(f"Fixed: {pro.name} - set available to False")
    
    # Fix professionals with invalid lock values
    invalid = Professional.objects.filter(locked_by="PROFESSION")
    print(f"Found {invalid.count()} professionals with invalid lock values")
    
    for pro in invalid:
        pro.locked_by = None
        pro.available = True
        pro.save()
        print(f"Fixed invalid lock: {pro.name}")
    
    # Fix professionals with empty string locks
    empty_locks = Professional.objects.filter(locked_by="")
    for pro in empty_locks:
        pro.locked_by = None
        pro.available = True
        pro.save()
        print(f"Fixed empty lock: {pro.name}")
    
    print("✅ Database locking consistency fixed!")

if __name__ == "__main__":
    fix_professional_locks()