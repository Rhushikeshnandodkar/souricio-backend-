"""
API v1 router aggregation
"""
from fastapi import APIRouter
from app.api.v1.endpoints import products, categories, tags, admin, auth, cart, quotes, images, orders, shipping

api_router = APIRouter()

api_router.include_router(
    auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(
    products.router, prefix="/products", tags=["Products"])
api_router.include_router(
    categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(tags.router, prefix="/tags", tags=["Tags"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(cart.router, prefix="/cart", tags=["Cart"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])
api_router.include_router(quotes.admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(orders.router, prefix="/orders", tags=["Orders"])
api_router.include_router(orders.admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(images.router, prefix="/images", tags=["Images"])
api_router.include_router(shipping.router, prefix="/shipping", tags=["Shipping"])
