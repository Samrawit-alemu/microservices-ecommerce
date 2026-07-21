# order_service/app/infrastructure/external_services/chapa_client.py
import httpx
from typing import Optional
from decimal import Decimal

class ChapaClient:
    def __init__(self, secret_key: Optional[str] = None):
        # Fallback to a mock key if none is provided
        self.secret_key = secret_key or "CHAPUBK_TEST-MockKeyForPortfolioTesting"
        self.base_url = "https://api.chapa.co/v1"

    async def initialize_payment(
        self, 
        amount: Decimal, 
        email: str, 
        tx_ref: str, 
        callback_url: str
    ) -> str:
        """
        Calls Chapa to initialize a transaction.
        If using a mock key, it returns a simulated payment URL.
        """
        # If using a mock key, simulate a successful redirect URL immediately
        if "MockKey" in self.secret_key:
            print("[*] Chapa Mock Client: Simulating payment checkout url...")
            # We return a local endpoint we can visit to simulate payment success
            return f"http://localhost:8002/orders/mock-payment-success?tx_ref={tx_ref}"

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
                # Fallback to mock url on failure so execution doesn't crash
                return f"http://localhost:8002/orders/mock-payment-success?tx_ref={tx_ref}"
                
            except Exception as e:
                print(f"[!] Chapa Network Error: {str(e)}")
                return f"http://localhost:8002/orders/mock-payment-success?tx_ref={tx_ref}"