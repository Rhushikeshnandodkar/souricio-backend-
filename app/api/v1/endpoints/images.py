"""
Image upload API endpoints
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.cloudinary_service import upload_multiple_images
from app.dependencies import get_current_user
from app.db.models.user import User, UserRole

router = APIRouter()


class ImageUploadResponse(BaseModel):
    """Response model for image upload"""
    urls: List[str]
    count: int


@router.post("/upload", response_model=ImageUploadResponse, tags=["Images"])
async def upload_images(
    files: List[UploadFile] = File(...),
    folder: Optional[str] = Query(None, description="Optional folder path in Cloudinary (e.g., 'products/123')"),
    current_user: User = Depends(get_current_user)
) -> ImageUploadResponse:
    """
    Upload one or more images to Cloudinary.
    
    Requires authentication. Only OWNER role can upload images.
    
    - **files**: List of image files to upload (multipart/form-data)
    - **folder**: Optional folder path in Cloudinary for organization
    
    Returns list of Cloudinary URLs for the uploaded images.
    """
    # Check if user has permission (only owners can upload)
    if current_user.role != UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only product owners are allowed to upload images"
        )
    
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )
    
    try:
        urls = upload_multiple_images(files, folder=folder)
        return ImageUploadResponse(urls=urls, count=len(urls))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading images: {str(e)}"
        )
