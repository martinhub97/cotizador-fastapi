import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

PG_USER = os.getenv("PG_USER", "postgres")
PG_PWD = os.getenv("PG_PWD", "tupassword")
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = os.getenv("PG_PORT", "5432")
PG_DB = os.getenv("PG_DB", "tubasededatos")
PG_SCHEMA = os.getenv("PG_SCHEMA", "public")

# Construir URL de conexión para psycopg2
SQLALCHEMY_DATABASE_URL = f"postgresql://{PG_USER}:{PG_PWD}@{PG_HOST}:{PG_PORT}/{PG_DB}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"options": f"-csearch_path={PG_SCHEMA}"}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependencia para inyectar sesión en los endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
