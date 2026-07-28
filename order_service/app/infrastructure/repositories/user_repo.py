# order_service/app/infrastructure/repositories/user_repo.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.infrastructure.db.models import UserDB

class UserRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(self, email: str, hashed_password: str) -> UserDB:
        """
        Saves a new user to the database with their pre-hashed password.
        """
        db_user = UserDB(
            email=email,
            hashed_password=hashed_password
        )
        self.db_session.add(db_user)
        await self.db_session.flush()
        return db_user

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        """
        Fetches a user by their email address. Useful for login & duplication checks.
        """
        query = select(UserDB).where(UserDB.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> Optional[UserDB]:
        """
        Fetches a user by their ID. Useful for token verification.
        """
        query = select(UserDB).where(UserDB.id == user_id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()