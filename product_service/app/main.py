# product_service/app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as product_router


# 1. Database Table Initialization via Lifespan Events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the application.
    When the app starts, we automatically create our PostgreSQL tables.
    """
    async with engine.begin() as conn:
        # Runs SQLAlchemy Base.metadata.create_all in an async thread
        await conn.run_sync(Base.metadata.create_all)
    
    yield  # The application runs while paused here
    
    # Shutdown tasks (e.g., closing database connection pools) go here
    await engine.dispose()


# 2. Initialize the FastAPI Application
app = FastAPI(
    title="Product Service",
    description="Microservice for managing product catalogs and inventory",
    version="1.0.0",
    lifespan=lifespan
)


# 3. Include our Clean Architecture API routes
app.include_router(product_router)


# 4. Global Health Check Endpoint
@app.get("/", tags=["Health"])
async def health_check():
    """
    A simple health check endpoint to verify the service is running.
    """
    return {"status": "healthy", "service": "product-service"}