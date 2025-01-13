from ninja import NinjaAPI
from .auth.api import router as auth_router
from .balance.api import router as balance_router
from .order.api import router as order_router
from .package.api import router as package_router
from .status.api import router as status_router

api = NinjaAPI(
    title="ATOM API",
    version="1.0.0",
    description="""
    # ATOM API Documentation
    
    ## Authentication
    All endpoints require JWT authentication.
    
    ## Rate Limiting
    API calls are limited to 1000 requests per hour per user.
    
    ## Pagination
    List endpoints support pagination with `page` and `size` parameters.
    
    ## Error Codes
    - 400: Bad Request
    - 401: Unauthorized
    - 403: Forbidden
    - 404: Not Found
    - 429: Too Many Requests
    """,
    docs_url="/docs",  # URL для документации
    openapi_url="/openapi.json",  # URL для OpenAPI схемы
    urls_namespace="api_v1",  # Добавить namespace для версионирования
)

api.add_router("/auth/", auth_router)
api.add_router("/balance/", balance_router)
api.add_router("/order/", order_router)
api.add_router("/package/", package_router)
api.add_router("/status/", status_router)
