# product_service/app/infrastructure/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.domain.models import Product as ProductDomain
from app.infrastructure.db.config import get_db
from app.infrastructure.repositories.product_repo import ProductRepository
from app.use_cases.manage_products import ProductUseCases

router = APIRouter(prefix="/products", tags=["Products"])

# 1. Define a helper dependency to handle the architectural wiring
def get_product_use_cases(db: AsyncSession = Depends(get_db)) -> ProductUseCases:
    """
    FastAPI dependency that constructs the repository and the use cases.
    Notice that this dependency itself 'Depends' on our get_db dependency.
    """
    repo = ProductRepository(db)
    return ProductUseCases(repo)


@router.post("/", response_model=ProductDomain, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductDomain, 
    use_cases: ProductUseCases = Depends(get_product_use_cases)  # 2. Inject the use case directly
):
    """
    Endpoint to add a new product.
    """
    return await use_cases.create_product(product)


@router.get("/{product_id}", response_model=ProductDomain)
async def get_product(
    product_id: int, 
    use_cases: ProductUseCases = Depends(get_product_use_cases)
):
    """
    Endpoint to retrieve a product by its ID.
    """
    try:
        return await use_cases.get_product(product_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )


@router.get("/", response_model=List[ProductDomain])
async def list_products(
    use_cases: ProductUseCases = Depends(get_product_use_cases)
):
    """
    Endpoint to fetch all products.
    """
    return await use_cases.list_products()