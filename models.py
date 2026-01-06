from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column,Integer,String,DateTime
from datetime import datetime
Base = declarative_base()

class User(Base):
  __tablename__ = "user"
  id = Column(Integer,primary_key=True)
  username = Column(String,unique = True, index=True)
  hashed_password = Column(String)
  created_at = Column(DateTime,default=datetime.utcnow)
  
