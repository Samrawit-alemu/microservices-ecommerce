# product_service/app/infrastructure/db/models.py
from sqlalchemy import Column, Integer, String, Text, Numeric
from app.infrastructure.db.config import Base

class ProductDB(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    stock = Column(Integer, nullable=False, default=0)