# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/iot_ble")

# Neon requires SSL — detect and configure accordingly
connect_args = {}
if DATABASE_URL and "neon.tech" in DATABASE_URL:
    connect_args = {"sslmode": "require"}

# Engine SQLAlchemy (echo=False in production)
engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "false").lower() == "true",
    pool_pre_ping=True,
    connect_args=connect_args,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base ORM
Base = declarative_base()