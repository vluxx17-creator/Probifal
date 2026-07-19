from sqlalchemy import Column, Integer, BigInteger, String, DateTime, JSON, Boolean, Text
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(64))
    last_name = Column(String(64), nullable=True)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_admin = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    balance = Column(Integer, default=0)
    free_requests = Column(JSON, default={
        "phone": 2, "ip": 2, "address": 2, "vk": 2
    })

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount_requests = Column(Integer)
    price_stars = Column(Integer)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="completed")

class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    request_type = Column(String(20), nullable=False)
    input_data = Column(Text)
    response_summary = Column(JSON)
    ip_address = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class IpLog(Base):
    __tablename__ = "ip_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    ip = Column(String(45))
    timestamp = Column(DateTime, default=datetime.utcnow)
