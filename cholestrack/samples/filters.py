# samples/filters.py
import django_filters
from django.db.models import Q
from .models import Patient
from files.models import AnalysisFileLocation


class PatientSampleFilter(django_filters.FilterSet):
    """
    FilterSet for the sample list view.
    Provides filtering capabilities for all visible columns except Files column.
    """

    # Text search filters
    project = django_filters.CharFilter(
        method='filter_project',
        label='Project',
        lookup_expr='icontains'
    )

    batch = django_filters.CharFilter(
        method='filter_batch',
        label='Batch',
        lookup_expr='icontains'
    )

    sample_id = django_filters.CharFilter(
        method='filter_sample_id',
        label='Sample ID',
        lookup_expr='icontains'
    )

    # Choice filters
    data_type = django_filters.ChoiceFilter(
        method='filter_data_type',
        label='Data Type',
        choices=AnalysisFileLocation.DATA_TYPE_CHOICES,
        empty_label='All'
    )

    main_result = django_filters.CharFilter(
        field_name='main_exome_result',
        lookup_expr='icontains',
        label='Main Result'
    )

    analysis_status = django_filters.ChoiceFilter(
        field_name='analysis_status',
        label='Analysis Status',
        choices=Patient.ANALYSIS_STATUS_CHOICES,
        empty_label='All'
    )

    class Meta:
        model = Patient
        fields = []

    def filter_project(self, queryset, name, value):
        """Filter patients by project name from related file locations."""
        if not value:
            return queryset
        return queryset.filter(
            file_locations__project_name__icontains=value,
            file_locations__is_active=True
        ).distinct()

    def filter_batch(self, queryset, name, value):
        """Filter patients by batch ID from related file locations."""
        if not value:
            return queryset
        return queryset.filter(
            file_locations__batch_id__icontains=value,
            file_locations__is_active=True
        ).distinct()

    def filter_sample_id(self, queryset, name, value):
        """Filter patients by sample ID from related file locations."""
        if not value:
            return queryset
        return queryset.filter(
            file_locations__sample_id__icontains=value,
            file_locations__is_active=True
        ).distinct()

    def filter_data_type(self, queryset, name, value):
        """Filter patients by data type from related file locations."""
        if not value:
            return queryset
        return queryset.filter(
            file_locations__data_type=value,
            file_locations__is_active=True
        ).distinct()
