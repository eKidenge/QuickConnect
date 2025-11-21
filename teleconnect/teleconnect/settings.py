"""
Django settings for teleconnect project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-bcok+%c17r==+dy!s&xx6cc75mp(^i@(_yz&#9xa1d+uiy#2d5'

DEBUG = True

ALLOWED_HOSTS = ['192.168.100.38', '192.168.0.122', '192.168.0.192', 'localhost', '127.0.0.1', '0.0.0.0']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'channels',
    'rest_framework',
    'rest_framework.authtoken',  # ADDED: Token authentication
    'corsheaders',

    # Local apps
    'quickconnect',
    'users',  # Add this line
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS first
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'teleconnect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'teleconnect.wsgi.application'
ASGI_APPLICATION = 'teleconnect.asgi.application'  # <-- needed for Channels

# Channels layers (in-memory for dev; Redis recommended for production)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # For collectstatic
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files (user uploaded content)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework settings - UPDATED with Token Authentication
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',  # ADDED: Token authentication
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
}

# CORS settings - UPDATED WITH COMPREHENSIVE CONFIG
CORS_ALLOW_ALL_ORIGINS = True  # For development only - allows all origins

# Specific allowed origins (more secure alternative)
CORS_ALLOWED_ORIGINS = [
    # React Native Development Servers
    "http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:19006",  # Expo default
    "http://localhost:19000",  # Expo dev tools
    "http://localhost:3000",
    
    # Local IP addresses with various ports
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082", 
    "http://127.0.0.1:19006",
    "http://127.0.0.1:3000",
    
    # Your specific IPs
    "http://10.106.110.181:8081",
    "http://10.106.110.181:8082",
    "http://192.168.100.38:8081",
    "http://192.168.100.38:8082",
    "http://192.168.0.122:8081", 
    "http://192.168.0.122:8082",
    "http://192.168.0.192:8081",
    "http://192.168.0.192:8082",
    
    # Add any other development URLs you use
    "http://0.0.0.0:8081",
    "http://0.0.0.0:8082",
]

# Regex patterns for dynamic ports during development
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
    r"^http://192\.168\.\d+\.\d+:\d+$",
    r"^http://10\.\d+\.\d+\.\d+:\d+$",
    r"^http://0\.0\.0\.0:\d+$",
]

# CSRF trusted origins for POST requests
CSRF_TRUSTED_ORIGINS = [
	"http://localhost:8081",
    "http://localhost:8082",
    "http://localhost:19006",
    "http://127.0.0.1:8081",
    "http://127.0.0.1:8082",
    "http://10.106.110.181:8081",
    "http://10.106.110.181:8082",
    "http://192.168.100.38:8081",
    "http://192.168.100.38:8082",
    "http://192.168.0.122:8081",
    "http://192.168.0.122:8082",
    "http://192.168.0.192:8081",
    "http://192.168.0.192:8082",
]

# CORS methods and headers
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET', 
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-auth-token',  # Custom headers if needed
]

# Additional CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours