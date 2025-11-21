# release_all.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teleconnect.settings')
django.setup()

from quickconnect.models import Professional

# Release ALL professionals for fresh start
Professional.objects.all().update(locked_by=None, available=True)
print("✅ All professionals released and available for testing!")