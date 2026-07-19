from database import AsyncSessionLocal
from models import User
from sqlalchemy import select, update

async def get_free_requests(telegram_id: int, req_type: str) -> int:
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            return 0
        return user.free_requests.get(req_type, 0)

async def use_free_request(telegram_id: int, req_type: str) -> bool:
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user:
            return False
        current = user.free_requests.get(req_type, 0)
        if current > 0:
            user.free_requests[req_type] = current - 1
            await session.commit()
            return True
        return False
