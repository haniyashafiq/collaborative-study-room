from passlib.context import CryptContext
from fastapi import HTTPException, status

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    if isinstance(password, bytes):
        password = password.decode("utf-8")
    if len(password) > 72:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must not exceed 72 characters"
        )
    
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
