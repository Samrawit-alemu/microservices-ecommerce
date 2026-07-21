# order_service/app/domain/models.py
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

class OrderItem(BaseModel):
    product_id: int = Field(..., description="The ID of the product being purchased")
    quantity: int = Field(..., gt=0, description="Quantity must be at least 1")
    unit_price: Optional[Decimal] = Field(None, description="Price at purchase time (set by backend)")

    model_config = ConfigDict(from_attributes=True)

class OrderCreate(BaseModel):
    customer_email: str = Field(..., description="Customer email address")
    items: List[OrderItem] = Field(..., min_length=1, description="Order must contain at least one item")

class Order(BaseModel):
    id: Optional[int] = None
    customer_email: str
    total_amount: Decimal
    status: str  # 'PENDING', 'PAID', 'FAILED'
    tx_ref: str  # Unique transaction reference for Chapa
    created_at: datetime
    items: List[OrderItem]

    model_config = ConfigDict(from_attributes=True)

class OrderResponse(BaseModel):
    order: Order
    payment_url: str