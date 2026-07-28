# order_service/app/infrastructure/security/auth_handler.py
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional

# We load our JWT Secret Key from the environment, defaulting to a secure local string
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-for-portfolio-jwt-generation-12345")
JWT_ALGORITHM = "HS256"

class AuthHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashes a plain-text password using bcrypt.
        """
        # Generate a secure salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verifies a plain-text password against its stored hash.
        """
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    @staticmethod
    def create_access_token(user_id: int, expires_delta_hours: int = 24) -> str:
        """
        Generates a signed JSON Web Token (JWT) containing the user ID.
        """
        payload = {
            "sub": str(user_id),  # 'sub' (subject) is the standard JWT key for User ID
            "exp": datetime.utcnow() + timedelta(hours=expires_delta_hours)  # Expiration timestamp
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> Optional[int]:
        """
        Decodes a JWT token, verifies its signature and expiration, and returns the User ID.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return int(payload["sub"])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, ValueError):
            return None