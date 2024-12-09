import logging
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse, FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from .models import UploadedFile
from .service import determine_origin, handle_archive
import mimetypes
from .forms import UploadedFileForm
from pooler.views import remove_duplicate_lines


@require_POST
def upload_combofile(request):
    if 'file' not in request.FILES:
        return JsonResponse({'status': 404, 'error': 'No file part'})

    file = request.FILES['file']
    if not file.name:
        return JsonResponse({'status': 404, 'error': 'No file selected'})

    filename = file.name.replace(" ", "_")  # Получаем имя файла
    origin = determine_origin(filename)  # Определяем происхождение файла

    # Извлекаем страну или категорию файла
    if "gmail" in filename.lower() or "yahoo" in filename.lower():
        category = "major_providers"
    else:
        category = "private_providers"

    save_path = os.path.join(settings.BASE_DIR, 'uploads', category)

    try:
        # Создаём директорию для сохранения файла
        os.makedirs(save_path, exist_ok=True)

        file_path = os.path.join(save_path, filename)
        fs = FileSystemStorage(location=save_path)
        fs.save(filename, file)  # Сохраняем файл

        # Определяем MIME-тип файла
        mime_type, _ = mimetypes.guess_type(file_path)

        # Если файл является архивом, разархивируем его
        if mime_type == 'application/zip':
            handle_archive(file_path, save_path)
            logging.info(f"Archive '{filename}' successfully extracted to {save_path}")

        # Если файл текстовый, удаляем дубликаты строк
        elif mime_type and mime_type.startswith("text"):
            num_duplicates = remove_duplicate_lines(file_path)
            logging.info(f"Removed {num_duplicates} duplicate lines from {filename}")
        else:
            logging.info(f"File '{filename}' is not a text file or archive. Skipping additional processing.")

        # Проверяем, авторизован ли пользователь
        if not request.user.is_authenticated:
            return JsonResponse({'status': 403, 'error': 'User is not authenticated.'})

        # Сохраняем информацию о файле в модели
        uploaded_file = UploadedFile.objects.create(
            filename=filename,
            file_path=file_path,
            country=category,
            duplicate_count=num_duplicates if 'num_duplicates' in locals() else 0,
            origin=origin,
            user=request.user  # Привязываем файл к текущему пользователю
        )

        # Возвращаем на главную страницу с уведомлением
        return HttpResponseRedirect(f"{reverse('pooler:panel')}?success=File '{filename}' uploaded successfully!")

    except Exception as e:
        logging.error(f"Error uploading file: {e}")
        return JsonResponse({'status': 500, 'error': str(e)})


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
            return redirect(reverse('files:uploaded_files_list'))  # Редирект на список файлов
    else:
        form = UploadedFileForm(instance=file_obj)

    return render(request, 'uploaded_files_form.html', {'form': form, 'file': file_obj})


@login_required
def uploaded_file_delete(request, pk):
    """Удаление загруженного файла."""
    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)
    if request.method == 'POST':
        file_obj.delete()
        return redirect('files:uploaded_files_list')  # Редирект на список файлов
    return render(request, 'uploaded_file_confirm_delete.html', {'file': file_obj})
