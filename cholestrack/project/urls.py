# project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('profile/', include('profile.urls')),
    path('home/', include('home.urls')),
    path('samples/', include('samples.urls')),
    path('files/', include('files.urls')),
    path('', lambda request: redirect('users:login') if not request.user.is_authenticated else redirect('home:dashboard'), name='root_redirect'),
]