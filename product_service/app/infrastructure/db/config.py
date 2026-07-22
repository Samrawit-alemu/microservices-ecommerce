# product_service/app/infrastructure/db/config.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# If 'DATABASE_URL' is set on the cloud server, use it. Otherwise, fallback to your working local database.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://postgres:password123@localhost:5433/product_db"
)

# Convert standard postgres:// URLs (used by cloud providers) to our psycopg async format
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_async_engine(DATABASE_URL, echo=True)
...

# Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Create a session maker for handling transactions
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for our SQLAlchemy ORM models
Base = declarative_base()

# Dependency to get database sessions in our API routes
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise