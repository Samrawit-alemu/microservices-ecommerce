# order_service/app/infrastructure/external_services/chapa_client.py
import httpx
from typing import Optional
from decimal import Decimal

class ChapaClient:
    def __init__(self, secret_key: Optional[str] = None, order_service_url: Optional[str] = None):
        self.secret_key = secret_key or "CHAPUBK_TEST-MockKeyForPortfolioTesting"
        self.base_url = "https://api.chapa.co/v1"
        # Dynamically load the order service base URL
        self.order_service_url = order_service_url or "http://localhost:8002"

    async def initialize_payment(
        self, 
        amount: Decimal, 
        email: str, 
        tx_ref: str, 
        callback_url: str
    ) -> str:
        """
        Initializes a transaction. If using a mock key, redirects to the dynamic order service URL.
        """
        if "MockKey" in self.secret_key:
            print("[*] Chapa Mock Client: Simulating payment checkout url...")
            # Dynamically uses the host URL (whether local or cloud)
            return f"{self.order_service_url}/orders/mock-payment-success?tx_ref={tx_ref}"

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "amount": str(amount),
            "currency": "ETB",
            "email": email,
            "first_name": "Customer",
            "last_name": "User",
            "tx_ref": tx_ref,
            "callback_url": callback_url,
            "customization": {
                "title": "My Portfolio Store",
                "description": "Order Payment"
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/transaction/initialize",
                    json=payload,
                    headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", {}).get("checkout_url")
                
                print(f"[!] Chapa initialization failed: {response.text}")
                return f"{self.order_service_url}/orders/mock-payment-success?tx_ref={tx_ref}"
                
            except Exception as e:
                print(f"[!] Chapa Network Error: {str(e)}")
                return f"{self.order_service_url}/orders/mock-payment-success?tx_ref={tx_ref}"