import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, ShippingAddress, User
from app.db.models.user import UserRole
from app.schemas.shipping import ShippingAddressCreate, ShippingAddressUpdate
from app.services.shipping_service import (
    create_shipping_address,
    delete_shipping_address,
    list_shipping_addresses,
    update_shipping_address,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def user(db_session):
    user = User(
        email="user@example.com",
        hashed_password="secret",
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _create_address_payload(name_suffix: str = "") -> ShippingAddressCreate:
    return ShippingAddressCreate(
        name=f"John Doe{name_suffix}",
        phone="9876543210",
        country="India",
        state="KA",
        city="Bangalore",
        address1="123 Main Street",
        address2=None,
        postal_code="560001",
        company=None,
        instructions=None,
        is_default=False,
    )


def test_first_address_becomes_default(db_session, user):
    address = create_shipping_address(db_session, user.id, _create_address_payload())
    assert address.is_default is True


def test_setting_new_default_unsets_previous(db_session, user):
    first = create_shipping_address(db_session, user.id, _create_address_payload(" 1"))
    second_payload = _create_address_payload(" 2")
    second_payload.is_default = True

    second = create_shipping_address(db_session, user.id, second_payload)

    db_session.refresh(first)
    assert second.is_default is True
    assert first.is_default is False


def test_cannot_unset_last_default(db_session, user):
    address = create_shipping_address(db_session, user.id, _create_address_payload())
    with pytest.raises(ValueError):
        update_shipping_address(
            db_session,
            user_id=user.id,
            address_id=address.id,
            payload=ShippingAddressUpdate(is_default=False),
        )


def test_delete_default_promotes_other(db_session, user):
    first = create_shipping_address(db_session, user.id, _create_address_payload(" 1"))
    second = create_shipping_address(db_session, user.id, _create_address_payload(" 2"))

    replacement = delete_shipping_address(db_session, user.id, first.id)
    db_session.refresh(second)

    assert replacement.id == second.id
    assert second.is_default is True


def test_update_requires_ownership(db_session, user):
    address = create_shipping_address(db_session, user.id, _create_address_payload())
    with pytest.raises(ValueError):
        update_shipping_address(
            db_session,
            user_id=999,  # different user
            address_id=address.id,
            payload=ShippingAddressUpdate(city="Mumbai"),
        )

