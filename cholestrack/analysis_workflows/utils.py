# analysis_workflows/utils.py
"""
Utility functions for generating workflow configuration files.
"""

import os
from pathlib import Path
from django.conf import settings


def generate_workflow_yaml(config_data):
    """
    Generate YAML configuration file based on user selections.

    Args:
        config_data: Dictionary containing user selections:
            - aligner: str ('bwa', 'dragmap', or 'minimap2')
            - minimap2_preset: str (if minimap2 selected)
            - use_gatk: bool
            - use_strelka: bool
            - run_annovar: bool
            - run_vep: bool

    Returns:
        str: Complete YAML configuration as string
    """
    # Read the template file
    template_path = Path(settings.BASE_DIR).parent / 'config_example.yaml'

    with open(template_path, 'r') as f:
        yaml_content = f.read()

    # Replace aligner setting
    aligner = config_data.get('aligner', 'bwa')
    yaml_content = replace_yaml_value(yaml_content, 'aligner', aligner)

    # Replace minimap2 preset if minimap2 is selected
    if aligner == 'minimap2':
        minimap2_preset = config_data.get('minimap2_preset', 'sr')
        yaml_content = replace_yaml_value(
            yaml_content,
            'preset',
            minimap2_preset,
            section='minimap2'
        )

    # Replace variant caller settings
    use_gatk = config_data.get('use_gatk', True)
    use_strelka = config_data.get('use_strelka', False)
    yaml_content = replace_yaml_value(yaml_content, 'use_gatk', str(use_gatk))
    yaml_content = replace_yaml_value(yaml_content, 'use_strelka', str(use_strelka))

    # Replace annotation tool settings
    run_annovar = config_data.get('run_annovar', True)
    run_vep = config_data.get('run_vep', False)
    yaml_content = replace_yaml_value(yaml_content, 'run_annovar', str(run_annovar))
    yaml_content = replace_yaml_value(yaml_content, 'run_vep', str(run_vep))

    return yaml_content


def replace_yaml_value(yaml_content, key, value, section=None):
    """
    Replace a value in YAML content.

    Args:
        yaml_content: str, complete YAML content
        key: str, key to replace
        value: str, new value
        section: str, optional section to limit search

    Returns:
        str: Updated YAML content
    """
    lines = yaml_content.split('\n')
    updated_lines = []
    in_section = (section is None)  # If no section specified, search everywhere

    for line in lines:
        # Check if we're entering the target section
        if section and line.strip().startswith(f'{section}:'):
            in_section = True

        # Check if we're leaving the target section (another top-level key)
        elif section and in_section and line and not line[0].isspace() and ':' in line:
            in_section = False

        # Replace the value if we find the key
        if in_section and line.strip().startswith(f'{key}:'):
            indent = len(line) - len(line.lstrip())
            # Preserve comments
            if '#' in line:
                comment_part = line[line.index('#'):]
                updated_line = f'{" " * indent}{key}: {value}  {comment_part}'
            else:
                updated_line = f'{" " * indent}{key}: {value}'
            updated_lines.append(updated_line)
        else:
            updated_lines.append(line)

    return '\n'.join(updated_lines)


def get_config_summary(config_data):
    """
    Generate a human-readable summary of the configuration.

    Args:
        config_data: Dictionary with configuration parameters

    Returns:
        dict: Summary information
    """
    aligner = config_data.get('aligner', 'bwa')

    summary = {
        'aligner': {
            'bwa': 'BWA-MEM',
            'dragmap': 'DRAGEN DRAGMAP',
            'minimap2': 'Minimap2'
        }.get(aligner, aligner),
        'minimap2_preset': None,
        'variant_callers': [],
        'annotation_tools': []
    }

    # Add minimap2 preset if applicable
    if aligner == 'minimap2':
        preset = config_data.get('minimap2_preset', 'sr')
        preset_names = {
            'sr': 'Short reads (Illumina)',
            'map-ont': 'Oxford Nanopore',
            'map-pb': 'PacBio CLR',
            'map-hifi': 'PacBio HiFi/CCS',
            'asm5': 'Assembly-to-ref (e95% identity)',
            'asm10': 'Assembly-to-ref (e90% identity)',
            'asm20': 'Assembly-to-ref (e80% identity)',
        }
        summary['minimap2_preset'] = preset_names.get(preset, preset)

    # Add variant callers
    if config_data.get('use_gatk', True):
        summary['variant_callers'].append('GATK HaplotypeCaller')
    if config_data.get('use_strelka', False):
        summary['variant_callers'].append('Strelka2')

    # Add annotation tools
    if config_data.get('run_annovar', True):
        summary['annotation_tools'].append('ANNOVAR')
    if config_data.get('run_vep', False):
        summary['annotation_tools'].append('VEP')

    return summary
