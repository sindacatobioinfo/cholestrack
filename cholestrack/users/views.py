# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login # para o login
from django.contrib.auth.decorators import login_required 
from django.views.decorators.cache import never_cache 
from .models import Patient, AnalysisFileLocation
# NOVO: Importe o FileResponse para download
from django.http import FileResponse, HttpResponse
from django.contrib.auth.views import LoginView as DjangoLoginView # <--- Esta linha está faltando

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
class CholestrackLoginView(DjangoLoginView):
    # Diz ao Django para usar o seu template personalizado
    template_name = 'users/login.html' 
    # Opcional: define qual formulário usar (padrão é AuthenticationForm)
    # form_class = AuthenticationForm

# 3. View de Home/Dashboard (O que o usuário vê após logar)
@login_required
@never_cache # <--  Garante que a página não fica em cache no navegador
def home(request):
    
    all_patients = Patient.objects.all().prefetch_related('file_locations')
    patient_data = []
    
    for patient in all_patients:
        # Prepara a lista de arquivos disponíveis para a tabela
        
        available_files = {}
        # Inicializa metadados do arquivo (pega do primeiro arquivo relacionado)
        file_metadata = {
            'project': 'N/D', 
            'batch': 'N/D', 
            'sample_id': 'N/D', 
            'data_type': 'N/D'
        }
        
        locations = list(patient.file_locations.all())
        
        # Se houver localizações, pegamos os metadados do primeiro registro
        if locations:
            first_location = locations[0]
            # Extrai os novos campos usando os nomes definidos em models.py
            file_metadata['project'] = getattr(first_location, 'project_name', 'N/D')
            file_metadata['batch'] = getattr(first_location, 'batch_id', 'N/D')
            file_metadata['sample_id'] = getattr(first_location, 'sample_id', 'N/D')
            file_metadata['data_type'] = getattr(first_location, 'data_type', 'N/D').upper()
            
            # Mapeia todos os arquivos para a coluna de download
            for location in locations:
                available_files[location.file_type] = {
                    'id': location.id,
                    'server': location.server_name
                }


        patient_data.append({
            'patient_id': patient.patient_id,
            'name': patient.name,
            'main_result': getattr(patient, 'main_exome_result', 'N/D'), 
            'clinical_preview': patient.clinical_info_json.get('diagnostico', 'N/D') if patient.clinical_info_json else 'N/D',
            'files': available_files,
            # NOVOS DADOS enviados para o template
            'project': file_metadata['project'],
            'batch': file_metadata['batch'],
            'sample_id': file_metadata['sample_id'],
            'data_type': file_metadata['data_type'],
        })
        
    context = {
        'patient_list': patient_data,
        'user_name': request.user.username
    }
    
    return render(request, 'home.html', context)

# B. View para Download Seguro (Coração da segurança do arquivo)
@login_required
def download_file(request, file_location_id):
    # Esta View só deve aceitar requisições POST para evitar ataques CSRF e downloads acidentais
    if request.method != 'POST':
        return redirect('home')

    try:
        # 1. Busca a localização do arquivo usando o ID fornecido pelo frontend (ID SECRETO)
        file_location = AnalysisFileLocation.objects.get(id=file_location_id)
        
        # 2. Permissão: Assumimos que o usuário logado tem permissão.
        
        # 3. Monta o caminho completo interno do arquivo
        # ATENÇÃO: ESTE É O CAMINHO SECRETO DO SEU SERVIDOR!
        # Exemplo: /server1_data/caminho/do/arquivo/HG001.vcf
        full_path = f"/{file_location.server_name.lower()}_data/{file_location.file_path}"
        
        # 4. Implementação do Download (Mock ou Real)
        
        # MOCKUP DE DOWNLOAD SEGURO (SUBSTITUA PELA SUA LÓGICA SFTP/FTP REAL DE STREAMING!)
        
        # Este é apenas um placeholder para demonstrar que o Django interceptou a requisição 
        # e encontrou o caminho secreto, mas não o está mostrando ao cliente.
        
        response = HttpResponse(
            f"Download iniciado. Caminho SECRETO interno encontrado: {full_path}. Tipo: {file_location.file_type}.", 
            content_type='text/plain'
        )
        
        # Define o nome do arquivo que será salvo no computador do usuário
        response['Content-Disposition'] = f'attachment; filename="{file_location.patient.patient_id}_{file_location.file_type}.txt"'
        
        return response
        
    except AnalysisFileLocation.DoesNotExist:
        # Redireciona se o arquivo não for encontrado (segurança)
        return redirect('home')
    except Exception as e:
        # Logar o erro
        print(f"Erro no download seguro: {e}")
        return redirect('home')