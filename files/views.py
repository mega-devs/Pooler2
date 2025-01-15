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

from files.serializers import ExtractedDataSerializer, UploadedFileSerializer
from .models import UploadedFile, ExtractedData
from .forms import UploadedFileForm, ExtractedDataForm
from .service import determine_origin
from .tasks import async_handle_archive, async_process_uploaded_files
from .service import remove_duplicate_lines, extract_country_from_filename
from random import sample
from django.http import HttpResponse

from rest_framework import viewsets
from rest_framework.decorators import api_view
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


logger = logging.getLogger(__name__)

# @swagger_auto_schema(
#     methods=['post'],
#     operation_description="Upload a combo file",
#     request_body=openapi.Schema(
#         type=openapi.TYPE_OBJECT,
#         properties={
#             'file': openapi.Schema(type=openapi.TYPE_FILE)
#         }
#     ),
#     responses={200: "File uploaded successfully"}
# )


@api_view(['GET'])
@login_required(login_url='users:login')
def panel_table(request):
    """Display data with pagination or random selection.
    
    Handles filtering by provider, email, and country.
    Supports both random sampling and paginated full data display."""

    query_params = request.GET
    show_all = query_params.get('show_all') == 'true'
    random_count = int(query_params.get('random_count', 10))

    # Data selection
    data = ExtractedData.objects.all()

    # Get unique countries
    countries = list(ExtractedData.objects.values_list('country', flat=True).distinct())

    # Apply filters
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
        # Output random records
        total_count = data.count()
        random_count = min(random_count, total_count)
        random_ids = sample(list(data.values_list('id', flat=True)), random_count)
        data = data.filter(id__in=random_ids)
        data_serialized = ExtractedDataSerializer(data, many=True).data
        response_data = {
            'data': data_serialized,
            'countries': countries,
            'show_all': show_all,
            'random_count': random_count,
            'total_pages': 1
        }
    else:
        # Enable pagination for "Show All"
        paginator = Paginator(data, 10)
        page = query_params.get('page', 1)
        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        data_serialized = ExtractedDataSerializer(page_obj.object_list, many=True).data
        response_data = {
            'data': data_serialized,
            'countries': countries,
            'show_all': show_all,
            'random_count': random_count,
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }

    return JsonResponse(response_data)


# --- Upload Combo File ---
@api_view(['POST'])
@require_POST
def upload_combofile(request):
    """Handles file upload and initiates async processing.

    Validates file presence and format, saves to appropriate directory.
    Triggers background tasks for file processing and data extraction."""

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file part'}, status=400)

    file = request.FILES['file']
    if not file.name:
        return JsonResponse({'error': 'No file selected'}, status=400)

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

        # Async processing
        async_handle_archive.delay(file_path, save_path)
        async_process_uploaded_files.delay(save_path, uploaded_file.id)

        return JsonResponse({
            'message': f"File '{filename}' uploaded successfully!",
            'file_id': uploaded_file.id
        }, status=201)

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
def process_file(request, file_path, file_name, uploaded_file):
    """Extracts data from the unpacked file.
    
    Processes text files to extract email/password combinations and saves to database.
    Handles duplicate removal and data validation."""
    try:
        # Check file format
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type != 'text/plain':
            return JsonResponse({
                'error': f"Unsupported file type: {mime_type}. Only text files are supported."
            }, status=400)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        num_duplicates = remove_duplicate_lines(file_path)
        logger.info(f"Removed {num_duplicates} duplicate lines from {file_name}")

        upload_origin = determine_origin(file_name)
        processed_count = 0

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
                processed_count += 1

        return JsonResponse({
            'message': f"Extracted data from {file_name} successfully saved.",
            'processed_lines': processed_count,
            'duplicates_removed': num_duplicates
        }, status=200)

    except ValueError as ve:
        return JsonResponse({
            'error': f"File processing error: {file_name}: {str(ve)}"
        }, status=400)

    except Exception as e:
        return JsonResponse({
            'error': f"Unexpected error processing file {file_name}: {str(e)}"
        }, status=500)


@api_view(['GET'])
@require_GET
def download_file(request, filename):
    """Serves requested file for download.
    
    Takes a filename parameter and returns the file as a download attachment.
    Raises 404 if file is not found in the combofiles directory."""

    directory = os.path.join(settings.BASE_DIR, "data", "combofiles")
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        return JsonResponse({
            'error': f"File {filename} not found."
        }, status=404)

    try:
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return JsonResponse({
                'message': 'File downloaded successfully',
                'filename': filename,
                'download_url': response.url
            }, status=200)
    except Exception as e:
        return JsonResponse({
            'error': f"Error downloading file: {str(e)}"
        }, status=500)


@api_view(['GET'])
@require_GET
def download_combofile(request, filename):
    """Handles file downloads.
    
    Takes a filename parameter and returns the file as a download attachment.
    Raises 404 if file is not found in the combofiles directory."""

    directory = os.path.join(settings.BASE_DIR, 'data', 'combofiles')
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        return JsonResponse({
            'error': f"File {filename} not found."
        }, status=404)

    try:
        with open(file_path, 'rb') as file:
            response = HttpResponse(file.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return JsonResponse({
                'message': 'File downloaded successfully',
                'filename': filename,
                'download_url': response.url
            }, status=200)
    except Exception as e:
        return JsonResponse({
            'error': f"Error downloading file: {str(e)}"
        }, status=500)
    

@api_view(['GET'])
@login_required
def uploaded_files_list(request):
    """
    Handles file downloads.
    
    Takes a filename parameter and returns the file as a download attachment.
    Raises 404 if file is not found in the combofiles directory.
    """

    user_files = UploadedFile.objects.filter(user=request.user)
    files_data = [{
        'id': file.id,
        'filename': file.filename,
        'file_path': file.file_path,
        'upload_date': file.upload_date,
        'status': file.status
    } for file in user_files]
    
    return JsonResponse({
        'message': 'Files retrieved successfully',
        'files': files_data
    }, status=200)


@api_view(['PUT'])
@login_required
def uploaded_file_update(request, pk):
    """
    Update uploaded file information.
    
    Allows users to modify metadata of their uploaded files.
    Only accessible to authenticated users who own the file.
    """

    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)

    if request.method == 'PUT':
        form = UploadedFileForm(request.data, instance=file_obj)
        if form.is_valid():
            updated_file = form.save()
            return JsonResponse({
                'message': 'File updated successfully',
                'file': {
                    'id': updated_file.id,
                    'filename': updated_file.filename,
                    'file_path': updated_file.file_path,
                    'upload_date': updated_file.upload_date,
                    'status': updated_file.status
                }
            }, status=200)
        return JsonResponse({
            'errors': form.errors
        }, status=400)

    return JsonResponse({
        'error': 'Method not allowed'
    }, status=405)


@api_view(['DELETE'])
@login_required
def uploaded_file_delete(request, pk):
    """
    Delete uploaded file along with database object and unpacked files.

    Handles deletion of the uploaded file, its database record, and any associated unpacked files.
    Ensures proper cleanup of all related data and files from both database and filesystem.
    """

    file_obj = get_object_or_404(UploadedFile, pk=pk, user=request.user)

    if request.method == 'DELETE':
        file_path = file_obj.file_path
        extracted_path = os.path.splitext(file_path)[0]  # Предполагаем, что распакованные файлы находятся в папке с таким же именем

        try:
            with transaction.atomic():
                # Delete related ExtractedData records
                extracted_data_deleted, _ = ExtractedData.objects.filter(uploaded_file=file_obj).delete()
                logger.info(f"Удалено связанных записей: {extracted_data_deleted}")

                # Delete unpacked files and folders
                if os.path.exists(extracted_path):
                    for root, dirs, files in os.walk(extracted_path, topdown=False):
                        for file in files:
                            os.remove(os.path.join(root, file))
                        for dir in dirs:
                            os.rmdir(os.path.join(root, dir))
                    os.rmdir(extracted_path) # Delete the folder itself
                    logger.info(f"Folder {extracted_path} successfully deleted.")
                else:
                    logger.warning(f"Folder {extracted_path} not found.")

                # Delete original file from disk
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"File {file_path} deleted from disk.")
                else:
                    logger.warning(f"File {file_path} not found on disk.")

                # Delete UploadedFile record
                file_obj.delete()
                logger.info(f"Object {file_obj.filename} deleted from database.")

                return JsonResponse({
                    'message': 'File and associated data deleted successfully'
                }, status=200)

        except IntegrityError as e:
            logger.error(f"Error deleting object: {e}")
            return JsonResponse({
                'error': f"Error deleting object: {str(e)}"
            }, status=500)

        except Exception as e:
            logger.error(f"Error deleting file {file_path} or folder {extracted_path}: {e}")
            return JsonResponse({
                'error': f"Error deleting file or folder: {str(e)}"
            }, status=500)

    return JsonResponse({
        'error': 'Method not allowed'
    }, status=405)


@api_view(['GET', 'POST'])
@login_required
def download_txt(request):
    """
    Download data displayed on the current page in TXT format.
    Takes the currently filtered/displayed records from the session
    and generates a downloadable TXT file with the data.
    """

    current_data_ids = request.session.get('current_data_ids', [])

    # Get records visible on the page
    data = ExtractedData.objects.filter(id__in=current_data_ids)

    # Generate file content
    content = []
    for item in data:
        line = {
            "line_number": item.line_number,
            "filename": item.filename,
            "email": item.email,
            "password": item.password,
            "provider": item.provider,
            "country": item.country,
            "upload_origin": item.upload_origin
        }
        content.append(line)
        
    return JsonResponse({
        'status': 'success',
        'data': content,
        'message': 'Data retrieved successfully'
    }, status=200)


@api_view(['GET', 'POST'])
@login_required
def extracted_data_update(request, pk):
    """
    Edit extracted data.
    Allows updating of existing extracted data records through a form.
    Returns JSON response after update attempt.
    """

    data_obj = get_object_or_404(ExtractedData, pk=pk)

    if request.method == 'POST':
        form = ExtractedDataForm(request.POST, instance=data_obj)
        if form.is_valid():
            form.save()
            return JsonResponse({
                'status': 'success',
                'message': 'Data updated successfully'
            }, status=200)
        return JsonResponse({
            'status': 'error',
            'errors': form.errors
        }, status=400)
    else:
        form = ExtractedDataForm(instance=data_obj)
        return JsonResponse({
            'status': 'success',
            'data': {
                'id': data_obj.pk,
                'email': data_obj.email,
                'password': data_obj.password,
                'provider': data_obj.provider,
                'country': data_obj.country,
                'filename': data_obj.filename,
                'line_number': data_obj.line_number,
                'upload_origin': data_obj.upload_origin
            }
        }, status=200)


@api_view(['GET', 'POST'])
@login_required
def extracted_data_delete(request, pk):
    """
    Delete extracted data with confirmation.
    Handles both GET requests to show confirmation page and POST requests to perform deletion.
    Removes both database record and associated file from the server.
    """
    
    data_obj = get_object_or_404(ExtractedData, pk=pk)

    if request.method == 'POST':
        file_path = os.path.join(settings.BASE_DIR, 'uploads', data_obj.filename)

        try:
            with transaction.atomic():
                # Delete file from server
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"File {file_path} successfully deleted from server.")
                else:
                    logger.warning(f"File {file_path} not found on server.")

                # Delete record from database
                data_obj.delete()
                logger.info(f"Object {data_obj.email} deleted from database.")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Data deleted successfully'
                }, status=200)

        except Exception as e:
            logger.error(f"Error while deleting {data_obj.email}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f"Error deleting object: {e}"
            }, status=500)

    # Return data object details on GET request
    return JsonResponse({
        'status': 'success',
        'data': {
            'id': data_obj.pk,
            'email': data_obj.email,
            'filename': data_obj.filename
        },
        'message': 'Confirm deletion of this item'
    }, status=200)


# viewsets for models, Swagger
class ExtractedDataModelViewSet(viewsets.ModelViewSet):
    queryset = ExtractedData.objects.all()
    serializer_class = ExtractedDataSerializer

    @swagger_auto_schema(
        operation_description="""Get list of items.

            This endpoint returns all extracted data items.
            Use this to retrieve the complete collection of extracted data.
            """,
        responses={200: ExtractedDataSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""Create new item.

            This endpoint allows creation of new extracted data items.
            Provide the required data in the request body to create a new entry.""",
        request_body=ExtractedDataSerializer,
        responses={201: ExtractedDataSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    

class UploadedFileModelViewSet(viewsets.ModelViewSet):
    queryset = UploadedFile.objects.all()
    serializer_class = UploadedFileSerializer

    @swagger_auto_schema(
        operation_description="""Get list of items.
            
            This endpoint returns all uploaded file items.
            Use this to retrieve the complete collection of files.""",
        responses={200: UploadedFileSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="""Create new item.
            
            This endpoint allows creation of new uploaded file items.
            Provide the required data in the request body to create a new entry.""",
        request_body=UploadedFileSerializer,
        responses={201: UploadedFileSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
