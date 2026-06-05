from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.settings import global_settings

engine = create_async_engine(
    global_settings.mysql.url,
    pool_size=10,
    max_overflow=20,
)

async_session_local = async_sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

# 异步获取数据库（连接在 lifespan 启动时通过 health_check 验证）
async def get_db():
    async with async_session_local() as session:
        try:
            yield session
        finally:
            await session.close()

