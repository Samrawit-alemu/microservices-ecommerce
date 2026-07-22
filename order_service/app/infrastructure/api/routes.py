# order_service/app/infrastructure/api/routes.py
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.domain.models import Order as OrderDomain, OrderCreate, OrderResponse
from app.infrastructure.db.config import get_db
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.external_services.product_client import ProductClient
from app.infrastructure.external_services.chapa_client import ChapaClient
from app.infrastructure.messaging.publisher import RabbitMQPublisher
from app.use_cases.manage_orders import OrderUseCases

router = APIRouter(prefix="/orders", tags=["Orders"])

# 1. Dependency Injection wiring helper
def get_order_use_cases(db: AsyncSession = Depends(get_db)) -> OrderUseCases:
    repo = OrderRepository(db)
    
    # Read the live Product Service live cloud URL if deployed, otherwise fallback to local
    product_service_url = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")
    product_client = ProductClient(base_url=product_service_url)
    
    # Read Chapa secret key from server environment
    chapa_secret_key = os.getenv("CHAPA_SECRET_KEY")
    chapa_client = ChapaClient(secret_key=chapa_secret_key)
    
    publisher = RabbitMQPublisher()
    return OrderUseCases(repo, product_client, chapa_client, publisher)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    """
    Endpoint to process checkout and return order + payment link.
    """
    # Replace this with your public Ngrok URL when testing live Chapa webhooks
    ngrok_url = "http://localhost:8002/orders/webhook/chapa"
    
    try:
        return await use_cases.create_order(order_data, callback_url=ngrok_url)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.post("/webhook/chapa", status_code=status.HTTP_200_OK)
async def chapa_webhook(
    payload: dict,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    """
    Webhook endpoint called asynchronously by Chapa (or our mock) on payment success.
    """
    tx_ref = payload.get("tx_ref")
    status_field = payload.get("status")

    if not tx_ref or status_field != "success":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook payload")

    try:
        await use_cases.confirm_payment(tx_ref)
        return {"status": "success", "message": "payment confirmed and stock decrement event published"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/mock-payment-success", response_class=HTMLResponse)
async def mock_payment_success(tx_ref: str):
    """
    Simulated landing page that automatically triggers our Chapa webhook locally.
    This provides a self-contained environment to demonstrate the full workflow.
    """
    # Simulate Chapa's webhook POST request internally
    webhook_payload = {"tx_ref": tx_ref, "status": "success"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post("http://localhost:8002/orders/webhook/chapa", json=webhook_payload)
            success = True
        except Exception:
            success = False

    if success:
        return """
        <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f4fdf4;">
                <h1 style="color: #2e7d32;">✔ Payment Successful (Mock Mode)</h1>
                <p>Transaction Reference: <strong>""" + tx_ref + """</strong></p>
                <p style="color: #555;">The Order Service updated your status to <strong>PAID</strong> and published an event to RabbitMQ.</p>
                <p style="color: #888;">You can close this tab and check your logs!</p>
            </body>
        </html>
        """
    return "<h3>Error executing mock payment webhook redirect</h3>"


@router.get("/{order_id}", response_model=OrderDomain)
async def get_order(
    order_id: int,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    try:
        return await use_cases.get_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))