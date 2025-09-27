from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from app import models, schemas
from app.database import get_db
from app.auth_utils import create_access_token, verify_access_token, verify_password, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

# Dependency to get current logged-in user
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username: str = payload.get("sub")
    result = await db.execute(
        select(models.User).filter(models.User.username == username)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/register", response_model=schemas.UserOut)
async def register_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user with username + password (hashed).
    """
    # Check if user already exists
    result = await db.execute(select(models.User).filter(models.User.username == user.username))
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    print("PASSWORD TYPE:", type(user.password))
    print("PASSWORD VALUE:", user.password)
    print("PASSWORD LENGTH:", len(user.password))

    hashed_pw = hash_password(user.password)
    new_user = models.User(username=user.username, email=user.email, hashed_password=hashed_pw)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username & password (checks DB).
    Returns JWT token if valid.
    """
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    user = result.scalars().first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# 🔹 Logout route (client should simply discard token)
@router.post("/logout")
async def logout(current_user: models.User = Depends(get_current_user)):
    return {"message": f"User '{current_user.username}' logged out successfully. Please discard your token."}


# {
#   "username": "alice",
#   "email": "alice@example.com",
#   "password": "password123"
# }

# {
#     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhbGljZSIsImV4cCI6MTc1ODk0NTM3MH0.pt6HvAury203dQMKDcWryGS0tUm8bFxeODMXS2lj39Q",
#     "token_type": "bearer"
# }

# {
#   "username": "bob",
#   "email" : "bob@example.com",
#   "password": "password123"
# }

# {
#     "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJib2IiLCJleHAiOjE3NTg5NDU1NDR9.wjfNZWzX-pxqEjL7H8dq3oaRSySjV8vCR61Hl6qlDus",
#     "token_type": "bearer"
# }