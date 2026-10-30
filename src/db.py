import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from sqlalchemy import create_engine

# ----Read the connection string from the .env file in the project root----
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
DATABASE_URL = os.environ["DATABASE_URL"]


# ----For writing data (used by load_db.py)----
def get_connection():
    return psycopg.connect(DATABASE_URL)


# ----For reading into pandas (pd.read_sql wants a SQLAlchemy engine)----
def get_engine():
    return create_engine(DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1))
