"""
Password hashing and verification service using SHA-256 + bcrypt
Uses SHA-256 pre-hashing to handle bcrypt's 72-byte limit automatically.
This approach works with passwords of any length.
"""
import hashlib
import base64
import bcrypt as bcrypt_lib


def hash_password(password: str) -> str:
    """
    Hash a password using SHA-256 + bcrypt.
    This automatically handles bcrypt's 72-byte limit by pre-hashing with SHA-256.
    
    Args:
        password: Plain text password (should be validated before calling)
        
    Returns:
        Hashed password string (bcrypt format)
        
    Raises:
        ValueError: If password is empty
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    # CRITICAL: Never pass password directly to bcrypt - always pre-hash with SHA-256
    # This avoids bcrypt's 72-byte limit completely
    sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
    base64_hash = base64.b64encode(sha256_hash).decode('utf-8')
    
    # base64_hash is always exactly 44 characters (32 bytes SHA-256 -> 44 base64 chars)
    # This is well under bcrypt's 72-byte limit
    # Use bcrypt library directly to avoid passlib's validation
    hashed = bcrypt_lib.hashpw(base64_hash.encode('utf-8'), bcrypt_lib.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    Supports both SHA-256+bcrypt (new) and plain bcrypt (legacy) formats.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    if not plain_password or not hashed_password:
        return False
    
    try:
        # Try SHA-256 + bcrypt method first (new format)
        sha256_hash = hashlib.sha256(plain_password.encode('utf-8')).digest()
        base64_hash = base64.b64encode(sha256_hash).decode('utf-8')
        
        # Use bcrypt library directly
        if bcrypt_lib.checkpw(base64_hash.encode('utf-8'), hashed_password.encode('utf-8')):
            return True
        
        # Fallback: try plain bcrypt (legacy format) - but truncate to 72 bytes
        # This handles old passwords that were hashed directly with bcrypt
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            plain_password = password_bytes[:72].decode('utf-8', errors='ignore')
        
        return bcrypt_lib.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, TypeError, Exception):
        # Invalid hash format or verification failed
        return False
