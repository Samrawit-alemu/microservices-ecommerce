# product_service/app/main.py
import threading
import time
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Added import
from contextlib import asynccontextmanager

from app.infrastructure.db.config import engine, Base
from app.infrastructure.api.routes import router as product_router
from app.infrastructure.messaging.consumer import RabbitMQConsumer

def start_rabbitmq_consumer():
    max_retries = 6
    retry_delay = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[*] Connection Attempt {attempt}/{max_retries} to RabbitMQ...")
            consumer = RabbitMQConsumer()
            consumer.start_consuming()
            break
        except Exception as e:
            print(f"[!] Connection Attempt {attempt} failed.")
            if attempt == max_retries:
                print("[!] Maximum RabbitMQ connection retries reached. Background consumer stopped.")
                traceback.print_exc()
            else:
                print(f"[*] RabbitMQ might still be starting. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    yield
    await engine.dispose()

app = FastAPI(
    title="Product Service",
    description="Microservice for managing product catalogs and inventory",
    version="1.0.0",
    lifespan=lifespan
)

# Added CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all local host ports to make requests
    allow_credentials=True,
    allow_methods=["*"],  # Permits GET, POST, etc.
    allow_headers=["*"],
)

app.include_router(product_router)

@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "product-service"}