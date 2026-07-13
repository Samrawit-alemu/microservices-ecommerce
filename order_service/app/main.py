# order_service/app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as order_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup tasks: Create database tables in our 'order_db'.
    Shutdown tasks: Dispose of connection pools.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    await engine.dispose()


# Initialize the Order Service application
app = FastAPI(
    title="Order Service",
    description="Microservice for orchestrating customer checkouts and transactions",
    version="1.0.0",
    lifespan=lifespan
)

# Include the order endpoints
app.include_router(order_router)

# Health Check
@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "order-service"}