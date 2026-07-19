from database import AsyncSessionLocal
from models import User
from sqlalchemy import select, update

async def get_user_balance(telegram_id: int) -> int:
    async with AsyncSessionLocal() as session:
        stmt = select(User.balance).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar() or 0

async def add_balance(telegram_id: int, amount: int):
    async with AsyncSessionLocal() as session:
        stmt = update(User).where(User.telegram_id == telegram_id).values(balance=User.balance + amount)
        await session.execute(stmt)
        await session.commit()

async def deduct_balance(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        user = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user.scalar_one_or_none()
        if not user or user.balance < 1:
            return False
        user.balance -= 1
        await session.commit()
        return True
