# order_service/app/infrastructure/external_services/product_client.py
import httpx
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

class ProductResponse(BaseModel):
    """
    Temporary schema representing the product data 
    returned by the Product Service.
    """
    id: int
    name: str
    price: Decimal
    stock: int

class ProductClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url

    async def get_product_details(self, product_id: int) -> Optional[ProductResponse]:
        """
        Queries the Product Service (on port 8001) for product pricing and stock.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/products/{product_id}")
                
                if response.status_code == 200:
                    return ProductResponse(**response.json())
                return None
                
            except httpx.RequestError:
                # Triggers if the Product Service is completely offline/crashed
                raise RuntimeError("Product Service is currently offline or unreachable")