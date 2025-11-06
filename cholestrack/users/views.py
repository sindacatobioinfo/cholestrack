# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login # para o login
from django.contrib.auth.decorators import login_required 

# 1. View de Cadastro (Register)
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Opcional: Logar o usuário automaticamente após o cadastro
            # login(request, user) 
            return redirect('login') # Redireciona para a página de login após o cadastro
    else:
        form = UserCreationForm()
        
    # Renderiza o template de cadastro. O caminho completo é 'templates/users/register.html'
    return render(request, 'users/register.html', {'form': form})


# 2. View de Login Simples (Usando o formulário nativo do Django para testes iniciais)
def login_user(request):
    # Geralmente é melhor usar a View nativa do Django (django.contrib.auth.views.LoginView),
    # mas para manter as coisas simples por agora e usar seu template, vamos apenas renderizar.
    # A implementação completa do login com o AuthenticationForm é mais complexa e
    # recomendaria usar a classe nativa do Django.
    return render(request, 'users/login.html', {})

# users/views.py

# 3. View de Home/Dashboard (O que o usuário vê após logar)
# O decorador garante que, se o usuário não estiver logado, será redirecionado para a URL de login.
@login_required
def home(request):
    # Passa o nome de usuário para mostrar na página
    context = {
        'message': f'Bem-vindo(a) ao Cholestrack, {request.user.username}!',
        'user_name': request.user.username
    }
    # Por enquanto, renderizamos o base.html. Você deve criar um home.html mais tarde.
    return render(request, 'base.html', context)
    
# A função login_user() foi substituída pela LoginView em users/urls.py
