# users/urls.py
from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import CholestrackLoginView

# O namespace é importante para referenciar as URLs como 'users:home'
app_name = 'users'

urlpatterns = [
    # Rotas de Autenticação
    path('register/', views.register, name='register'),
    
    # CORREÇÃO: Usando a View de Classe do Django, apontando para o seu template
    # O .as_view() é necessário para classes
    path('login/', CholestrackLoginView.as_view(), name='login'),    
    # A view nativa do Django é recomendada para Logout por questões de segurança (POST)
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'), 
    
    # Rota Principal (Dashboard pós-login)
    path('home/', views.home, name='home'),
    
    # Rota de Download (Segura - usa o ID da localização, que é o 'file_location_id' da View)
    # Note que a URL utiliza um inteiro (int) como parâmetro, que será passado para a função download_file
    path('download/<int:file_location_id>/', views.download_file, name='download_file'),
]