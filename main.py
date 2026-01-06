from fastapi import FastAPI,Depends,HTTPException,Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from fastapi.responses import JSONResponse
from typing import Annotated
from config import settings
from models import User
from schema import successfull_reponse,error_response,APIResponse,UserOut,UserIn,UserDbIn
from dependancies import get_db,authenticate,token_generator,get_current_user,hash_password
from fastapi.exceptions import RequestValidationError
from datetime import timedelta
from sqlalchemy import select
from uuid import uuid4
import httpx
import asyncio
app = FastAPI()

algo = settings.ALGO
@app.middleware("http")
async def set_request_id(request:Request,call_next):
  request_id = request.headers.get("X-Request-ID",str(uuid4()))
  request.state.request_id = request_id
  response = await call_next(request)
  response.headers["X-Request-ID"] = request_id
  return response
  
@app.exception_handler(HTTPException)
async def http_exception(request:Request,exc:HTTPException):
  return error_response(message=exc.detail,status_code=exc.status_code,request_id=getattr(request.state,"request_id",None))
@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc:RequestValidationError):
  field_errors = {}
  for error in exc.errors():
    field = error["loc"][-1]
    field_errors.setdefault(field,[]).append(error["msg"])
  return error_response(message="validation error",status_code=422,errors=field_errors,request_id=getattr(request.state, "request_id",None))

@app.exception_handler(Exception)
async def general_exception(request:Request,exc:Exception):
    return error_response(status_code=500,message="Something went wrong. Please try again later.",request_id=getattr(request.state, "request_id", None))
  
  
@app.post("/user/signup/",response_model=APIResponse[UserOut])
async def register_user(user:UserIn,db:AsyncSession = Depends(get_db)):
  user = User(**user.model_dump(exclude={"password"}),hashed_password=hash_password(user.password))
  try:
      async with db.begin():
        db.add(user)
  except IntegrityError as e:
    if "username" in str(e.orig):
      raise HTTPException(409,"username already used!!")  
  return successfull_reponse(message="sign up successfully!!!",data=user)
  


@app.post("/login")
async def login(form:Annotated[OAuth2PasswordRequestForm,Depends()],db:AsyncSession = Depends(get_db)):
  username = form.username
  password = form.password
  credentials_exception = HTTPException(status_code=401,detail="Invalid username or password!!!",headers={"WWW-Authenticate":"Bearer"})
  
  user = await authenticate(db=db,username=username,password=password)
  if not user:
    raise credentials_exception
  access_token = token_generator({"sub":str(user.id),"type":"access"},secret_key=settings.ACCESS_TOKEN_SECRET_KEY,exp=timedelta(hours=7))
  refresh_token = token_generator({"sub":str(user.id),"type":"refresh"},secret_key=settings.REFRESH_TOKEN_SECRET_KEY,exp=timedelta(days=30))
  response = JSONResponse(status_code=200,content={"access_token":access_token,"token_type":"Bearer"})
  response.set_cookie(
    key="refresh",
    value=refresh_token,
    httponly = True,
    secure = False,
    max_age = 3600 * 24 * 7
  )
  return response


@app.get("/user/profile", response_model=APIResponse[UserOut])
async def get_user(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(User).where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User doesn't exist")

    user_out = UserOut.model_validate(user)

    return successfull_reponse(
        message="user fetched",
        data=user_out
    )
@app.get("/external/data")
async def fetch_external_data():
    urls = [
        "https://jsonplaceholder.typicode.com/posts/1",
        "https://jsonplaceholder.typicode.com/posts/2",
        "https://jsonplaceholder.typicode.com/posts/3",
    ]

    async with httpx.AsyncClient(timeout=10) as client:

        async def fetch(url: str):
            response = await client.get(url)
            return response.json()

        results = await asyncio.gather(
            *(fetch(url) for url in urls)
        )

    return {
        "count": len(results),
        "data": results
    }
