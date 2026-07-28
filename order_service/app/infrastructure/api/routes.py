# order_service/app/infrastructure/api/routes.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer  # Added import
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.domain.models import Order as OrderDomain, OrderCreate, OrderResponse, UserRegister, UserLogin, UserResponse, TokenResponse
from app.infrastructure.db.config import get_db
from app.infrastructure.repositories.order_repo import OrderRepository
from app.infrastructure.repositories.user_repo import UserRepository
from app.infrastructure.external_services.product_client import ProductClient
from app.infrastructure.external_services.chapa_client import ChapaClient
from app.infrastructure.messaging.publisher import RabbitMQPublisher
from app.infrastructure.security.auth_handler import AuthHandler
from app.use_cases.manage_orders import OrderUseCases
from app.use_cases.manage_users import UserUseCases
from app.infrastructure.db.models import UserDB

router = APIRouter(prefix="/orders", tags=["Orders"])

# 1. Initialize FastAPI's security Bearer schema
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="orders/auth/login")


# --- DEPENDENCIES ---

def get_order_use_cases(db: AsyncSession = Depends(get_db)) -> OrderUseCases:
    repo = OrderRepository(db)
    product_client = ProductClient(base_url=os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001"))
    chapa_client = ChapaClient(secret_key=os.getenv("CHAPA_SECRET_KEY"), order_service_url=os.getenv("ORDER_SERVICE_URL", "http://localhost:8002"))
    publisher = RabbitMQPublisher()
    return OrderUseCases(repo, product_client, chapa_client, publisher)

def get_user_use_cases(db: AsyncSession = Depends(get_db)) -> UserUseCases:
    repo = UserRepository(db)
    return UserUseCases(repo)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserDB:
    """
    FastAPI security dependency. Extracts the JWT token, verifies its signature,
    and injects the authenticated User database model into protected endpoints.
    """
    user_id = AuthHandler.decode_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user no longer exists",
        )
    return user


# --- AUTH ENDPOINTS ---

@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    try:
        return await use_cases.register_user(user_data.email, user_data.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/auth/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    try:
        token = await use_cases.login_user(credentials.email, credentials.password)
        return {"access_token": token, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


# --- SECURED ORDER ENDPOINTS ---

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: UserDB = Depends(get_current_user),  # Protected by JWT authentication
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    """
    Creates an order linked securely to the authenticated User.
    """
    order_service_url = os.getenv("ORDER_SERVICE_URL", "http://localhost:8002")
    callback_url = f"{order_service_url}/orders/webhook/chapa"
    
    try:
        # Pass the verified user's ID and Email securely fetched from the database
        return await use_cases.create_order(
            order_data, 
            user_id=int(current_user.id),  # type: ignore
            email=str(current_user.email), 
            callback_url=callback_url
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


# --- WEBHOOKS & UTILITIES ---

@router.post("/webhook/chapa", status_code=status.HTTP_200_OK)
async def chapa_webhook(
    payload: dict,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
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
async def mock_payment_success(request: Request, tx_ref: str):
    base_url = str(request.base_url).rstrip("/")
    webhook_payload = {"tx_ref": tx_ref, "status": "success"}
    async with httpx.AsyncClient() as client:
        try:
            await client.post(f"{base_url}/orders/webhook/chapa", json=webhook_payload)
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


# Registered before /{order_id} so "me" is not parsed as an integer path param
@router.get("/me", response_model=List[OrderDomain])
async def list_my_orders(
    current_user: UserDB = Depends(get_current_user),
    use_cases: OrderUseCases = Depends(get_order_use_cases),
):
    """
    Returns the authenticated user's order history (JWT-scoped).
    """
    return await use_cases.list_orders_for_user(int(current_user.id))  # type: ignore


@router.get("/{order_id}", response_model=OrderDomain)
async def get_order(
    order_id: int,
    use_cases: OrderUseCases = Depends(get_order_use_cases)
):
    try:
        return await use_cases.get_order(order_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))