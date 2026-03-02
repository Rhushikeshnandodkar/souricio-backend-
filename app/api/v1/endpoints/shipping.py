"""
Shipping address endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.db.models.user import User
from app.schemas.response import APIResponse, ErrorDetail, ErrorResponse
from app.schemas.shipping import (
    ShippingAddressCreate,
    ShippingAddressResponse,
    ShippingAddressUpdate,
)
from app.services.shipping_service import (
    create_shipping_address,
    delete_shipping_address,
    list_shipping_addresses,
    update_shipping_address,
)


router = APIRouter()


@router.get("", response_model=APIResponse, status_code=status.HTTP_200_OK)
def get_shipping_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    addresses = list_shipping_addresses(db, current_user.id)
    response_data = [
        ShippingAddressResponse.model_validate(address).model_dump()
        for address in addresses
    ]
    return APIResponse(
        status="success",
        message="Shipping addresses retrieved successfully",
        data=response_data,
    )


@router.post("", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
def create_shipping(
    request: ShippingAddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        address = create_shipping_address(db, user_id=current_user.id, payload=request)
        return APIResponse(
            status="success",
            message="Shipping address created successfully",
            data=ShippingAddressResponse.model_validate(address).model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to create shipping address",
                error=ErrorDetail(code="VALIDATION_ERROR", message=str(exc)),
            ).model_dump(),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Internal server error",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An error occurred while creating the shipping address.",
                ),
            ).model_dump(),
        )


@router.put("/{address_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
@router.patch("/{address_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
def update_shipping(
    address_id: int,
    request: ShippingAddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        address = update_shipping_address(
            db, user_id=current_user.id, address_id=address_id, payload=request
        )
        return APIResponse(
            status="success",
            message="Shipping address updated successfully",
            data=ShippingAddressResponse.model_validate(address).model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                status="error",
                message="Failed to update shipping address",
                error=ErrorDetail(code="VALIDATION_ERROR", message=str(exc)),
            ).model_dump(),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Internal server error",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An error occurred while updating the shipping address.",
                ),
            ).model_dump(),
        )


@router.delete("/{address_id}", response_model=APIResponse, status_code=status.HTTP_200_OK)
def delete_shipping(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        replacement = delete_shipping_address(
            db, user_id=current_user.id, address_id=address_id
        )
        return APIResponse(
            status="success",
            message="Shipping address deleted successfully",
            data={
                "default_address_id": replacement.id if replacement else None,
            },
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                status="error",
                message="Shipping address not found",
                error=ErrorDetail(code="NOT_FOUND", message=str(exc)),
            ).model_dump(),
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                status="error",
                message="Internal server error",
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An error occurred while deleting the shipping address.",
                ),
            ).model_dump(),
        )

