# product_service/app/infrastructure/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.domain.models import Product as ProductDomain
from app.infrastructure.db.config import get_db
from app.infrastructure.repositories.product_repo import ProductRepository
from app.use_cases.manage_products import ProductUseCases

# Set up our router with the prefix "/products"
router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductDomain, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductDomain, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to add a new product to the catalog.
    """
    # 1. Instantiate the Repository with the injected DB Session
    repo = ProductRepository(db)
    
    # 2. Inject the Repository into the Use Case
    use_cases = ProductUseCases(repo)
    
    # 3. Execute the Use Case business logic
    return await use_cases.create_product(product)

@router.get("/{product_id}", response_model=ProductDomain)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    """
    Endpoint to retrieve a single product by its unique ID.
    """
    repo = ProductRepository(db)
    use_cases = ProductUseCases(repo)
    
    try:
        # Execute the Use Case logic
        return await use_cases.get_product(product_id)
    except ValueError as e:
        # Catch business logic errors (ValueError) and translate them to HTTP 404
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=str(e)
        )

@router.get("/", response_model=List[ProductDomain])
async def list_products(db: AsyncSession = Depends(get_db)):
    """
    Endpoint to fetch all products in the catalog.
    """
    repo = ProductRepository(db)
    use_cases = ProductUseCases(repo)
    return await use_cases.list_products()