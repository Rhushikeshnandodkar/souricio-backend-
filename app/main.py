"""
Main FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination

from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import json
from sqlalchemy import text
from app.core.config import settings
from app.db.database import engine
from app.db.models.base import Base
# Import all models to ensure they're registered with Base.metadata
from app.db.models import (
    Category, Tag, Product, ProductVariant, User, OTP, Cart,
    Quote, QuoteItem, ProductPriceHistory, Order, OrderItem
)
from app.api.v1.api import api_router
from app.schemas.response import ErrorResponse, ErrorDetail
from datetime import datetime
from fastapi.openapi.utils import get_openapi
from app.lib.redis_client import close_redis_client, check_redis_health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events.
    """
    # Startup: Create tables if they don't exist
    try:
        from sqlalchemy import inspect as sql_inspect
        inspector = sql_inspect(engine)
        existing_tables = inspector.get_table_names()

        # If tables exist, check if they have new columns
        needs_recreate = False
        if existing_tables:
            try:
                # Check if categories table has new columns
                if 'categories' in existing_tables:
                    category_columns = [col['name']
                                        for col in inspector.get_columns('categories')]
                    if 'parent_id' not in category_columns:
                        needs_recreate = True
                        print(
                            "⚠️  Schema mismatch detected. Tables need to be recreated.")

                # Check if users table has required columns
                if 'users' in existing_tables:
                    user_columns = [col['name']
                                    for col in inspector.get_columns('users')]
                    required_user_columns = ['role', 'category', 'gst_number', 'shipping_address1',
                                             'shipping_address2', 'shipping_pin', 'shipping_city',
                                             'shipping_state', 'shipping_country']
                    missing_user_columns = [
                        col for col in required_user_columns if col not in user_columns]
                    if missing_user_columns:
                        needs_recreate = True
                        print(
                            f"⚠️  Schema mismatch detected. Users table missing columns: {missing_user_columns}. Tables need to be recreated.")

                # Check if carts table exists and has required columns
                if 'carts' in existing_tables:
                    cart_columns = [col['name']
                                    for col in inspector.get_columns('carts')]
                    required_columns = ['user_id',
                                        'product_id', 'variant_id', 'quantity']
                    missing_columns = [
                        col for col in required_columns if col not in cart_columns]
                    if missing_columns:
                        needs_recreate = True
                        print(
                            f"⚠️  Schema mismatch detected. Carts table missing columns: {missing_columns}. Tables need to be recreated.")

                # Check if orders table exists and has required columns
                if 'orders' in existing_tables:
                    order_columns = [col['name']
                                     for col in inspector.get_columns('orders')]
                    required_order_columns = ['order_number', 'quote_id', 'user_id', 'status',
                                              'subtotal', 'total_tax', 'total', 'tax_breakdown',
                                              'notes', 'created_at', 'updated_at']
                    missing_order_columns = [
                        col for col in required_order_columns if col not in order_columns]
                    if missing_order_columns:
                        needs_recreate = True
                        print(
                            f"⚠️  Schema mismatch detected. Orders table missing columns: {missing_order_columns}. Tables need to be recreated.")
                elif 'orders' not in existing_tables:
                    print("⚠️  Orders table not found. Will be created on startup.")

                # Check if order_items table exists and has required columns
                if 'order_items' in existing_tables:
                    order_item_columns = [col['name']
                                          for col in inspector.get_columns('order_items')]
                    required_order_item_columns = ['order_id', 'product_id', 'product_name',
                                                   'price', 'quantity', 'created_at']
                    missing_order_item_columns = [
                        col for col in required_order_item_columns if col not in order_item_columns]
                    if missing_order_item_columns:
                        needs_recreate = True
                        print(
                            f"⚠️  Schema mismatch detected. Order_items table missing columns: {missing_order_item_columns}. Tables need to be recreated.")
                elif 'order_items' not in existing_tables:
                    print(
                        "⚠️  Order_items table not found. Will be created on startup.")
            except Exception as check_error:
                print(f"Warning: Could not check schema: {check_error}")
                needs_recreate = True

        if needs_recreate:
            print("🔄 Dropping and recreating tables to match new schema...")
            # Drop all tables with CASCADE to handle foreign key dependencies
            try:
                # Use SQLAlchemy's drop_all which handles dependencies
                Base.metadata.drop_all(bind=engine, checkfirst=True)
            except Exception as drop_error:
                print(f"Warning during drop_all: {drop_error}")
                # Fallback: drop tables individually with CASCADE
                try:
                    from sqlalchemy import inspect as sql_inspect
                    inspector = sql_inspect(engine)
                    existing_tables = inspector.get_table_names()
                    with engine.begin() as conn:
                        # Drop tables in reverse dependency order
                        for table_name in reversed(existing_tables):
                            conn.execute(
                                text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                except Exception as fallback_error:
                    print(f"Fallback drop failed: {fallback_error}")

            Base.metadata.create_all(bind=engine)
            print("✓ Tables recreated successfully")
        else:
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Error creating tables: {e}")
        # If creation fails due to schema mismatch, try dropping first
        try:
            print("Attempting to drop and recreate tables...")
            # Use SQLAlchemy's drop_all which handles dependencies
            try:
                Base.metadata.drop_all(bind=engine, checkfirst=True)
            except Exception as drop_error:
                print(f"Warning during drop_all: {drop_error}")
                # Fallback: drop tables individually with CASCADE
                try:
                    from sqlalchemy import inspect as sql_inspect
                    inspector = sql_inspect(engine)
                    existing_tables = inspector.get_table_names()
                    with engine.begin() as conn:
                        # Drop tables in reverse dependency order
                        for table_name in reversed(existing_tables):
                            conn.execute(
                                text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
                except Exception as fallback_error:
                    print(f"Fallback drop failed: {fallback_error}")

            Base.metadata.create_all(bind=engine)
            print("✓ Tables recreated successfully")
        except Exception as e2:
            print(f"Error resetting database: {e2}")

    yield

    # Shutdown: Close Redis connection
    await close_redis_client()


app = FastAPI(
    title=settings.APP_NAME,
    description="Product management API for Sourcio",
    version=settings.APP_VERSION,
    lifespan=lifespan
)


def custom_openapi():
    """Custom OpenAPI schema with Bearer token authentication."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Product management API for Sourcio",
        routes=app.routes,
    )

    # Ensure components section exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}

    # Add or update Bearer token security scheme
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    openapi_schema["components"]["securitySchemes"]["Bearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Global exception handlers for consistent error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent format"""
    # If detail is already an ErrorResponse dict, serialize it properly
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        # Ensure datetime objects are serialized
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_datetime(item) for item in obj]
            return obj

        serialized_detail = serialize_datetime(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=serialized_detail
        )

    # Otherwise, wrap in standard error format
    error_response = ErrorResponse(
        status="error",
        message=exc.detail if isinstance(
            exc.detail, str) else "An error occurred",
        error=ErrorDetail(
            code=f"HTTP_{exc.status_code}",
            message=exc.detail if isinstance(
                exc.detail, str) else "Request failed"
        )
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=json.loads(error_response.model_dump_json())
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with consistent format"""
    errors = exc.errors()
    first_error = errors[0] if errors else None

    error_detail = ErrorResponse(
        status="error",
        message="Validation error",
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message=first_error.get(
                "msg", "Invalid request data") if first_error else "Invalid request",
            field=str(first_error.get("loc", [])[-1]
                      ) if first_error and first_error.get("loc") else None
        )
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=json.loads(error_detail.model_dump_json())
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with consistent format"""
    error_detail = ErrorResponse(
        status="error",
        message="Internal server error",
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later."
        )
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=json.loads(error_detail.model_dump_json())
    )

# Configure CORS
origins = settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix="/api/v1")

# Add pagination support to the app
add_pagination(app)


@app.get("/", tags=["Health"])
def root() -> dict:
    """
    Root endpoint to welcome users.
    """
    return {"message": "Welcome to Sourcio Backend"}


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint to verify backend, database, and Redis connectivity.

    Returns:
        Health status with database and Redis connection status
    """
    health_status = {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "disconnected",
        "redis": "disconnected"
    }

    # Check database connection
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            health_status["database"] = "connected"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["database"] = f"error: {str(e)}"

    # Check Redis connection
    try:
        redis_healthy = await check_redis_health()
        if redis_healthy:
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "not configured or unavailable"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        # Redis failure doesn't make the service unhealthy, just log it

    return health_status
