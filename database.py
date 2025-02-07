from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

import os
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
# Create MetaData instance
metadata = MetaData()
# Reflect the database
metadata.reflect(bind=engine)
# Create automap base
Base = automap_base(metadata=metadata)
Base.prepare()
# Get the Runner model class
Runner = Base.classes.Runner
Activity = Base.classes.Activity

# SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
