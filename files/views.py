import asyncio
import os
import mimetypes
import re
from random import sample
import threading
from datetime import datetime
from django.db.models import Count, Q

from django.utils import timezone
from django.db.models import Sum, Count
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from drf_yasg import openapi
from pooler.utils import check_smtp_imap_emails_from_zip, process_smtp_imap_background
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view

from .serializers import ExtractedDataSerializer, UploadedFileSerializer, URLFetcherSerializer
from .models import UploadedFile, ExtractedData, URLFetcher
from .forms import UploadedFileForm, ExtractedDataForm
from .service import determine_origin
from .tasks import async_handle_archive, async_process_uploaded_files
from .service import remove_duplicate_lines, extract_country_from_filename

from rest_framework import viewsets
from rest_framework.decorators import api_view

from drf_yasg.utils import swagger_auto_schema


from root.logger import getLogger

logger = getLogger(__name__)

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


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'show_all',
            openapi.IN_QUERY,
            type=openapi.TYPE_BOOLEAN,
            description="Show all records"
        ),
        openapi.Parameter(
            'random_count',
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Number of random records to return"
        ),
        openapi.Parameter(
            'provider',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter by provider"
        ),
        openapi.Parameter(
            'email',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter by email"
        ),
        openapi.Parameter(
            'country',
            openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            description="Filter by country"
        ),
        openapi.Parameter(
            'page',
            openapi.IN_QUERY,
            type=openapi.TYPE_INTEGER,
            description="Page number for pagination"
        ),
    ],
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'password': openapi.Schema(type=openapi.TYPE_STRING),
                                'provider': openapi.Schema(type=openapi.TYPE_STRING),
                                'country': openapi.Schema(type=openapi.TYPE_STRING),
                                'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                'line_number': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'upload_origin': openapi.Schema(type=openapi.TYPE_STRING),
                                'smtp_is_valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'imap_is_valid': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                            }
                        )
                    ),
                    'countries': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                    'show_all': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    'random_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    'current_page': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                    'total_pages': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                    'has_next': openapi.Schema(type=openapi.TYPE_BOOLEAN, nullable=True),
                    'has_previous': openapi.Schema(type=openapi.TYPE_BOOLEAN, nullable=True),
                }
            )
        )
    }
)
@cache_page(60 * 2)
@api_view(['GET'])
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


@swagger_auto_schema(
    method='post',
    responses={
        201: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'file_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@api_view(['POST'])
@require_POST
def upload_combofile(request):
    """Handles file upload and initiates async processing.

    Validates file presence and format, saves to appropriate directory.
    Triggers background tasks for file processing and data extraction."""

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file part'}, status=400)
    
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'error': 'User is not authenticated'}, status=401)
    
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
            user=user
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


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'filename',
            openapi.IN_PATH,
            description="The name of the file to download",
            type=openapi.TYPE_STRING
        ),
    ],
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'filename': openapi.Schema(type=openapi.TYPE_STRING),
                    'download_url': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
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
    

@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'files': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                'file_path': openapi.Schema(type=openapi.TYPE_STRING),
                                'upload_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    )
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@cache_page(60 * 2)
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


@swagger_auto_schema(
    method='put',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'filename': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Name of the uploaded file"
            ),
            'file_path': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Path to the uploaded file"
            ),
            'upload_date': openapi.Schema(
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_DATETIME,
                description="Date the file was uploaded"
            ),
            'status': openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Status of the uploaded file"
            ),
        },
        required=['filename', 'country', 'is_checked']
    ),
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                    'file': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'filename': openapi.Schema(type=openapi.TYPE_STRING),
                            'file_path': openapi.Schema(type=openapi.TYPE_STRING),
                            'upload_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                            'status': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(
                        type=openapi.TYPE_STRING
                    )
                }
            )
        ),
        405: openapi.Response(
            'Method Not Allowed',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(
                        type=openapi.TYPE_STRING
                    )
                }
            )
        ),
    }
)
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


@swagger_auto_schema(
    method='delete',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        405: openapi.Response(
            'Method Not Allowed',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
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


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'line_number': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'filename': openapi.Schema(type=openapi.TYPE_STRING),
                                'email': openapi.Schema(type=openapi.TYPE_STRING),
                                'password': openapi.Schema(type=openapi.TYPE_STRING),
                                'provider': openapi.Schema(type=openapi.TYPE_STRING),
                                'country': openapi.Schema(type=openapi.TYPE_STRING),
                                'upload_origin': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        )
                    ),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    }
)
@cache_page(60 * 2)
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


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'password': openapi.Schema(type=openapi.TYPE_STRING),
                            'provider': openapi.Schema(type=openapi.TYPE_STRING),
                            'country': openapi.Schema(type=openapi.TYPE_STRING),
                            'filename': openapi.Schema(type=openapi.TYPE_STRING),
                            'line_number': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'upload_origin': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    )
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'email': openapi.Schema(type=openapi.TYPE_STRING),
            'password': openapi.Schema(type=openapi.TYPE_STRING),
            'provider': openapi.Schema(type=openapi.TYPE_STRING),
            'country': openapi.Schema(type=openapi.TYPE_STRING),
            'filename': openapi.Schema(type=openapi.TYPE_STRING),
            'line_number': openapi.Schema(type=openapi.TYPE_INTEGER),
            'upload_origin': openapi.Schema(type=openapi.TYPE_STRING),
        },
    ),
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        400: openapi.Response(
            'Bad Request',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(
                        type=openapi.TYPE_STRING
                    ),
                    'errors': openapi.Schema(
                        type=openapi.TYPE_OBJECT)
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
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


@swagger_auto_schema(
    method='get',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'data': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'email': openapi.Schema(type=openapi.TYPE_STRING),
                            'filename': openapi.Schema(type=openapi.TYPE_STRING),
                        }
                    ),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(type=openapi.TYPE_STRING),
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'status': openapi.Schema(
                        type=openapi.TYPE_STRING
                    ),
                    'message': openapi.Schema(
                        type=openapi.TYPE_STRING
                    )
                }
            )
        ),
    }
)
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
    @method_decorator(cache_page(60 * 2))
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
    @method_decorator(cache_page(60 * 2))
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

@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def uploaded_files_data(request):
    """
    Get uploaded files data with filtering options.    
    """

    queryset = UploadedFile.objects.all()
    
    origin = request.query_params.get('origin')
    country = request.query_params.get('country')
    checked = request.query_params.get('checked')
    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')

    if origin:
        queryset = queryset.filter(origin=origin)
    if country:
        queryset = queryset.filter(country=country)
    if checked is not None:
        queryset = queryset.filter(is_checked=checked.lower() == 'true')
    if date_from:
        queryset = queryset.filter(upload_date__gte=date_from)
    if date_to:
        queryset = queryset.filter(upload_date__lte=date_to)

    stats = {
        'total_files': queryset.count(),
        'total_duplicates': queryset.aggregate(Sum('duplicate_count'))['duplicate_count__sum'] or 0,
        'origins_breakdown': dict(queryset.values_list('origin').annotate(count=Count('id'))),
        'files': list(queryset.values(
            'id',
            'filename',
            'file_path',
            'upload_date',
            'country',
            'duplicate_count',
            'origin',
            'is_checked',
            'user_id'
        ))
    }
    
    return JsonResponse({
        'statistics': stats,
    })


@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            'Success',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        ),
        404: openapi.Response(
            'Not Found',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
        500: openapi.Response(
            'Error',
            openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING)
                }
            )
        ),
    }
)
@api_view(['POST'])
@require_POST
def process_uploaded_file(request, pk):
    """
    Return an immediate 200 response, then run extra logic in a background thread.
    """
    file_obj = get_object_or_404(UploadedFile, pk=pk)
    file_path = file_obj.file_path
    
    response = JsonResponse({
        'message': f"File '{file_obj.filename}' found. Background process starting..."
    }, status=200)
    
    def run_after_response():
        print(f"Background thread started for file with id {pk} at path {file_path}")        
        process_smtp_imap_background(file_path)
        print(f"Completed background process for file: {file_path}")

    thread = threading.Thread(target=run_after_response, daemon=True)
    thread.start()

    return response


class URLFetcherAPIView(ModelViewSet):
    queryset = URLFetcher.objects.all()
    serializer_class = URLFetcherSerializer



@api_view(['GET'])
def file_details(request, pk):
    """
    Retrieve file details for a single UploadedFile instance.
    Returns a JSON response including file name, size, user, date, type, and total rows.
    """
    file_obj = get_object_or_404(UploadedFile, pk=pk)
    
    if not file_obj.file_size:
        try:
            file_obj.file_size = file_obj.file.size
            file_obj.save()
            logger.info(f"File size updated for file {file_obj.filename}: {file_obj.file_size}")
        except Exception as e:
            file_obj.file_size = 'N/A'
            logger.error(f"Could not determine file size for {file_obj.filename}: {e}")
    
    if not file_obj.file_type:
        try:
            file_extension = file_obj.filename.split('.')[-1].lower()
            file_obj.file_type = file_extension
            file_obj.save()
            logger.info(f"File type updated for file {file_obj.filename}: {file_obj.file_type}")
        except Exception as e:
            file_obj.file_type = 'N/A'
            logger.error(f"Could not determine file type for {file_obj.filename}: {e}")
    
    if not file_obj.total_rows_in_file:
        try:
            with open(file_obj.file_path, 'r') as f:
                file_obj.total_rows_in_file = sum(1 for line in f)
            file_obj.save()
            logger.info(f"Total rows updated for file {file_obj.filename}: {file_obj.total_rows_in_file}")
        except Exception as e:
            file_obj.total_rows_in_file = 0
            logger.error(f"Could not determine total rows for {file_obj.filename}: {e}")

    data = {
        'file_name': file_obj.filename,
        'file_size': file_obj.file_size or 'N/A',
        'uploaded_by': f"{file_obj.user.username} ({'Admin' if file_obj.user.is_superuser else 'User'})",
        'upload_date': file_obj.upload_date.strftime("%Y-%m-%d %H:%M:%S"),
        'file_type': file_obj.file_type or 'N/A',
        'total_rows_in_file': file_obj.total_rows_in_file,
    }
    logger.info(f"File details retrieved for {file_obj.filename}")
    return JsonResponse(data)


@api_view(['GET'])
def processing_summary(request, pk):
    try:
        latest_file = UploadedFile.objects.get(pk=pk)
    except UploadedFile.DoesNotExist:
        return JsonResponse({
            "message": "No files have been uploaded yet."
        }, status=404)

    start_time = latest_file.processing_start_time or latest_file.upload_date
    end_time = latest_file.processing_end_time or timezone.now()
    processing_duration = end_time - start_time

    total_rows_processed = latest_file.total_rows_in_file if latest_file.total_rows_in_file else 0

    valid_entries = ExtractedData.objects.filter(
        uploaded_file=latest_file, 
        smtp_is_valid=True, 
        imap_is_valid=True
    ).count()

    invalid_entries = ExtractedData.objects.filter(
        uploaded_file=latest_file
    ).filter(
        Q(smtp_is_valid=False) | Q(imap_is_valid=False)
    ).count()

    if total_rows_processed == 0:
        processing_status = "❌ Not Started"
    elif valid_entries + invalid_entries == total_rows_processed:
        processing_status = "✅ Completed"
    else:
        processing_status = "⏳ Processing"

    summary = {
        "Start Time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "End Time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
        "Processing Duration": str(processing_duration),
        "Total Rows Processed": total_rows_processed,
        "Valid Entries": valid_entries,
        "Invalid Entries": invalid_entries,
        "Processing Status": processing_status
    }

    return JsonResponse(summary)


@api_view(['GET'])
def error_summary(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    missing_email_count = ExtractedData.objects.filter(email='').count()
    missing_email_examples = ExtractedData.objects.filter(email='').values('line_number', 'email')[:10]

    invalid_email_count = ExtractedData.objects.filter(email__regex=r'^[^@]+@[^@]+\.[^@]+$').count()
    invalid_email_examples = ExtractedData.objects.filter(email__regex=r'^[^@]+@[^@]+\.[^@]+$').values('line_number', 'email')[:10]

    duplicate_email_count = ExtractedData.objects.values('email').annotate(email_count=Count('email')).filter(email_count__gt=1).count()
    duplicate_email_examples = ExtractedData.objects.values('email').annotate(email_count=Count('email')).filter(email_count__gt=1).values('email', 'line_number', 'email_count')[:10]

    error_summary = {
        "Missing Email Address": {
            "count": missing_email_count,
            "examples": list(missing_email_examples)
        },
        "Invalid Email Format": {
            "count": invalid_email_count,
            "examples": list(invalid_email_examples)
        },
        "Duplicate Records": {
            "count": duplicate_email_count,
            "examples": list(duplicate_email_examples)
        }
    }

    return JsonResponse(error_summary)
