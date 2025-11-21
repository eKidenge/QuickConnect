# routing.py
from django.urls import re_path
from .consumers import QuickConnectConsumer, SessionConsumer

websocket_urlpatterns = [
    re_path(r'ws/quick-connect/$', QuickConnectConsumer.as_asgi()),
    re_path(r'ws/session/(?P<professional_id>[^/]+)/(?P<client_id>[^/]+)/$', SessionConsumer.as_asgi()),
]