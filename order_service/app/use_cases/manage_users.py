# order_service/app/use_cases/manage_users.py
from typing import Optional
from app.infrastructure.repositories.user_repo import UserRepository
from app.infrastructure.security.auth_handler import AuthHandler
from app.infrastructure.db.models import UserDB

class UserUseCases:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, email: str, plain_password: str) -> UserDB:
        """
        Business logic for registering a new user securely.
        """
        # 1. Prevent duplicate email accounts
        existing_user = await self.user_repo.get_by_email(email)
        if existing_user:
            raise ValueError("Email already registered")

        # 2. Hash the password before saving
        hashed_password = AuthHandler.hash_password(plain_password)

        # 3. Save to database
        return await self.user_repo.create_user(email, hashed_password)

    async def login_user(self, email: str, plain_password: str) -> str:
        """
        Verifies credentials and returns a signed JWT access token.
        """
        # 1. Fetch user. If not found, raise a generic error
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")

        # 2. Verify password hash. If invalid, raise the same generic error
        is_valid = AuthHandler.verify_password(plain_password, str(user.hashed_password))
        if not is_valid:
            raise ValueError("Invalid email or password")

        # 3. Generate and return the signed JWT token
        return AuthHandler.create_access_token(int(user.id)) # type: ignore