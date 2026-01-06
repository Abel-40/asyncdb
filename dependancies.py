import jwt
from db_connection import AsyncLocalSession
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User
from pwdlib import PasswordHash
from datetime import datetime, timezone,timedelta
from config import settings
from fastapi import HTTPException,Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Annotated
from jwt import PyJWTError
# helper function

auth_scheme = OAuth2PasswordBearer(tokenUrl="/login")
password = PasswordHash.recommended()
algo = settings.ALGO
def hash_password(plain_password:str):
  return password.hash(plain_password)

def verify_password(plain_password:str,hashed_password:str):
  return password.verify(plain_password,hashed_password)

async def get_db():
  async with AsyncLocalSession() as session:
    yield session

async def get_user(db:AsyncSession,username:str):
  user = await db.execute(select(User).where(User.username == username))
  return user.scalar_one_or_none()


async def authenticate(db:AsyncSession,username:str,password:str):
  user = await get_user(db=db,username=username)
  if not user:
    return False
  if not verify_password(password,user.hashed_password):
    return False
  return user

def token_generator(data:dict,secret_key:str,exp:timedelta | None = None):
  to_encode = data.copy()
  if exp:
    exp = datetime.now(timezone.utc) + exp
  else:
    exp = datetime.now(timezone.utc) + timedelta(days=15)
  to_encode.update({"exp":exp})
  token = jwt.encode(to_encode,secret_key,algorithm=algo)
  
  return token


async def get_current_user(
    token: Annotated[str, Depends(auth_scheme)],
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.ACCESS_TOKEN_SECRET_KEY,
            algorithms=[algo],
        )

        token_type = payload.get("type")
        if token_type != "access":
            raise credentials_exception

        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except PyJWTError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user



  