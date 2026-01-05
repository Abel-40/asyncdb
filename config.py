from pydantic_settings import BaseSettings

class Settings(BaseSettings):
  DB_URL:str
  
  class config:
    env_file = ".env"
    

settings = Settings()