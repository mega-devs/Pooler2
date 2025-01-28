from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from proxy.serializers import TextFileUploadSerializer

from .tasks import check_imap
from .models import ImapConfig, Combo, IMAPCheckResult, Statistics
from .serializers import ImapConfigSerializer, ComboSerializer, IMAPCheckResultSerializer, StatisticsSerializer


class ImapConfigViewSet(viewsets.ModelViewSet):
    serializer_class = ImapConfigSerializer
    permission_classes = [IsAuthenticated]
    queryset = ImapConfig.objects.none()

    def get_queryset(self):
        return ImapConfig.objects.filter(user=self.request.user)


class ComboViewSet(viewsets.ModelViewSet):
    serializer_class = ComboSerializer
    permission_classes = [IsAuthenticated]
    queryset = Combo.objects.none()

    def get_queryset(self):
        return Combo.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='upload-combo')
    def upload_combo(self, request):
        serializer = TextFileUploadSerializer(data=request.data)

        if serializer.is_valid():
            file = serializer.validated_data['file']

            try:
                file_content = file.read().decode('utf-8')
                check_imap.delay(self.request.user.id, file_content)
                return Response({"status": "Checking IMAP started"}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IMAPCheckResultViewSet(viewsets.ModelViewSet):
    serializer_class = IMAPCheckResultSerializer
    permission_classes = [IsAuthenticated]

    queryset = IMAPCheckResult.objects.none()

    def get_queryset(self):
        return IMAPCheckResult.objects.filter(user=self.request.user)


class StatisticsViewSet(viewsets.ModelViewSet):
    serializer_class = StatisticsSerializer
    permission_classes = [IsAuthenticated]

    queryset = Statistics.objects.none()

    def get_queryset(self):
        return Statistics.objects.filter(user=self.request.user)
