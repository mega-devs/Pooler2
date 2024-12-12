import logging
import os
import mimetypes
import re
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, IntegrityError
from .models import UploadedFile, ExtractedData
from .forms import UploadedFileForm, ExtractedDataForm
from .service import determine_origin
from .tasks import async_handle_archive, async_process_uploaded_files
from pooler.views import remove_duplicate_lines
from pooler.utils import extract_country_from_filename
from random import sample
from django.http import HttpResponse


logger = logging.getLogger(__name__)


# --- Панель управления ---
@login_required(login_url='users:login')
def panel_table(request):
    """Отображение данных с пагинацией или случайным выбором."""
    query_params = request.GET
    show_all = query_params.get('show_all') == 'true'
    random_count = int(query_params.get('random_count', 10))

    # Выбор данных
    data = ExtractedData.objects.all()

    # Получение уникальных стран
    countries = ExtractedData.objects.values_list('country', flat=True).distinct()

    # Применение фильтров
    provider_filter = query_params.get('provider')
    email_filter = query_params.get('email')
    country_filter = query_params.get('country')

    if provider_filter:
        data = data.filter(provider__icontains=provider_filter)
    if email_filter:
        data = data.filter(email__icontains=email_filter)
    if country_filter:
        data = data.filter(country__icontains=country_filter)

    if not show_all:
        # Выводим случайные записи
        total_count = data.count()
        random_count = min(random_count, total_count)
        random_ids = sample(list(data.values_list('id', flat=True)), random_count)
        data = data.filter(id__in=random_ids)
        paginator = None
        current_data_ids = list(data.values_list('id', flat=True))  # IDs случайных записей
    else:
        # Включаем пагинацию при "Show All"
        paginator = Paginator(data, 10)
        page = query_params.get('page', 1)
        try:
            data = paginator.page(page)
        except PageNotAnInteger:
            data = paginator.page(1)
        except EmptyPage:
            data = paginator.page(paginator.num_pages)

        current_data_ids = list(data.object_list.values_list('id', flat=True))  # IDs записей текущей страницы

    # Сохраняем IDs текущих записей в сессии
    request.session['current_data_ids'] = current_data_ids

    return render(request, 'tables.html', {
        'active_page': "tables",
        'data': data,
        'countries': countries,
        'show_all': show_all,
        'random_count': random_count,
        'paginator': paginator,
        'query_params': query_params,
    })


# --- Загрузка файла ---
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
        os.makedirs(save_path, exist_ok=True)
        file_path = os.path.join(save_path, filename)
        fs = FileSystemStorage(location=save_path)
        fs.save(filename, file)

        uploaded_file = UploadedFile.objects.create(
            filename=filename,
            file_path=file_path,
            country=category,
            origin=origin,
            user=request.user
        )

        # Асинхронная обработка
        async_handle_archive.delay(file_path, save_path)
        async_process_uploaded_files.delay(save_path, uploaded_file.id)

        return HttpResponseRedirect(f"{reverse('pooler:panel')}?success=File '{filename}' uploaded successfully!")

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JsonResponse({'status': 500, 'error': str(e)})


# --- Обработка файлов ---
def process_file(file_path, file_name, uploaded_file):
    """Извлекает данные из распакованного файла."""
    try:
        # Проверка формата файла
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type != 'text/plain':
            raise ValueError(f"Unsupported file type: {mime_type}. Only text files are supported.")

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        num_duplicates = remove_duplicate_lines(file_path)
        logger.info(f"Removed {num_duplicates} duplicate lines from {file_name}")

        upload_origin = determine_origin(file_name)

        for line in lines:
            match = re.match(r"([^@]+@[^:]+):(.+)", line.strip())
            if match:
                email, password = match.groups()
                provider = email.split('@')[1].split('.')[0].upper()
                country = extract_country_from_filename(file_name)

                ExtractedData.objects.create(
                    email=email,
                    password=password,
                    provider=provider,
                    country=country,
                    filename=file_name,
                    uploaded_file=uploaded_file,
                    upload_origin=upload_origin
                )

        logger.info(f"Extracted data from {file_name} successfully saved.")

    except ValueError as ve:
        logger.error(f"File processing error: {file_name}: {ve}")

    except Exception as e:
        logger.error(f"Unexpected error processing file {file_name}: {e}")


# --- Загрузка файлов ---
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


# --- Управление файлами ---
@login_required
def uploaded_files_list(request):
    """Просмотр списка загруженных файлов."""
    user_files = UploadedFile.objects.filter(user=request.user)
    return render(request, 'uploaded_files_list.html', {'uploaded_files': user_files})


@login_required
def uploaded_file_update(request, pk):
    """Обновление информации о загруженном файле."""
    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)

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
    """Удаление загруженного файла вместе с объектом базы данных и распакованными файлами."""
    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)

    if request.method == 'POST':
        file_path = file_obj.file_path
        extracted_path = os.path.splitext(file_path)[0]  # Предполагаем, что распакованные файлы находятся в папке с таким же именем

        try:
            with transaction.atomic():
                # Удаляем связанные записи ExtractedData
                extracted_data_deleted, _ = ExtractedData.objects.filter(uploaded_file=file_obj).delete()
                logger.info(f"Удалено связанных записей: {extracted_data_deleted}")

                # Удаляем распакованные файлы и папки
                if os.path.exists(extracted_path):
                    for root, dirs, files in os.walk(extracted_path, topdown=False):
                        for file in files:
                            os.remove(os.path.join(root, file))
                        for dir in dirs:
                            os.rmdir(os.path.join(root, dir))
                    os.rmdir(extracted_path)  # Удаляем саму папку
                    logger.info(f"Папка {extracted_path} успешно удалена.")
                else:
                    logger.warning(f"Папка {extracted_path} не найдена.")

                # Удаляем оригинальный файл с диска
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Файл {file_path} удален с диска.")
                else:
                    logger.warning(f"Файл {file_path} не найден на диске.")

                # Удаляем запись UploadedFile
                file_obj.delete()
                logger.info(f"Объект {file_obj.filename} удален из базы данных.")

                return redirect('files:uploaded_files_list')

        except IntegrityError as e:
            logger.error(f"Ошибка удаления объекта: {e}")
            return render(request, 'uploaded_file_confirm_delete.html', {
                'file': file_obj,
                'error': f"Ошибка удаления объекта: {e}"
            })

        except Exception as e:
            logger.error(f"Ошибка удаления файла {file_path} или папки {extracted_path}: {e}")
            return render(request, 'uploaded_file_confirm_delete.html', {
                'file': file_obj,
                'error': f"Ошибка удаления файла или папки: {e}"
            })

    return render(request, 'uploaded_file_confirm_delete.html', {'file': file_obj})


################################ Работа с загруженными и распакованными данными
@login_required
def download_txt(request):
    """Скачивание данных, отображаемых на текущей странице, в формате TXT."""
    current_data_ids = request.session.get('current_data_ids', [])

    # Получение записей, видимых на странице
    data = ExtractedData.objects.filter(id__in=current_data_ids)

    # Создание TXT файла
    response = HttpResponse(content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="extracted_data.txt"'

    for item in data:
        line = f"Filename: {item.filename} | Email: {item.email} | Password: {item.password} | Provider: {item.provider} | Country: {item.country} | Upload Origin: {item.upload_origin}\n"
        response.write(line)

    return response



@login_required
def extracted_data_update(request, pk):
    """Редактирование распакованных данных"""
    data_obj = get_object_or_404(ExtractedData, pk=pk)

    if request.method == 'POST':
        form = ExtractedDataForm(request.POST, instance=data_obj)
        if form.is_valid():
            form.save()
            return redirect('files:panel_table')
    else:
        form = ExtractedDataForm(instance=data_obj)

    return render(request, 'extracted_data_form.html', {'form': form, 'data': data_obj})


@login_required
def extracted_data_delete(request, pk):
    """Удаление распакованных данных с подтверждением"""
    data_obj = get_object_or_404(ExtractedData, pk=pk)

    if request.method == 'POST':
        file_path = os.path.join(settings.BASE_DIR, 'uploads', data_obj.filename)

        try:
            with transaction.atomic():
                # Удаляем файл с сервера
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Файл {file_path} успешно удален с сервера.")
                else:
                    logger.warning(f"Файл {file_path} не найден на сервере.")

                # Удаляем запись из базы данных
                data_obj.delete()
                logger.info(f"Объект {data_obj.email} удален из базы данных.")
                return redirect('files:panel_table')

        except Exception as e:
            logger.error(f"Ошибка при удалении {data_obj.email}: {e}")
            return render(request, 'extracted_data_confirm_delete.html', {
                'data': data_obj,
                'error': f"Ошибка удаления объекта: {e}"
            })

    # Отображаем страницу подтверждения удаления при GET-запросе
    return render(request, 'extracted_data_confirm_delete.html', {'data': data_obj})
