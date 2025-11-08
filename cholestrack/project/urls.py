# cholestrack/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Inclui todas as URLs definidas em users/urls.py
    path('', include('users.urls')), 
    
    # CORREÇÃO: Redireciona o caminho raiz ('/') para a URL nomeada 'users:home'
    path('', lambda request: redirect('users:home'), name='root_redirect'),
]