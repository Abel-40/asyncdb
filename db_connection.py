from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker,AsyncSession
from config import settings

engine = create_async_engine(url=settings.DB_URL,echo=True,pool_size=10,max_overflow=5)
AsyncLocalSession = async_sessionmaker(engine,autoflush=False,expire_on_commit=False)
