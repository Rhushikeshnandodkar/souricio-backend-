"""
Authentication service to orchestrate user and OTP management
"""
from typing import Optional
from sqlalchemy.orm import Session
from app.db.models.user import User, UserRole, UserCategory
from app.services.otp_service import create_otp, invalidate_user_otps
from app.services.email_service import send_otp_email
from app.services.password_service import hash_password, verify_password
from datetime import datetime


def get_or_create_user(email: str, db: Session) -> User:
    """
    Get existing user or create a new one.

    Args:
        email: User email address (will be normalized to lowercase)
        db: Database session

    Returns:
        User object
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Try to find existing user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # Create new user
        user = User(
            email=email,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


async def create_user_with_password(
    email: str, 
    password: str, 
    db: Session, 
    role: UserRole = UserRole.USER,
    category: Optional[str] = None,
    gst_number: Optional[str] = None,
    shipping_address1: Optional[str] = None,
    shipping_address2: Optional[str] = None,
    shipping_pin: Optional[str] = None,
    shipping_city: Optional[str] = None,
    shipping_state: Optional[str] = None,
    shipping_country: Optional[str] = None
) -> User:
    """
    Create a new user with password and send OTP for email verification.
    User is created as inactive until email is verified.

    Args:
        email: User email address (will be normalized to lowercase)
        password: Plain text password (will be hashed)
        db: Database session
        role: User role (default: USER)
        category: User category (personal/organization)
        gst_number: GST number (required for organizations)
        shipping_address1: Shipping address line 1
        shipping_address2: Shipping address line 2
        shipping_pin: PIN code
        shipping_city: City
        shipping_state: State
        shipping_country: Country

    Returns:
        User object (inactive until verified)

    Raises:
        ValueError: If user already exists or validation fails
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError(f"User with email {email} already exists")

    # Validate category and GST
    user_category = None
    if category:
        try:
            user_category = UserCategory(category.lower())
        except ValueError:
            raise ValueError(f"Invalid category: {category}. Must be 'personal' or 'organization'")
        
        if user_category == UserCategory.ORGANIZATION and not gst_number:
            raise ValueError("GST number is required for organizations")

    # Hash password
    hashed_password = hash_password(password)

    # Create new user as INACTIVE until email is verified
    user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=False,  # User must verify email before activation
        category=user_category,
        gst_number=gst_number.upper().replace(' ', '').replace('-', '') if gst_number else None,
        shipping_address1=shipping_address1,
        shipping_address2=shipping_address2,
        shipping_pin=shipping_pin.replace(' ', '') if shipping_pin else None,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_country=shipping_country or "India"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Invalidate any existing unused OTPs for this email
    invalidate_user_otps(email, db)

    # Generate and store OTP for email verification
    code = create_otp(email, db)

    # Send OTP via email
    await send_otp_email(email, code)

    return user


def create_active_user_with_password(
    email: str, 
    password: str, 
    db: Session, 
    role: UserRole = UserRole.USER,
    category: Optional[str] = None,
    gst_number: Optional[str] = None,
    shipping_address1: Optional[str] = None,
    shipping_address2: Optional[str] = None,
    shipping_pin: Optional[str] = None,
    shipping_city: Optional[str] = None,
    shipping_state: Optional[str] = None,
    shipping_country: Optional[str] = None
) -> User:
    """
    Create a new user with password and mark as active immediately (no OTP verification required).
    This is used by admin endpoints to create users directly without email verification.

    Args:
        email: User email address (will be normalized to lowercase)
        password: Plain text password (will be hashed)
        db: Database session
        role: User role (default: USER)
        category: User category (personal/organization)
        gst_number: GST number (required for organizations)
        shipping_address1: Shipping address line 1
        shipping_address2: Shipping address line 2
        shipping_pin: PIN code
        shipping_city: City
        shipping_state: State
        shipping_country: Country

    Returns:
        User object (active immediately)

    Raises:
        ValueError: If user already exists or validation fails
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError(f"User with email {email} already exists")

    # Validate category and GST
    user_category = None
    if category:
        try:
            user_category = UserCategory(category.lower())
        except ValueError:
            raise ValueError(f"Invalid category: {category}. Must be 'personal' or 'organization'")
        
        if user_category == UserCategory.ORGANIZATION and not gst_number:
            raise ValueError("GST number is required for organizations")

    # Hash password
    hashed_password = hash_password(password)

    # Create new user as ACTIVE (no email verification required)
    user = User(
        email=email,
        hashed_password=hashed_password,
        role=role,
        is_active=True,  # User is active immediately
        category=user_category,
        gst_number=gst_number.upper().replace(' ', '').replace('-', '') if gst_number else None,
        shipping_address1=shipping_address1,
        shipping_address2=shipping_address2,
        shipping_pin=shipping_pin.replace(' ', '') if shipping_pin else None,
        shipping_city=shipping_city,
        shipping_state=shipping_state,
        shipping_country=shipping_country or "India"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """
    Authenticate user with email and password.

    Args:
        email: User email address
        password: Plain text password
        db: Database session

    Returns:
        User object if authentication successful, None otherwise
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Get user
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not user.is_active:
        return None

    # Check if user has a password set
    if not user.hashed_password:
        return None

    # Verify password
    if not verify_password(password, user.hashed_password):
        return None

    return user


def set_user_password(user: User, new_password: str, db: Session) -> None:
    """
    Set or update user password.

    Args:
        user: User object
        new_password: Plain text new password
        db: Database session
    """
    user.hashed_password = hash_password(new_password)
    db.commit()
    db.refresh(user)


def verify_user_password(user: User, password: str) -> bool:
    """
    Verify user's current password.

    Args:
        user: User object
        password: Plain text password to verify

    Returns:
        True if password matches, False otherwise
    """
    if not user.hashed_password:
        return False

    return verify_password(password, user.hashed_password)


def get_user_by_email(email: str, db: Session) -> Optional[User]:
    """
    Get existing user by email (does not create user).

    Args:
        email: User email address (will be normalized to lowercase)
        db: Database session

    Returns:
        User object if found, None otherwise
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Find existing user
    user = db.query(User).filter(User.email == email).first()
    return user


async def initiate_login(email: str, db: Session) -> bool:
    """
    Initiate login process by generating OTP and sending email.
    Only works for existing users - does not create new users.

    Args:
        email: User email address
        db: Database session

    Returns:
        True if OTP was generated and email sent successfully

    Raises:
        ValueError: If user does not exist
    """
    # Get existing user (do not create)
    user = get_user_by_email(email, db)

    if not user:
        raise ValueError(
            f"User with email {email} does not exist. Please sign up first.")

    if not user.is_active:
        raise ValueError("User account is inactive")

    # Invalidate any existing unused OTPs for this user
    invalidate_user_otps(email, db)

    # Generate and store new OTP
    code = create_otp(email, db)

    # Send OTP via email
    email_sent = await send_otp_email(email, code)

    return email_sent


def update_user_last_login(user: User, db: Session) -> None:
    """
    Update user's last login timestamp.

    Args:
        user: User object
        db: Database session
    """
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)


def update_user_role(email: str, role: UserRole, db: Session) -> User:
    """
    Update user's role.

    Args:
        email: User email address (will be normalized to lowercase)
        role: New role to assign
        db: Database session

    Returns:
        Updated User object

    Raises:
        ValueError: If user not found
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Get user by email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise ValueError(f"User with email {email} not found")

    # Update role
    user.role = role
    db.commit()
    db.refresh(user)

    return user


def update_user_profile(
    user: User,
    db: Session,
    category: Optional[str] = None,
    gst_number: Optional[str] = None,
    shipping_address1: Optional[str] = None,
    shipping_address2: Optional[str] = None,
    shipping_pin: Optional[str] = None,
    shipping_city: Optional[str] = None,
    shipping_state: Optional[str] = None,
    shipping_country: Optional[str] = None
) -> User:
    """
    Update user profile information.

    Args:
        user: User object to update
        db: Database session
        category: User category (personal/organization)
        gst_number: GST number (required for organizations)
        shipping_address1: Shipping address line 1
        shipping_address2: Shipping address line 2
        shipping_pin: PIN code
        shipping_city: City
        shipping_state: State
        shipping_country: Country

    Returns:
        Updated User object

    Raises:
        ValueError: If validation fails
    """
    # Validate category and GST
    if category is not None:
        try:
            user_category = UserCategory(category.lower())
            user.category = user_category
            
            # If changing to organization, GST is required
            if user_category == UserCategory.ORGANIZATION and not gst_number and not user.gst_number:
                raise ValueError("GST number is required for organizations")
        except ValueError as e:
            if "Invalid category" in str(e):
                raise ValueError(f"Invalid category: {category}. Must be 'personal' or 'organization'")
            raise
    
    # Update GST number
    if gst_number is not None:
        # If category is organization and GST is being cleared, validate
        if user.category == UserCategory.ORGANIZATION and not gst_number:
            raise ValueError("GST number cannot be removed for organizations")
        user.gst_number = gst_number.upper().replace(' ', '').replace('-', '') if gst_number else None
    elif category == 'organization' and user.category == UserCategory.ORGANIZATION and not user.gst_number:
        raise ValueError("GST number is required for organizations")
    
    # Update shipping address fields
    if shipping_address1 is not None:
        user.shipping_address1 = shipping_address1
    if shipping_address2 is not None:
        user.shipping_address2 = shipping_address2
    if shipping_pin is not None:
        user.shipping_pin = shipping_pin.replace(' ', '') if shipping_pin else None
    if shipping_city is not None:
        user.shipping_city = shipping_city
    if shipping_state is not None:
        user.shipping_state = shipping_state
    if shipping_country is not None:
        user.shipping_country = shipping_country
    
    # Validate shipping address completeness
    address_fields = [
        user.shipping_address1,
        user.shipping_pin,
        user.shipping_city,
        user.shipping_state,
        user.shipping_country
    ]
    filled_fields = [f for f in address_fields if f]
    
    if filled_fields and not all([user.shipping_address1, user.shipping_pin, 
                                   user.shipping_city, user.shipping_state, user.shipping_country]):
        raise ValueError("All shipping address fields (address1, pin, city, state, country) are required together")
    
    db.commit()
    db.refresh(user)
    
    return user
