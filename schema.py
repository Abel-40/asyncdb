from pydantic import BaseModel
from typing import Generic,TypeVar,Dict,Any,List,Optional
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
import math
class User(BaseModel):
  username:str

class UserIn(User):
  password:str
  
class UserDbIn(User):
  hashed_password:str
  
class UserOut(BaseModel):
  id:int
  username:str
  
  model_config = {
      "from_attributes": True
  }
    
T = TypeVar("T")
class APIResponse(BaseModel,Generic[T]):
  success:bool
  message:str
  data:T | None = None
  errors:Any | None = None
  meta:Any | None = None

  
  
I = TypeVar("I")
class PaginationMeta(BaseModel):
  page:int
  page_size:int
  total_pages:int
  total_itmes:int
  
class PaginatedItem(BaseModel,Generic[I]):
  items:List[I]
  meta:PaginationMeta
  
  
async def paginated_query_response(db:AsyncSession,stmt,page:int,page_size:int):
  count = select(func.count()).select(stmt.subquery())
  total_itmes = await db.exceute(count).scalar_one()
  total_pages = math.ceil(total_itmes/page_size)
  pagination_stmt = (
    stmt
    .offset((page - 1) * page_size)
    .limit(page_size)
  )
  
  items = await db.execute(pagination_stmt).scalars().all()
  
  content = {
    "items":items,
    "meta":{
      "page":page,
      "page_size":page_size,
      "total_pages":total_pages,
      "total_items":total_itmes
      
    }
  }
  return content
  
def successfull_reponse(message:str,data:T | None = None,meta:Dict[str,Any] | None = None):
  return APIResponse(success=True,message=message,data=data,meta=meta)

def error_response(message:str,status_code:int,errors:Any | None = None,request_id:str | None = None,meta:Dict[str,Any] | None = None):
  content = APIResponse(success=False,message=message,errors=errors,meta={"request_id":request_id} if request_id else None)
  return JSONResponse(status_code=status_code,content=jsonable_encoder(content))