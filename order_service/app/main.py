# order_service/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Added import
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as order_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()

app = FastAPI(
    title="Order Service",
    description="Microservice for orchestrating customer checkouts and transactions",
    version="1.0.0",
    lifespan=lifespan
)

# Added CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(order_router)

@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "order-service"}