
import os
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Import the provided async trading backend (SQLAlchemy models & functions)
import trading_backend as tb

# ----------- Config -----------
# Simplest: default to SQLite file (no MySQL needed). Override via env var if desired.
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db"))
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
ALLOW_ORIGIN = os.getenv("CORS_ORIGIN", "*")

app = FastAPI(title="IFT401 Trading API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOW_ORIGIN] if ALLOW_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------- Models -----------
class CreateUserIn(BaseModel):
    full_name: str
    username: str
    email: str

class AmountIn(BaseModel):
    amount: float

class CreateStockIn(BaseModel):
    company_name: str
    ticker: str
    total_shares: int
    initial_price: float

class PlaceOrderIn(BaseModel):
    user_id: int
    ticker: str
    quantity: float
    side: str  # "buy" | "sell"
    order_type: Optional[str] = "market"  # "market" | "limit"
    price: Optional[float] = None

class SimPriceIn(BaseModel):
    ticker: str
    new_price: float

# ----------- Startup -----------
@app.on_event("startup")
async def _startup():
    # Create tables if they don't exist (idempotent)
    await tb.init_db()

@app.get("/health")
async def health():
    return {"ok": True}

# ----------- Users / Cash -----------
@app.post("/users")
async def create_user(body: CreateUserIn):
    try:
        return await tb.create_user(**body.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/cash/{user_id}")
async def get_cash(user_id: int):
    try:
        bal = await tb.get_cash_balance(user_id)
        return {"user_id": user_id, "balance": bal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/cash/{user_id}/deposit")
async def deposit(user_id: int, body: AmountIn):
    try:
        bal = await tb.deposit_cash(user_id, body.amount)
        return {"user_id": user_id, "balance": bal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/cash/{user_id}/withdraw")
async def withdraw(user_id: int, body: AmountIn):
    try:
        bal = await tb.withdraw_cash(user_id, body.amount)
        return {"user_id": user_id, "balance": bal}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------- Stocks -----------
@app.post("/stocks")
async def create_stock(body: CreateStockIn):
    try:
        return await tb.create_stock(**body.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/stocks")
async def list_stocks():
    return await tb.list_stocks()

@app.get("/stocks/{ticker}")
async def get_stock(ticker: str):
    s = await tb.get_stock(ticker)
    if not s:
        raise HTTPException(status_code=404, detail="unknown ticker")
    return s

@app.post("/stocks/sim-price")
async def simulate_price(body: SimPriceIn):
    try:
        return await tb.simulate_market_price(body.ticker, body.new_price)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------- Orders -----------
@app.post("/orders")
async def place_order(body: PlaceOrderIn):
    try:
        return await tb.place_order(**body.dict())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders")
async def list_orders(user_id: Optional[int] = None, status: Optional[str] = None):
    try:
        return await tb.list_orders(user_id=user_id, status=status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/portfolio/{user_id}")
async def portfolio(user_id: int):
    try:
        return await tb.get_portfolio(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/transactions")
async def transactions(user_id: Optional[int] = None):
    try:
        return await tb.list_transactions(user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------- Polygon proxy (prev day OHLC) -----------
@app.get("/poly/prev")
async def poly_prev(ticker: str = Query(..., description="Stock ticker symbol")):
    if not POLY_API_KEY:
        raise HTTPException(status_code=500, detail="POLY_API_KEY not configured on server")
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker.upper()}/prev"
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=headers)
    return r.json()
