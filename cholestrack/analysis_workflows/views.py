# analysis_workflows/views.py
"""
Views for workflow configuration and YAML generation.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from users.decorators import role_confirmed_required
from .forms import WorkflowConfigForm
from .models import WorkflowConfiguration
from .utils import generate_workflow_yaml, get_config_summary


@login_required
@role_confirmed_required
def config_builder(request):
    """
    Main view for building workflow configuration.
    """
    if request.method == 'POST':
        form = WorkflowConfigForm(request.POST)

        if form.is_valid():
            # Extract form data
            config_data = {
                'project_name': form.cleaned_data['project_name'],
                'model_type': form.cleaned_data['model_type'],
                'aligner': form.cleaned_data['aligner'],
                'minimap2_preset': form.cleaned_data['minimap2_preset'],
                'use_gatk': form.cleaned_data['use_gatk'],
                'use_strelka': form.cleaned_data['use_strelka'],
                'use_deepvariant': form.cleaned_data['use_deepvariant'],
                'run_annovar': form.cleaned_data['run_annovar'],
                'run_vep': form.cleaned_data['run_vep'],
            }

            # Save configuration if name is provided
            if form.cleaned_data.get('name'):
                config = form.save(commit=False)
                config.user = request.user
                config.save()
                messages.success(request, f'Configuration "{config.name}" saved successfully!')

            # Store in session for preview/download
            request.session['workflow_config'] = config_data

            return redirect('analysis_workflows:preview')
    else:
        # Initialize with default values
        form = WorkflowConfigForm(initial={
            'project_name': 'workflow_test',
            'model_type': 'WES',
            'aligner': 'minimap2',
            'minimap2_preset': 'sr',
            'use_gatk': True,
            'use_strelka': True,
            'use_deepvariant': False,
            'run_annovar': False,
            'run_vep': True,
        })

    context = {
        'form': form,
        'title': 'Workflow Configuration Builder'
    }
    return render(request, 'analysis_workflows/config_builder.html', context)


@login_required
@role_confirmed_required
def preview_config(request):
    """
    Preview the generated YAML configuration.
    """
    config_data = request.session.get('workflow_config')

    if not config_data:
        messages.warning(request, 'No configuration data found. Please configure your workflow first.')
        return redirect('analysis_workflows:config_builder')

    # Generate YAML content
    yaml_content = generate_workflow_yaml(config_data)

    # Get summary
    summary = get_config_summary(config_data)

    context = {
        'yaml_content': yaml_content,
        'summary': summary,
        'title': 'Configuration Preview'
    }
    return render(request, 'analysis_workflows/preview.html', context)


@login_required
@role_confirmed_required
def download_config(request):
    """
    Download the generated YAML configuration file.
    """
    config_data = request.session.get('workflow_config')

    if not config_data:
        messages.warning(request, 'No configuration data found. Please configure your workflow first.')
        return redirect('analysis_workflows:config_builder')

    # Generate YAML content
    yaml_content = generate_workflow_yaml(config_data)

    # Create HTTP response with YAML file
    response = HttpResponse(yaml_content, content_type='application/x-yaml')
    response['Content-Disposition'] = 'attachment; filename="workflow_config.yaml"'

    messages.success(request, 'Configuration file downloaded successfully!')
    return response


@login_required
@role_confirmed_required
def saved_configs(request):
    """
    View list of saved configurations.
    """
    configs = WorkflowConfiguration.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'configs': configs,
        'title': 'Saved Configurations'
    }
    return render(request, 'analysis_workflows/saved_configs.html', context)


@login_required
@role_confirmed_required
def load_config(request, config_id):
    """
    Load a saved configuration.
    """
    try:
        config = WorkflowConfiguration.objects.get(id=config_id, user=request.user)

        # Store in session
        config_data = {
            'project_name': config.project_name,
            'model_type': config.model_type,
            'aligner': config.aligner,
            'minimap2_preset': config.minimap2_preset,
            'use_gatk': config.use_gatk,
            'use_strelka': config.use_strelka,
            'use_deepvariant': config.use_deepvariant,
            'run_annovar': config.run_annovar,
            'run_vep': config.run_vep,
        }
        request.session['workflow_config'] = config_data

        messages.success(request, f'Configuration "{config.name}" loaded successfully!')
        return redirect('analysis_workflows:preview')

    except WorkflowConfiguration.DoesNotExist:
        messages.error(request, 'Configuration not found.')
        return redirect('analysis_workflows:saved_configs')
