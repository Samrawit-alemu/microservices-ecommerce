# product_service/app/domain/models.py
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional

class Product(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=255, description="The name of the product")
    description: Optional[str] = Field(None, description="Detailed product description")
    price: Decimal = Field(..., gt=0, description="Product price, must be greater than zero")
    stock: int = Field(..., ge=0, description="Available stock quantity, cannot be negative")

    # This configuration allows Pydantic to work seamlessly with ORM models (like SQLAlchemy) later
    model_config = ConfigDict(from_attributes=True)