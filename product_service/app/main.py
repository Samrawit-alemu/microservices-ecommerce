# product_service/app/main.py
import threading
import traceback
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as product_router
from app.infrastructure.messaging.consumer import RabbitMQConsumer


# Helper function to initialize and run our blocking consumer
# Open product_service/app/main.py and replace the start_rabbitmq_consumer function with this:
import time  # Ensure this is imported at the top of the file
import traceback

def start_rabbitmq_consumer():
    """
    Starts our RabbitMQ message listener with a robust connection retry loop.
    This prevents the app from crashing if RabbitMQ is still booting up.
    """
    max_retries = 6
    retry_delay = 5  # seconds
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[*] Connection Attempt {attempt}/{max_retries} to RabbitMQ...")
            consumer = RabbitMQConsumer()
            consumer.start_consuming()
            break  # If connection succeeds, break the loop and run the consumer
        except Exception as e:
            print(f"[!] Connection Attempt {attempt} failed.")
            if attempt == max_retries:
                print("[!] Maximum RabbitMQ connection retries reached. Background consumer stopped.")
                traceback.print_exc()
            else:
                print(f"[*] RabbitMQ might still be starting. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)


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