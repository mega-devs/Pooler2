from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Proxy
from .serializers import ProxySerizalizer, TextFileUploadSerializer


class ProxyViewSet(ModelViewSet):
    queryset = Proxy.objects.all()
    serializer_class = ProxySerizalizer
    pagination_class = PageNumberPagination

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_proxies(self, request):
        serializer = TextFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            try:
                for line in file:
                    line = line.decode('utf-8').strip()
                    if line:
                        host, port = line.split(':')
                        Proxy.objects.create(host=host, port=int(port))
                return Response({"message": "Proxies uploaded successfully!"}, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
