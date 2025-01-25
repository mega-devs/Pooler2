from django_filters import rest_framework as filters

from proxy.models import Proxy


class ProxyFilter(filters.FilterSet):
    max_timeout = filters.NumberFilter(field_name='timeout', lookup_expr='lte')
    country = filters.BaseInFilter(field_name='country', lookup_expr='iexact')

    class Meta:
        model = Proxy
        fields = ['max_timeout', 'country']
