"""
Shipping address business logic
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.shipping_address import ShippingAddress
from app.schemas.shipping import ShippingAddressCreate, ShippingAddressUpdate


def list_shipping_addresses(db: Session, user_id: int) -> List[ShippingAddress]:
    """
    Return all shipping addresses for a user with default addresses first.
    """
    return (
        db.query(ShippingAddress)
        .filter(ShippingAddress.user_id == user_id)
        .order_by(ShippingAddress.is_default.desc(), ShippingAddress.created_at.desc())
        .all()
    )


def _unset_other_defaults(db: Session, user_id: int, exclude_id: Optional[int] = None) -> None:
    query = db.query(ShippingAddress).filter(
        ShippingAddress.user_id == user_id,
        ShippingAddress.is_default.is_(True)
    )
    if exclude_id:
        query = query.filter(ShippingAddress.id != exclude_id)
    query.update({ShippingAddress.is_default: False})


def create_shipping_address(
    db: Session,
    user_id: int,
    payload: ShippingAddressCreate
) -> ShippingAddress:
    """
    Create a new shipping address for a user, ensuring a single default.
    """
    existing_addresses = db.query(ShippingAddress).filter(ShippingAddress.user_id == user_id).all()
    should_be_default = payload.is_default or len(existing_addresses) == 0

    if should_be_default:
        _unset_other_defaults(db, user_id)

    address = ShippingAddress(
        user_id=user_id,
        **payload.model_dump(exclude={"is_default"}),
        is_default=should_be_default,
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def update_shipping_address(
    db: Session,
    user_id: int,
    address_id: int,
    payload: ShippingAddressUpdate
) -> ShippingAddress:
    """
    Update a user's shipping address. Ensures ownership and single default.
    """
    address = (
        db.query(ShippingAddress)
        .filter(
            ShippingAddress.id == address_id,
            ShippingAddress.user_id == user_id
        )
        .first()
    )
    if not address:
        raise ValueError("Shipping address not found")

    update_data = payload.model_dump(exclude_none=True)

    if not update_data:
        raise ValueError("No fields provided to update")

    make_default = update_data.get("is_default")
    unset_default = update_data.get("is_default") is False

    if make_default:
        _unset_other_defaults(db, user_id, exclude_id=address_id)

    if unset_default and address.is_default:
        other_default = (
            db.query(ShippingAddress)
            .filter(
                ShippingAddress.user_id == user_id,
                ShippingAddress.id != address_id,
                ShippingAddress.is_default.is_(True),
            )
            .first()
        )
        if not other_default:
            raise ValueError("Set another address as default before unsetting this one")

    for field, value in update_data.items():
        setattr(address, field, value)

    db.commit()
    db.refresh(address)
    return address


def delete_shipping_address(db: Session, user_id: int, address_id: int) -> Optional[ShippingAddress]:
    """
    Delete a user's shipping address. If the deleted address was default,
    promote the most recent remaining address as default.
    """
    address = (
        db.query(ShippingAddress)
        .filter(
            ShippingAddress.id == address_id,
            ShippingAddress.user_id == user_id
        )
        .first()
    )
    if not address:
        raise ValueError("Shipping address not found")

    was_default = address.is_default
    db.delete(address)
    db.commit()

    if was_default:
        replacement = (
            db.query(ShippingAddress)
            .filter(ShippingAddress.user_id == user_id)
            .order_by(ShippingAddress.created_at.desc())
            .first()
        )
        if replacement:
            replacement.is_default = True
            db.commit()
            db.refresh(replacement)
            return replacement

    return None

