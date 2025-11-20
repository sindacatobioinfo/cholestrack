# Analysis Workflows - Configuration Builder

Django app for building and generating workflow configuration files for WES (Whole Exome Sequencing) analysis pipelines.

## Overview

This app provides a user-friendly interface to configure analysis workflow parameters and generate YAML configuration files for the InterOmics Snakemake pipeline.

## Features

- **Interactive Configuration Builder**: Card-based UI for selecting workflow parameters
- **Aligner Selection**: Choose between BWA-MEM or Minimap2
- **Minimap2 Presets**: Select appropriate preset for different read types (Illumina, Nanopore, PacBio, etc.)
- **Variant Callers**: Enable GATK HaplotypeCaller and/or Strelka2
- **Annotation Tools**: Enable ANNOVAR and/or VEP
- **YAML Generation**: Automatically generates configuration based on template
- **Save Configurations**: Save frequently-used configurations for later reuse
- **Preview & Download**: Preview generated YAML before downloading

## Usage

### Accessing the App

Navigate to `/workflows/` to access the workflow configuration builder.

### Creating a Configuration

1. **Select Alignment Tool**:
   - Click on BWA-MEM or Minimap2 card
   - If Minimap2 is selected, choose the appropriate preset

2. **Select Variant Callers**:
   - Click on GATK HaplotypeCaller and/or Strelka2 cards
   - Multiple callers can be selected

3. **Select Annotation Tools**:
   - Click on ANNOVAR and/or VEP cards
   - Multiple annotation tools can be selected

4. **Optional: Save Configuration**:
   - Enter a name in the "Configuration Name" field to save for later reuse
   - Leave blank for one-time configuration generation

5. **Preview Configuration**:
   - Click "Preview Configuration" button
   - Review the generated YAML file
   - Copy to clipboard or download as file

### Downloading YAML File

From the preview page:
- Click "Download YAML File" to download `workflow_config.yaml`
- Or click "Copy to Clipboard" to copy the YAML content

### Managing Saved Configurations

1. Navigate to "View Saved Configs" from the configuration builder
2. View all your previously saved configurations
3. Click "Load" on any configuration to preview and download

## Technical Details

### Models

**WorkflowConfiguration**:
- Stores user-created workflow configurations
- Fields:
  - `user`: Foreign key to User
  - `name`: Configuration name
  - `aligner`: Choice field (bwa, minimap2)
  - `minimap2_preset`: Choice field for Minimap2 presets
  - `use_gatk`: Boolean for GATK HaplotypeCaller
  - `use_strelka`: Boolean for Strelka2
  - `run_annovar`: Boolean for ANNOVAR
  - `run_vep`: Boolean for VEP

### URL Routes

- `/workflows/` - Configuration builder (main page)
- `/workflows/preview/` - Preview generated YAML
- `/workflows/download/` - Download YAML file
- `/workflows/saved/` - View saved configurations
- `/workflows/load/<id>/` - Load a saved configuration

### YAML Generation

The app uses `config_example.yaml` as a template and replaces the following parameters:
- `aligner`: Selected alignment tool
- `minimap2.preset`: Minimap2 preset (if Minimap2 selected)
- `use_gatk`: GATK HaplotypeCaller enabled/disabled
- `use_strelka`: Strelka2 enabled/disabled
- `run_annovar`: ANNOVAR enabled/disabled
- `run_vep`: VEP enabled/disabled

All other parameters retain their default values from the template.

### Session Storage

Configuration data is temporarily stored in the user's session after form submission, allowing preview and download without requiring a database save.

## Setup Instructions

### 1. Add to INSTALLED_APPS

Already configured in `settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'analysis_workflows',
]
```

### 2. Add to URLs

Already configured in `project/urls.py`:
```python
path('workflows/', include('analysis_workflows.urls')),
```

### 3. Run Migrations

```bash
python manage.py makemigrations analysis_workflows
python manage.py migrate analysis_workflows
```

### 4. Ensure Template File Exists

The app requires `config_example.yaml` to be present in the project root directory.

## Aligner Options

### BWA-MEM
- Default recommended for short Illumina reads
- Widely used and well-tested
- Suitable for WES and WGS

### Minimap2
- Versatile aligner supporting multiple read types
- **Presets**:
  - `sr`: Short reads (Illumina WES/WGS)
  - `map-ont`: Oxford Nanopore reads
  - `map-pb`: PacBio CLR reads
  - `map-hifi`: PacBio HiFi/CCS reads (high accuracy)
  - `asm5`: Assembly-to-reference (≥95% identity)
  - `asm10`: Assembly-to-reference (≥90% identity)
  - `asm20`: Assembly-to-reference (≥80% identity)

## Variant Callers

### GATK HaplotypeCaller
- Industry-standard germline variant caller
- Recommended for most WES/WGS analyses
- GATK Best Practices

### Strelka2
- Fast germline variant caller
- Complementary to GATK
- Can be used together for consensus calling

## Annotation Tools

### ANNOVAR
- Comprehensive variant annotation
- Multiple databases supported
- Includes downstream ETL processing

### VEP (Variant Effect Predictor)
- Ensembl's annotation tool
- Rich functional annotations
- Plugin support

## File Structure

```
analysis_workflows/
├── __init__.py
├── apps.py                 # App configuration
├── models.py               # WorkflowConfiguration model
├── forms.py                # Configuration form
├── views.py                # View logic
├── urls.py                 # URL routing
├── admin.py                # Django admin configuration
├── utils.py                # YAML generation utilities
├── migrations/             # Database migrations
│   ├── __init__.py
│   └── 0001_initial.py
├── templates/
│   └── analysis_workflows/
│       ├── config_builder.html   # Main configuration page
│       ├── preview.html           # YAML preview page
│       └── saved_configs.html    # Saved configurations list
└── README.md
```

## Future Enhancements

Potential features for future versions:
- Support for additional workflow parameters
- Configuration comparison tool
- YAML validation
- Import existing YAML files
- Configuration templates for common use cases
- Export to different workflow formats (CWL, WDL)

## Dependencies

- Django 5.2+
- PyYAML (for YAML parsing/generation)
- User authentication (provided by `users` app)
- Role-based access control (via `@role_confirmed_required`)

## License

Part of the CholesTrack project.
