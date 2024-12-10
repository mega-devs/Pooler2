import logging
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from .models import UploadedFile, ExtractedData
from .service import determine_origin, handle_archive
import mimetypes
from .forms import UploadedFileForm
from pooler.views import remove_duplicate_lines
from pooler.utils import extract_country_from_filename
import re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


logger = logging.getLogger(__name__)


@login_required(login_url='users:login')
def panel_table(request):
    """Отображение данных с пагинацией и фильтрацией."""
    query_params = request.GET

    # Фильтрация по стране, провайдеру и email
    country_filter = query_params.get('country', None)
    provider_filter = query_params.get('provider', None)
    email_filter = query_params.get('email', None)

    # Начальный запрос
    data = ExtractedData.objects.all()

    # Применение фильтров
    if country_filter:
        data = data.filter(country__icontains=country_filter)

    if provider_filter:
        data = data.filter(provider__icontains=provider_filter)

    if email_filter:
        data = data.filter(email__icontains=email_filter)

    # Пагинация
    page = query_params.get('page', 1)
    paginator = Paginator(data, 10)  # 10 записей на странице

    try:
        extracted_data = paginator.page(page)
    except PageNotAnInteger:
        extracted_data = paginator.page(1)
    except EmptyPage:
        extracted_data = paginator.page(paginator.num_pages)

    return render(request, 'tables.html', {
        'active_page': "tables",
        'data': extracted_data,
        'paginator': paginator,
        'query_params': query_params
    })


@require_POST
def upload_combofile(request):
    if 'file' not in request.FILES:
        return JsonResponse({'status': 404, 'error': 'No file part'})

    file = request.FILES['file']
    if not file.name:
        return JsonResponse({'status': 404, 'error': 'No file selected'})

    filename = file.name.replace(" ", "_")
    origin = determine_origin(filename)

    category = "major_providers" if "gmail" in filename.lower() or "yahoo" in filename.lower() else "private_providers"
    save_path = os.path.join(settings.BASE_DIR, 'uploads', category)

    try:
        # Создание директории для сохранения
        os.makedirs(save_path, exist_ok=True)

        file_path = os.path.join(save_path, filename)
        fs = FileSystemStorage(location=save_path)
        fs.save(filename, file)

        mime_type, _ = mimetypes.guess_type(file_path)

        # Обработка архива
        if mime_type == 'application/zip':
            handle_archive(file_path, save_path)
            logger.info(f"Archive '{filename}' extracted to {save_path}")

        if not request.user.is_authenticated:
            return JsonResponse({'status': 403, 'error': 'User is not authenticated.'})

        uploaded_file = UploadedFile.objects.create(
            filename=filename,
            file_path=file_path,
            country=category,
            origin=origin,
            user=request.user
        )

        process_uploaded_files(save_path, uploaded_file)

        return HttpResponseRedirect(f"{reverse('pooler:panel')}?success=File '{filename}' uploaded successfully!")

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JsonResponse({'status': 500, 'error': str(e)})


# --- Обработка Загруженных Файлов ---

def process_uploaded_files(base_upload_dir, uploaded_file):
    """Проходит по всем распакованным директориям и извлекает данные."""
    try:
        for root, dirs, files in os.walk(base_upload_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                process_file(file_path, file_name, uploaded_file)
    except Exception as e:
        logger.error(f"Error processing uploaded files: {e}")


def process_file(file_path, file_name, uploaded_file):
    """Извлекает данные из распакованного файла."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        num_duplicates = remove_duplicate_lines(file_path)
        logger.info(f"Removed {num_duplicates} duplicate lines from {file_name}")

        for line in lines:
            match = re.match(r"([^@]+@[^:]+):(.+)", line.strip())
            if match:
                email = match.group(1)
                password = match.group(2)
                provider = email.split('@')[1].split('.')[0].upper()
                country = extract_country_from_filename(file_name)

                ExtractedData.objects.create(
                    email=email,
                    password=password,
                    provider=provider,
                    country=country,
                    filename=file_name,
                    uploaded_file=uploaded_file
                )

        logger.info(f"Extracted data from {file_name} successfully saved.")

    except Exception as e:
        logger.error(f"Error processing file {file_name}: {e}")



@require_GET
def download_combofile(request, filename):
    directory = os.path.join(settings.BASE_DIR, 'data', 'combofiles')
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        raise Http404(f"File {filename} not found.")

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)



@require_GET
def download_file(request, filename):
    directory = os.path.join(settings.BASE_DIR, "data", "combofiles")
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        raise Http404(f"File {filename} not found.")

    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=filename)


@login_required
def uploaded_files_list(request):
    """Просмотр списка собственных загруженных файлов."""
    user_files = UploadedFile.objects.filter(user=request.user)
    return render(request, 'uploaded_files_list.html', {'uploaded_files': user_files})


@login_required
def uploaded_file_update(request, pk):
    """Обновление информации о загруженном файле."""
    try:
        file_obj = UploadedFile.objects.get(pk=pk, user=request.user)
    except UploadedFile.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'File not found or permission denied.'}, status=403)

    if request.method == 'POST':
        form = UploadedFileForm(request.POST, instance=file_obj)
        if form.is_valid():
            form.save()
            return redirect(reverse('files:uploaded_files_list'))
    else:
        form = UploadedFileForm(instance=file_obj)

    return render(request, 'uploaded_files_form.html', {'form': form, 'file': file_obj})


@login_required
def uploaded_file_delete(request, pk):
    """Удаление загруженного файла."""
    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)
    if request.method == 'POST':
        file_obj.delete()
        return redirect('files:uploaded_files_list')
    return render(request, 'uploaded_file_confirm_delete.html', {'file': file_obj})
