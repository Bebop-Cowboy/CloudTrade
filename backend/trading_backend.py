"""
Async MySQL-backed stock trading module.

Usage:
- Set env var DATABASE_URL, e.g.
  export DATABASE_URL="mysql+aiomysql://user:password@localhost:3306/trading_db"

- Call await init_db() once to create tables (or run migrations in production).
- Use the same async API as the in-memory module: create_user, deposit_cash, withdraw_cash,
  create_stock, place_order, cancel_order, get_portfolio, list_transactions, etc.

Notes / decisions:
- Uses SQLAlchemy async ORM with aiomysql driver: "mysql+aiomysql://..."
- Market hours & holidays are stored in a MarketSettings table (single row).
- Orders are executed synchronously when place_order is called or when update_stock_price
  / simulate_market_price / trigger_pending_orders_for_ticker are called.
- Basic validation and cash/share checks are enforced (no shorting allowed).
- This is a straightforward student-friendly persistence layer; in production add migrations,
  connection pool tuning, more robust error handling, and auditing.
"""
from __future__ import annotations
import os
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, date, time as dt_time
import time as time_module

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    Boolean,
    Text,
    select,
    update,
)
import enum
import json

# DATABASE_URL should be like: mysql+aiomysql://user:pass@host:3306/dbname
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:password@127.0.0.1:3306/trading_db")

# SQLAlchemy async engine & session
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# -----------------------
# Models
# -----------------------
class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(200), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Stock(Base):
    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), nullable=False)
    ticker = Column(String(20), nullable=False, unique=True, index=True)
    available_shares = Column(Float, nullable=False, default=0.0)  # shares available
    price = Column(Float, nullable=False, default=0.0)  # current market price
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False, default=0.0)


class CashAccount(Base):
    __tablename__ = "cash_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    balance = Column(Float, nullable=False, default=0.0)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    type = Column(Enum(OrderType), nullable=False)
    limit_price = Column(Float, nullable=True)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)
    fill_price = Column(Float, nullable=True)


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(50), nullable=False)  # deposit, withdraw, buy, sell
    ticker = Column(String(20), nullable=True)
    quantity = Column(Float, nullable=True)
    price = Column(Float, nullable=True)
    amount = Column(Float, nullable=False)  # positive for deposits/proceeds, negative for buys
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    balance_after = Column(Float, nullable=True)


class MarketSettings(Base):
    __tablename__ = "market_settings"
    id = Column(Integer, primary_key=True)
    open_time = Column(String(5), nullable=False, default="09:30")   # "HH:MM"
    close_time = Column(String(5), nullable=False, default="16:00")
    holidays_json = Column(Text, nullable=True)  # JSON array of "YYYY-MM-DD"


# -----------------------
# Helpers
# -----------------------
async def init_db():
    """
    Create database tables. Call once (or use migrations).
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _parse_hm(hm: str) -> dt_time:
    h, m = map(int, hm.split(":"))
    return dt_time(h, m)


async def _get_market_settings(session: AsyncSession) -> MarketSettings:
    res = await session.execute(select(MarketSettings).limit(1))
    ms = res.scalars().first()
    if ms is None:
        ms = MarketSettings(open_time="09:30", close_time="16:00", holidays_json=json.dumps([]))
        session.add(ms)
        await session.flush()
    return ms


async def is_market_open(at_dt: Optional[datetime] = None) -> bool:
    """
    Determine if market is open using MarketSettings stored in DB.
    """
    if at_dt is None:
        at_dt = datetime.utcnow()
    async with AsyncSessionLocal() as session:
        ms = await _get_market_settings(session)
        open_t = _parse_hm(ms.open_time)
        close_t = _parse_hm(ms.close_time)
        holidays = json.loads(ms.holidays_json or "[]")
    d = at_dt.date()
    if d.strftime("%Y-%m-%d") in holidays:
        return False
    if at_dt.weekday() >= 5:
        return False
    t = at_dt.time()
    return open_t <= t < close_t


# -----------------------
# Admin functions
# -----------------------
async def create_stock(company_name: str, ticker: str, total_shares: int, initial_price: float) -> Dict[str, Any]:
    if total_shares < 0:
        raise ValueError("total_shares must be >= 0")
    if initial_price <= 0:
        raise ValueError("initial_price must be > 0")
    ticker = ticker.upper()
    async with AsyncSessionLocal() as session:
        # ensure unique ticker
        res = await session.execute(select(Stock).where(Stock.ticker == ticker))
        if res.scalars().first():
            raise ValueError("ticker already exists")
        stock = Stock(company_name=company_name, ticker=ticker, available_shares=total_shares, price=initial_price)
        session.add(stock)
        await session.commit()
        await session.refresh(stock)
        return {
            "company_name": stock.company_name,
            "ticker": stock.ticker,
            "available_shares": stock.available_shares,
            "price": stock.price,
            "created_at": stock.created_at.isoformat(),
        }


async def update_stock_price(ticker: str, new_price: float) -> Dict[str, Any]:
    ticker = ticker.upper()
    if new_price <= 0:
        raise ValueError("price must be > 0")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock).where(Stock.ticker == ticker))
        stock = res.scalars().first()
        if not stock:
            raise ValueError("unknown ticker")
        stock.price = float(new_price)
        await session.commit()
    # after price update, attempt pending orders
    await trigger_pending_orders_for_ticker(ticker)
    return {"ticker": ticker, "price": new_price}


async def set_market_hours(open_hm: str, close_hm: str) -> None:
    open_t = _parse_hm(open_hm)
    close_t = _parse_hm(close_hm)
    if open_t >= close_t:
        raise ValueError("open must be before close")
    async with AsyncSessionLocal() as session:
        ms = await _get_market_settings(session)
        ms.open_time = open_hm
        ms.close_time = close_hm
        await session.commit()


async def set_holidays(dates: List[str]) -> None:
    # validate dates
    for d in dates:
        datetime.strptime(d, "%Y-%m-%d")
    async with AsyncSessionLocal() as session:
        ms = await _get_market_settings(session)
        ms.holidays_json = json.dumps(dates)
        await session.commit()


# -----------------------
# Customer / trading functions
# -----------------------
async def create_user(full_name: str, username: str, email: str) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        # uniqueness checks
        res = await session.execute(select(User).where((User.username == username) | (User.email == email)))
        if res.scalars().first():
            raise ValueError("username or email already exists")
        user = User(full_name=full_name, username=username, email=email)
        session.add(user)
        await session.flush()
        # create cash account
        cash = CashAccount(user_id=user.id, balance=0.0)
        session.add(cash)
        await session.commit()
        return {"id": user.id, "full_name": user.full_name, "username": user.username, "email": user.email, "created_at": user.created_at.isoformat()}


async def deposit_cash(user_id: int, amount: float) -> float:
    if amount <= 0:
        raise ValueError("deposit must be > 0")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(CashAccount).where(CashAccount.user_id == user_id))
        acc = res.scalars().first()
        if not acc:
            raise ValueError("unknown user")
        acc.balance += float(amount)
        # record transaction
        tx = Transaction(user_id=user_id, kind="deposit", amount=float(amount), balance_after=acc.balance)
        session.add(tx)
        await session.commit()
        return acc.balance


async def withdraw_cash(user_id: int, amount: float) -> float:
    if amount <= 0:
        raise ValueError("withdraw must be > 0")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(CashAccount).where(CashAccount.user_id == user_id))
        acc = res.scalars().first()
        if not acc:
            raise ValueError("unknown user")
        if acc.balance < amount:
            raise ValueError("insufficient cash")
        acc.balance -= float(amount)
        tx = Transaction(user_id=user_id, kind="withdraw", amount=-float(amount), balance_after=acc.balance)
        session.add(tx)
        await session.commit()
        return acc.balance


async def get_cash_balance(user_id: int) -> float:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(CashAccount).where(CashAccount.user_id == user_id))
        acc = res.scalars().first()
        if not acc:
            raise ValueError("unknown user")
        return float(acc.balance)


async def get_portfolio(user_id: int) -> Dict[str, float]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Holding).where(Holding.user_id == user_id))
        holdings = {h.ticker: h.quantity for h in res.scalars().all()}
        return holdings


async def list_transactions(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        if user_id is None:
            res = await session.execute(select(Transaction).order_by(Transaction.timestamp))
            txs = res.scalars().all()
        else:
            res = await session.execute(select(Transaction).where(Transaction.user_id == user_id).order_by(Transaction.timestamp))
            txs = res.scalars().all()
        out = []
        for t in txs:
            out.append({
                "id": t.id,
                "user_id": t.user_id,
                "kind": t.kind,
                "ticker": t.ticker,
                "quantity": t.quantity,
                "price": t.price,
                "amount": t.amount,
                "timestamp": t.timestamp.isoformat(),
                "balance_after": t.balance_after,
            })
        return out


# -----------------------
# Orders and execution
# -----------------------
async def place_order(user_id: int, ticker: str, quantity: float, side: str, order_type: str = "market", price: Optional[float] = None) -> Dict[str, Any]:
    """
    Place an order and attempt immediate execution if possible.
    Returns the order record.
    """
    ticker = ticker.upper()
    side = side.lower()
    order_type = order_type.lower()
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    if order_type not in {"market", "limit"}:
        raise ValueError("order_type must be 'market' or 'limit'")
    if order_type == "limit" and (price is None or price <= 0):
        raise ValueError("limit orders require positive price")
    async with AsyncSessionLocal() as session:
        # user exists?
        res = await session.execute(select(User).where(User.id == user_id))
        user = res.scalars().first()
        if not user:
            raise ValueError("unknown user")
        # stock exists?
        res = await session.execute(select(Stock).where(Stock.ticker == ticker))
        stock = res.scalars().first()
        if not stock:
            raise ValueError("unknown ticker")

        order = Order(user_id=user_id, ticker=ticker, quantity=quantity,
                      side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                      type=OrderType.MARKET if order_type == "market" else OrderType.LIMIT,
                      limit_price=float(price) if price is not None else None,
                      status=OrderStatus.PENDING)
        session.add(order)
        await session.flush()
        order_id = order.id
        await session.commit()

    # attempt execution
    await _attempt_execute(order_id)
    return await get_order(order_id)


async def _attempt_execute(order_id: int) -> None:
    """
    Tries to execute a pending order. Updates DB records atomically where needed.
    """
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Order).where(Order.id == order_id).with_for_update())
        order = res.scalars().first()
        if not order or order.status != OrderStatus.PENDING:
            return

        # check market open
        if not await is_market_open():
            return

        res = await session.execute(select(Stock).where(Stock.ticker == order.ticker).with_for_update())
        stock = res.scalars().first()
        if not stock:
            order.status = OrderStatus.REJECTED
            await session.commit()
            return

        market_price = stock.price
        if market_price is None:
            return

        fill_price = None
        if order.type == OrderType.MARKET:
            fill_price = market_price
        else:
            if order.side == OrderSide.BUY and order.limit_price >= market_price:
                fill_price = order.limit_price
            elif order.side == OrderSide.SELL and order.limit_price <= market_price:
                fill_price = order.limit_price

        if fill_price is None:
            return  # not fillable now

        # Validate and execute
        qty = order.quantity
        if order.side == OrderSide.BUY:
            if stock.available_shares < qty:
                order.status = OrderStatus.REJECTED
                await session.commit()
                return
            res = await session.execute(select(CashAccount).where(CashAccount.user_id == order.user_id).with_for_update())
            acc = res.scalars().first()
            if not acc or acc.balance < qty * fill_price:
                order.status = OrderStatus.REJECTED
                await session.commit()
                return
            # debit cash
            acc.balance -= qty * fill_price
            # decrease available shares
            stock.available_shares -= qty
            # update holdings (upsert)
            res = await session.execute(select(Holding).where(Holding.user_id == order.user_id, Holding.ticker == order.ticker).with_for_update())
            holding = res.scalars().first()
            if holding:
                holding.quantity += qty
            else:
                holding = Holding(user_id=order.user_id, ticker=order.ticker, quantity=qty)
                session.add(holding)
            # transaction
            tx = Transaction(user_id=order.user_id, kind="buy", ticker=order.ticker, quantity=qty, price=fill_price, amount=-(qty * fill_price), balance_after=acc.balance)
            session.add(tx)
        else:  # sell
            res = await session.execute(select(Holding).where(Holding.user_id == order.user_id, Holding.ticker == order.ticker).with_for_update())
            holding = res.scalars().first()
            if not holding or holding.quantity < qty:
                order.status = OrderStatus.REJECTED
                await session.commit()
                return
            # reduce holding
            holding.quantity -= qty
            # increase available shares
            stock.available_shares += qty
            # credit cash
            res = await session.execute(select(CashAccount).where(CashAccount.user_id == order.user_id).with_for_update())
            acc = res.scalars().first()
            if not acc:
                acc = CashAccount(user_id=order.user_id, balance=0.0)
                session.add(acc)
                await session.flush()
            acc.balance += qty * fill_price
            tx = Transaction(user_id=order.user_id, kind="sell", ticker=order.ticker, quantity=qty, price=fill_price, amount=qty * fill_price, balance_after=acc.balance)
            session.add(tx)

        # finalize order
        order.status = OrderStatus.FILLED
        order.filled_at = datetime.utcnow()
        order.fill_price = float(fill_price)
        await session.commit()


async def trigger_pending_orders_for_ticker(ticker: str) -> None:
    ticker = ticker.upper()
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Order).where(Order.ticker == ticker, Order.status == OrderStatus.PENDING))
        ids = [o.id for o in res.scalars().all()]
    for oid in ids:
        await _attempt_execute(oid)


async def trigger_pending_orders() -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Order).where(Order.status == OrderStatus.PENDING))
        ids = [o.id for o in res.scalars().all()]
    for oid in ids:
        await _attempt_execute(oid)


async def cancel_order(order_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Order).where(Order.id == order_id).with_for_update())
        order = res.scalars().first()
        if not order or order.status != OrderStatus.PENDING:
            return False
        order.status = OrderStatus.CANCELLED
        await session.commit()
        return True


async def list_orders(user_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        q = select(Order)
        if user_id is not None:
            q = q.where(Order.user_id == user_id)
        if status is not None:
            q = q.where(Order.status == OrderStatus(status))
        res = await session.execute(q.order_by(Order.created_at))
        out = []
        for o in res.scalars().all():
            out.append({
                "id": o.id,
                "user_id": o.user_id,
                "ticker": o.ticker,
                "quantity": o.quantity,
                "side": o.side.value,
                "type": o.type.value,
                "limit_price": o.limit_price,
                "status": o.status.value,
                "created_at": o.created_at.isoformat(),
                "filled_at": o.filled_at.isoformat() if o.filled_at else None,
                "fill_price": o.fill_price,
            })
        return out


async def get_order(order_id: int) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Order).where(Order.id == order_id))
        o = res.scalars().first()
        if not o:
            return None
        return {
            "id": o.id,
            "user_id": o.user_id,
            "ticker": o.ticker,
            "quantity": o.quantity,
            "side": o.side.value,
            "type": o.type.value,
            "limit_price": o.limit_price,
            "status": o.status.value,
            "created_at": o.created_at.isoformat(),
            "filled_at": o.filled_at.isoformat() if o.filled_at else None,
            "fill_price": o.fill_price,
        }


async def simulate_market_price(ticker: str, new_price: float) -> Dict[str, Any]:
    ticker = ticker.upper()
    if new_price <= 0:
        raise ValueError("price must be > 0")
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock).where(Stock.ticker == ticker))
        stock = res.scalars().first()
        if not stock:
            raise ValueError("unknown ticker")
        stock.price = float(new_price)
        await session.commit()
    await trigger_pending_orders_for_ticker(ticker)
    return {"ticker": ticker, "price": new_price}


async def list_stocks() -> List[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock))
        return [{"company_name": s.company_name, "ticker": s.ticker, "available_shares": s.available_shares, "price": s.price} for s in res.scalars().all()]


async def get_stock(ticker: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Stock).where(Stock.ticker == ticker.upper()))
        s = res.scalars().first()
        if not s:
            return None
        return {"company_name": s.company_name, "ticker": s.ticker, "available_shares": s.available_shares, "price": s.price}


async def reset_state() -> None:
    """
    WARNING: destructive. Drops and recreates all tables.
    Useful for tests/demos only.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


# Quick demo (run with: python -m asyncio trading_system_mysql.py) omitted to keep file focused.