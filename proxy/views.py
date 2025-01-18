from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Proxy
from .serializers import ProxySerizalizer, TextFileUploadSerializer
from .tasks import check_proxy_health


class ProxyViewSet(ModelViewSet):
    queryset = Proxy.objects.all()
    serializer_class = ProxySerizalizer
    pagination_class = PageNumberPagination

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_proxies(self, request):
        serializer = TextFileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            existing_proxies = set()

            for proxy in Proxy.objects.all():
                existing_proxies.add(f"{proxy.host}:{proxy.port}")

            created_proxies = []
            errors = []

            try:
                for line in file:
                    line = line.decode('utf-8').strip()
                    if line:
                        host, port = line.split(':')
                        proxy_key = f"{host}:{port}"

                        if proxy_key in existing_proxies:
                            errors.append(f"Proxy {proxy_key} already exist.")
                        else:
                            Proxy.objects.create(host=host, port=int(port))
                            created_proxies.append(proxy_key)

                check_proxy_health.delay()

                response_data = {
                    "message": "Proxies uploaded successfully!",
                    "created": created_proxies,
                    "errors": errors
                }
                return Response(response_data, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='upload-list')
    def upload_list_proxies(self, request):
        proxies = request.data.get('proxies', [])
        existing_proxies = set(f"{proxy.host}:{proxy.port}" for proxy in Proxy.objects.all())
        created_proxies = []
        errors = []

        try:
            for proxy in proxies:
                host = proxy.get('host')
                port = proxy.get('port')
                if host and port is not None:
                    proxy_key = f"{host}:{port}"

                    if proxy_key in existing_proxies:
                        errors.append(f"Proxy {proxy_key} already exists.")
                    else:
                        Proxy.objects.create(host=host, port=int(port))
                        created_proxies.append(proxy_key)

            check_proxy_health.delay()

            response_data = {
                "message": "Proxies uploaded successfully!",
                "created": created_proxies,
                "errors": errors
            }
            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
