# product_service/app/infrastructure/db/config.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# PostgreSQL async connection URL (points to our Docker container)
DATABASE_URL = "postgresql+psycopg://postgres:password123@localhost:5433/product_db"

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