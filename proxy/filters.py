from django_filters import rest_framework as filters

from proxy.models import Proxy


class ProxyFilter(filters.FilterSet):
    max_timeout = filters.NumberFilter(field_name='timeout', lookup_expr='lte')
    country = filters.BaseInFilter(field_name='country', lookup_expr='in')
    reverse = filters.BooleanFilter(method='filter_reverse', label='Reverse order')

    class Meta:
        model = Proxy
        fields = ['max_timeout', 'country', 'reverse']

    def filter_reverse(self, queryset, name, value):
        if value:
            return queryset.order_by('-id')
        return queryset
