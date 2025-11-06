# users/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Importa as views nativas de autenticação

urlpatterns = [
    # 1. Rota de Home/Dashboard
    path('', views.home, name='home'), 
    
    # 2. Rota de Cadastro (Register)
    path('register/', views.register, name='register'),
    
    # 3. Rota de Login (Usando a view nativa do Django)
    # Dizemos ao LoginView para usar nosso template específico: 'users/login.html'
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    
    # 4. Rota de Logout (Usando a view nativa do Django)
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), 
]