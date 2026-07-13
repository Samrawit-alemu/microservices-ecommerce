# order_service/app/infrastructure/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Order as OrderDomain, OrderCreate
from app.infrastructure.db.config import get_db
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.external_services.product_client import ProductClient
from app.use_cases.manage_orders import OrderUseCases

router = APIRouter(prefix="/orders", tags=["Orders"])

# 1. Dependency injection helper
def get_order_use_cases(db: AsyncSession = Depends(get_db)) -> OrderUseCases:
    """
    Constructs and injects the OrderUseCases complete with its
    database repository and external HTTP client dependencies.
    """
    repo = OrderRepository(db)
    product_client = ProductClient()
    return OrderUseCases(repo, product_client)


@router.post("/", response_model=OrderDomain, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    """
    Endpoint to process checkout and create a pending order.
    """
    try:
        return await use_cases.create_order(order_data)
    except ValueError as e:
        # Invalid inputs (missing product or insufficient stock) -> 400 Bad Request
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except RuntimeError as e:
        # Downstream microservice is offline -> 503 Service Unavailable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.get("/{order_id}", response_model=OrderDomain)
async def get_order(
    order_id: int,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    """
    Endpoint to retrieve an order by its unique ID.
    """
    try:
        return await use_cases.get_order(order_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )