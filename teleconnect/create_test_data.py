# create_test_data.py

import os
import django

# 1️⃣ Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teleconnect.settings")

# 2️⃣ Initialize Django
django.setup()

# 3️⃣ Now you can import Django apps and models
from django.apps import apps

# Get the quickconnect app
app = apps.get_app_config('quickconnect')

# List all models in quickconnect
for model in app.get_models():
    print(f"\nMODEL: {model.__name__}")
    has_rel = False
    for field in model._meta.get_fields():
        if field.is_relation:
            has_rel = True
            rel_type = field.get_internal_type()
            target = field.related_model.__name__ if field.related_model else None
            print(f"  • {field.name:<25} {rel_type:<18} -> {target}")
    if not has_rel:
        print("  (No relationships)")
