# product_service/app/use_cases/manage_products.py
from typing import List
from app.domain.models import Product as ProductDomain
from app.infrastructure.repositories.product_repo import ProductRepository
from app.infrastructure.db.models import ProductDB

class ProductUseCases:
    def __init__(self, product_repo: ProductRepository):
        """
        We inject the ProductRepository here.
        The Use Case does not know how to write SQL queries; 
        it simply tells the repository what to fetch or save.
        """
        self.product_repo = product_repo

    async def create_product(self, product_data: ProductDomain) -> ProductDB:
        """
        Handles the business workflow for adding a new product.
        In the future, we would add rules here like: 'Prevent duplicate product names'.
        """
        return await self.product_repo.create(product_data)

    async def get_product(self, product_id: int) -> ProductDB:
        """
        Handles retrieving a single product. 
        If the product does not exist, we raise a ValueError.
        """
        product = await self.product_repo.get_by_id(product_id)
        if not product:
            # We raise a generic Python error here, NOT a FastAPI HTTPException
            raise ValueError(f"Product with ID {product_id} not found")
        return product

    async def list_products(self) -> List[ProductDB]:
        """
        Handles listing all products in our catalog.
        """
        return await self.product_repo.list_all()