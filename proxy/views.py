from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import action, api_view
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Proxy
from .serializers import ProxySerizalizer, TextFileUploadSerializer
from .tasks import check_proxy_health
from .utils import check_single_proxy

from root.celery import app


class ProxyViewSet(ModelViewSet):
    queryset = Proxy.objects.all()
    serializer_class = ProxySerizalizer
    pagination_class = PageNumberPagination

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        proxy = check_single_proxy(instance)
        serializer = self.get_serializer(proxy)
        return Response(serializer.data)

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
                        parts = line.split(':')

                        if len(parts) == 2:
                            host, port = parts
                            username = None
                            password = None
                        elif len(parts) == 4:
                            host, port, username, password = parts
                        else:
                            errors.append(f"Invalid proxy format: {line}")
                            continue

                        proxy_key = f"{host}:{port}"

                        if proxy_key in existing_proxies:
                            errors.append(f"Proxy {proxy_key} already exists.")
                        else:
                            Proxy.objects.create(
                                host=host,
                                port=int(port),
                                username=username,
                                password=password
                            )
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
                username = proxy.get('username', None)
                password = proxy.get('password', None)

                if host and port is not None:
                    proxy_key = f"{host}:{port}"

                    if proxy_key in existing_proxies:
                        errors.append(f"Proxy {proxy_key} already exists.")
                    else:
                        Proxy.objects.create(
                            host=host,
                            port=int(port),
                            username=username,
                            password=password
                        )
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


@api_view(['POST'])
def set_backup_delay(request):
    try:
        app.conf.beat_schedule['backup']['schedule'] = timedelta(hours=request.data.get('delay'))
        return Response({'status': 'success'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_backup_delay(request):
    try:
        return Response({'delay': app.conf.beat_schedule['backup']['schedule']}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
