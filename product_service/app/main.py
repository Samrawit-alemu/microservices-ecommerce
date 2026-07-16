# product_service/app/main.py
import threading
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as product_router
from app.infrastructure.messaging.consumer import RabbitMQConsumer


# Helper function to initialize and run our blocking consumer
def start_rabbitmq_consumer():
    """
    Instantiates and starts our RabbitMQ message listener.
    """
    try:
        consumer = RabbitMQConsumer()
        print("[*] Starting RabbitMQ Background Consumer...")
        consumer.start_consuming()
    except Exception as e:
        print(f"[!] Failed to start background consumer: {str(e)}")


# Database Table & Consumer Initialization via Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create DB tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Launch the RabbitMQ Consumer in a separate background thread
    # Setting daemon=True ensures the thread terminates automatically when the app stops
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()

    yield  # The web server runs here
    
    # Clean up connection pools on shutdown
    await engine.dispose()


# Initialize the FastAPI App
app = FastAPI(
    title="Product Service",
    description="Microservice for managing product catalogs and inventory",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(product_router)

@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "product-service"}