"""
Cloudinary image upload and management service
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
from typing import List, Optional
from fastapi import UploadFile, HTTPException, status
import re
from urllib.parse import urlparse
import logging

from app.core.config import settings

# Import Cloudinary exceptions
try:
    from cloudinary.exceptions import Error as CloudinaryError
except ImportError:
    # Fallback for older cloudinary versions
    CloudinaryError = Exception

logger = logging.getLogger(__name__)

# Initialize Cloudinary
_cloudinary_initialized = False


def initialize_cloudinary() -> None:
    """Initialize Cloudinary client with settings from config."""
    global _cloudinary_initialized
    
    if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
        logger.warning("Cloudinary credentials not configured. Image uploads will fail.")
        return
    
    try:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=settings.CLOUDINARY_SECURE
        )
        _cloudinary_initialized = True
        logger.info(f"Cloudinary initialized successfully for cloud: {settings.CLOUDINARY_CLOUD_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Cloudinary: {str(e)}")
        _cloudinary_initialized = False
        raise


def _ensure_initialized():
    """Ensure Cloudinary is initialized before operations."""
    global _cloudinary_initialized
    if not _cloudinary_initialized:
        initialize_cloudinary()
    
    if not settings.CLOUDINARY_CLOUD_NAME:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary is not configured. Please set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in environment variables."
        )


def is_cloudinary_url(url: str) -> bool:
    """Check if a URL is from Cloudinary."""
    if not url:
        return False
    try:
        parsed = urlparse(url)
        # Check for cloudinary.com domain or res.cloudinary.com
        return 'cloudinary.com' in parsed.netloc
    except Exception:
        return False


def extract_public_id_from_url(url: str) -> Optional[str]:
    """Extract Cloudinary public_id from a Cloudinary URL."""
    if not is_cloudinary_url(url):
        return None
    
    try:
        # Cloudinary URLs typically look like:
        # https://res.cloudinary.com/{cloud_name}/image/upload/{transformations}/{public_id}.{format}
        # or
        # https://res.cloudinary.com/{cloud_name}/image/upload/{public_id}.{format}
        
        parsed = urlparse(url)
        path = parsed.path
        
        # Remove leading slash
        if path.startswith('/'):
            path = path[1:]
        
        # Split by '/'
        parts = path.split('/')
        
        # Find 'upload' in the path
        try:
            upload_index = parts.index('upload')
            # Everything after 'upload' is the path, but we need to remove transformations
            # Transformations are usually before the filename
            # The public_id is usually the last part before the extension
            
            # Get everything after 'upload'
            after_upload = '/'.join(parts[upload_index + 1:])
            
            # Remove file extension
            public_id = re.sub(r'\.[^.]+$', '', after_upload)
            
            # Remove common transformation patterns (v1234567890, w_500, h_500, etc.)
            # But keep folder structure
            public_id = re.sub(r'/v\d+/', '/', public_id)  # Remove version
            public_id = re.sub(r'/[a-z]_[0-9,]+/', '/', public_id)  # Remove transformations like w_500
            
            return public_id.strip('/')
        except ValueError:
            # 'upload' not found, try to extract from end
            # Assume last part before extension is public_id
            if parts:
                last_part = parts[-1]
                public_id = re.sub(r'\.[^.]+$', '', last_part)
                return public_id
        
        return None
    except Exception as e:
        logger.error(f"Error extracting public_id from URL {url}: {str(e)}")
        return None


def validate_image_file(file: UploadFile) -> None:
    """Validate that the uploaded file is an image."""
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename} has no content type"
        )
    
    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {file.filename} is not a valid image type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Check file extension as well
    if file.filename:
        ext = file.filename.split('.')[-1].lower()
        allowed_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} has invalid extension. Allowed extensions: {', '.join(allowed_extensions)}"
            )


def validate_url(url: str) -> bool:
    """Validate that a URL is a valid HTTP/HTTPS URL."""
    try:
        parsed = urlparse(url)
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except Exception:
        return False


def is_base64_data_url(url: str) -> bool:
    """Check if a string is a base64 data URL."""
    if not url:
        return False
    return url.startswith('data:image/')


def upload_base64_image(
    data_url: str,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
    overwrite: bool = False
) -> str:
    """
    Upload a base64 data URL image to Cloudinary.
    
    Args:
        data_url: Base64 data URL (e.g., 'data:image/png;base64,...')
        folder: Optional folder path in Cloudinary
        public_id: Optional public ID for the image
        overwrite: Whether to overwrite if public_id already exists
    
    Returns:
        Cloudinary URL of the uploaded image
    """
    _ensure_initialized()
    
    if not is_base64_data_url(data_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 data URL format"
        )
    
    # Verify Cloudinary is properly configured
    if not is_cloudinary_configured():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary is not properly configured. Please check your CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET environment variables."
        )
    
    try:
        # Prepare upload options - keep it simple to avoid signature issues
        upload_options = {
            'resource_type': 'image',
        }
        
        if folder:
            upload_options['folder'] = folder
        
        if public_id:
            upload_options['public_id'] = public_id
        
        if overwrite:
            upload_options['overwrite'] = overwrite
        
        # Upload base64 data URL directly - Cloudinary handles it natively
        # Note: fetch_format and quality can be applied via transformations in the URL later
        result = cloudinary.uploader.upload(
            data_url,
            **upload_options
        )
        
        # Return secure URL (HTTPS)
        return result.get('secure_url') or result.get('url')
    
    except CloudinaryError as e:
        error_msg = str(e)
        logger.error(f"Cloudinary upload error for base64 image: {error_msg}")
        
        # Provide more helpful error messages
        if 'Invalid Signature' in error_msg or 'Signature' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cloudinary authentication failed. Please verify your CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET are correct."
            )
        elif 'Unauthorized' in error_msg or '401' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cloudinary authentication failed. Please check your API credentials."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload base64 image to Cloudinary: {error_msg}"
            )
    except Exception as e:
        logger.error(f"Unexpected error uploading base64 image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload base64 image: {str(e)}"
        )


def upload_image(
    file: UploadFile,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
    overwrite: bool = False
) -> str:
    """
    Upload a single image file to Cloudinary.
    
    Args:
        file: FastAPI UploadFile object
        folder: Optional folder path in Cloudinary (e.g., 'products/123')
        public_id: Optional public ID for the image
        overwrite: Whether to overwrite if public_id already exists
    
    Returns:
        Cloudinary URL of the uploaded image
    """
    _ensure_initialized()
    validate_image_file(file)
    
    try:
        # Read file content
        file_content = file.file.read()
        file.file.seek(0)  # Reset file pointer
        
        # Prepare upload options - keep it simple to avoid signature issues
        upload_options = {
            'resource_type': 'image',
        }
        
        if folder:
            upload_options['folder'] = folder
        
        if public_id:
            upload_options['public_id'] = public_id
        
        if overwrite:
            upload_options['overwrite'] = overwrite
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_content,
            **upload_options
        )
        
        # Return secure URL (HTTPS)
        return result.get('secure_url') or result.get('url')
    
    except CloudinaryError as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image to Cloudinary: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


def upload_image_from_url(
    url: str,
    folder: Optional[str] = None,
    public_id: Optional[str] = None,
    overwrite: bool = False
) -> str:
    """
    Upload an image from a URL to Cloudinary.
    
    Args:
        url: URL of the image to upload
        folder: Optional folder path in Cloudinary
        public_id: Optional public ID for the image
        overwrite: Whether to overwrite if public_id already exists
    
    Returns:
        Cloudinary URL of the uploaded image
    """
    _ensure_initialized()
    
    if not validate_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL format: {url}"
        )
    
    # If it's already a Cloudinary URL, return it
    if is_cloudinary_url(url):
        return url
    
    try:
        # Prepare upload options - keep it simple to avoid signature issues
        upload_options = {
            'resource_type': 'image',
        }
        
        if folder:
            upload_options['folder'] = folder
        
        if public_id:
            upload_options['public_id'] = public_id
        
        if overwrite:
            upload_options['overwrite'] = overwrite
        
        # Upload from URL
        result = cloudinary.uploader.upload(
            url,
            **upload_options
        )
        
        # Return secure URL (HTTPS)
        return result.get('secure_url') or result.get('url')
    
    except CloudinaryError as e:
        logger.error(f"Cloudinary upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image from URL to Cloudinary: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error uploading image from URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image from URL: {str(e)}"
        )


def upload_multiple_images(
    files: List[UploadFile],
    folder: Optional[str] = None
) -> List[str]:
    """
    Upload multiple image files to Cloudinary.
    
    Args:
        files: List of FastAPI UploadFile objects
        folder: Optional folder path in Cloudinary
    
    Returns:
        List of Cloudinary URLs
    """
    urls = []
    errors = []
    
    for file in files:
        try:
            url = upload_image(file, folder=folder)
            urls.append(url)
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            logger.error(f"Failed to upload {file.filename}: {str(e)}")
    
    if errors and not urls:
        # All uploads failed
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"All image uploads failed: {'; '.join(errors)}"
        )
    
    if errors:
        # Some uploads failed, but some succeeded
        logger.warning(f"Some image uploads failed: {'; '.join(errors)}")
    
    return urls


def delete_image(public_id: str) -> bool:
    """
    Delete a single image from Cloudinary.
    
    Args:
        public_id: Cloudinary public_id of the image to delete
    
    Returns:
        True if deletion was successful
    """
    _ensure_initialized()
    
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type='image')
        return result.get('result') == 'ok'
    except CloudinaryError as e:
        logger.error(f"Cloudinary delete error for {public_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting image {public_id}: {str(e)}")
        return False


def delete_images(public_ids: List[str]) -> dict:
    """
    Delete multiple images from Cloudinary.
    
    Args:
        public_ids: List of Cloudinary public_ids to delete
    
    Returns:
        Dictionary with 'success' and 'failed' lists
    """
    results = {'success': [], 'failed': []}
    
    for public_id in public_ids:
        if delete_image(public_id):
            results['success'].append(public_id)
        else:
            results['failed'].append(public_id)
    
    return results


def delete_image_by_url(url: str) -> bool:
    """
    Delete an image from Cloudinary using its URL.
    
    Args:
        url: Cloudinary URL of the image to delete
    
    Returns:
        True if deletion was successful
    """
    if not is_cloudinary_url(url):
        logger.warning(f"URL is not a Cloudinary URL: {url}")
        return False
    
    public_id = extract_public_id_from_url(url)
    if not public_id:
        logger.warning(f"Could not extract public_id from URL: {url}")
        return False
    
    return delete_image(public_id)


def is_cloudinary_configured() -> bool:
    """Check if Cloudinary is properly configured."""
    return bool(
        settings.CLOUDINARY_CLOUD_NAME and 
        settings.CLOUDINARY_API_KEY and 
        settings.CLOUDINARY_API_SECRET
    )


def process_image(image_input: str, folder: Optional[str] = None) -> Optional[str]:
    """
    Process a single image input (URL, base64 data URL, or Cloudinary URL).
    Uploads non-Cloudinary images to Cloudinary and returns Cloudinary URL.
    
    Args:
        image_input: Image URL, base64 data URL, or Cloudinary URL
        folder: Optional folder path in Cloudinary
    
    Returns:
        Cloudinary URL or None if processing failed
    
    Raises:
        ValueError: If Cloudinary is not configured and image needs to be uploaded
    """
    if not image_input:
        return None
    
    # If already a Cloudinary URL, keep it
    if is_cloudinary_url(image_input):
        return image_input
    
    # Check if Cloudinary is configured before attempting upload
    if not is_cloudinary_configured():
        # If it's a base64 data URL, we MUST have Cloudinary configured
        if is_base64_data_url(image_input):
            raise ValueError(
                "Cloudinary is not configured. Please set CLOUDINARY_CLOUD_NAME, "
                "CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in your .env file. "
                "Base64 images cannot be stored directly in the database."
            )
        # For regular URLs, we can store them as-is if Cloudinary is not configured
        if validate_url(image_input):
            logger.warning("Cloudinary not configured, storing URL as-is")
            return image_input
        # Invalid format
        logger.warning(f"Invalid image format: {image_input[:100]}...")
        return None
    
    # If it's a base64 data URL, upload it
    if is_base64_data_url(image_input):
        try:
            return upload_base64_image(image_input, folder=folder)
        except HTTPException as e:
            # Re-raise HTTP exceptions (they have proper error messages)
            raise ValueError(f"Failed to upload base64 image to Cloudinary: {e.detail}")
        except Exception as e:
            logger.error(f"Failed to upload base64 image: {str(e)}")
            raise ValueError(f"Failed to upload base64 image to Cloudinary: {str(e)}")
    
    # If it's a valid HTTP/HTTPS URL, upload it
    if validate_url(image_input):
        try:
            return upload_image_from_url(image_input, folder=folder)
        except HTTPException as e:
            # Re-raise HTTP exceptions (they have proper error messages)
            raise ValueError(f"Failed to upload image from URL: {e.detail}")
        except Exception as e:
            logger.error(f"Failed to upload image from URL {image_input}: {str(e)}")
            return None
    
    # Invalid format
    logger.warning(f"Invalid image format: {image_input[:100]}...")
    return None


def process_images(
    images: Optional[List[str]],
    folder: Optional[str] = None
) -> List[str]:
    """
    Process a list of image inputs (URLs, base64 data URLs, or Cloudinary URLs).
    Uploads non-Cloudinary images to Cloudinary and returns Cloudinary URLs.
    
    Args:
        images: List of image URLs, base64 data URLs, or Cloudinary URLs
        folder: Optional folder path in Cloudinary
    
    Returns:
        List of Cloudinary URLs
    """
    if not images:
        return []
    
    processed_urls = []
    
    for image_input in images:
        if not image_input:
            continue
        
        processed_url = process_image(image_input, folder=folder)
        if processed_url:
            processed_urls.append(processed_url)
    
    return processed_urls
