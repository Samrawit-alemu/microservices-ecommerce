# product_service/app/infrastructure/repositories/product_repo.py
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.infrastructure.db.models import ProductDB
from app.domain.models import Product as ProductDomain

class ProductRepository:
    def __init__(self, db_session: AsyncSession):
        """
        We inject the database session here.
        This is called 'Dependency Injection' and makes testing much easier.
        """
        self.db_session = db_session

    async def create(self, product: ProductDomain) -> ProductDB:
        """
        Takes a Pydantic (Domain) model, maps it to a SQLAlchemy (DB) model,
        and saves it to the PostgreSQL database.
        """
        db_product = ProductDB(
            name=product.name,
            description=product.description,
            price=product.price,
            stock=product.stock,
            image_url=product.image_url
        )
        self.db_session.add(db_product)
        # Flush sends the insert SQL query to the DB immediately
        # so PostgreSQL generates the 'id' and we can return it.
        await self.db_session.flush()
        return db_product

    async def get_by_id(self, product_id: int) -> Optional[ProductDB]:
        """
        Queries PostgreSQL for a single product by its unique integer ID.
        """
        query = select(ProductDB).where(ProductDB.id == product_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(self) -> List[ProductDB]:
        """
        Queries PostgreSQL for a list of all products in the catalog.
        """
        # Without an explicit order, Postgres returns heap order, which reshuffles
        # the storefront grid whenever a row is updated by a stock decrement.
        query = select(ProductDB).order_by(ProductDB.id)
        result = await self.db_session.execute(query)
        return list(result.scalars().all())