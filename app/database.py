import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()  # load .env

DATABASE_URL = os.getenv("DATABASE_URL")

# create async engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# session factory for async sessions
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# base class for models
Base = declarative_base()

# dependency for FastAPI
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
