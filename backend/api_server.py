
import os
# ------- Set env defaults BEFORE importing trading_backend --------
os.environ.setdefault("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./trading.db"))
POLY_API_KEY = os.getenv("POLY_API_KEY", "")
ALLOW_ORIGIN = os.getenv("CORS_ORIGIN", "*")

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Now safe to import; trading_backend will read DATABASE_URL we've set
import trading_backend as tb

app = FastAPI(title="IFT401 Trading API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOW_ORIGIN] if ALLOW_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    side: str
    order_type: str = "market"
    price: float | None = None

class SimPriceIn(BaseModel):
    ticker: str
    new_price: float

@app.on_event("startup")
async def _startup():
    await tb.init_db()

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/users")
async def create_user(body: CreateUserIn):
    return await tb.create_user(**body.dict())

@app.get("/cash/{user_id}")
async def get_cash(user_id: int):
    bal = await tb.get_cash_balance(user_id)
    return {"user_id": user_id, "balance": bal}

@app.post("/cash/{user_id}/deposit")
async def deposit(user_id: int, body: AmountIn):
    bal = await tb.deposit_cash(user_id, body.amount)
    return {"user_id": user_id, "balance": bal}

@app.post("/cash/{user_id}/withdraw")
async def withdraw(user_id: int, body: AmountIn):
    bal = await tb.withdraw_cash(user_id, body.amount)
    return {"user_id": user_id, "balance": bal}

@app.post("/stocks")
async def create_stock(body: CreateStockIn):
    return await tb.create_stock(**body.dict())

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
    return await tb.simulate_market_price(body.ticker, body.new_price)

@app.post("/orders")
async def place_order(body: PlaceOrderIn):
    return await tb.place_order(**body.dict())

@app.get("/orders")
async def list_orders(user_id: int | None = None, status: str | None = None):
    return await tb.list_orders(user_id=user_id, status=status)

@app.get("/portfolio/{user_id}")
async def portfolio(user_id: int):
    return await tb.get_portfolio(user_id)

@app.get("/transactions")
async def transactions(user_id: int | None = None):
    return await tb.list_transactions(user_id=user_id)

@app.get("/poly/prev")
async def poly_prev(ticker: str = Query(..., description="Stock ticker symbol")):
    if not POLY_API_KEY:
        raise HTTPException(status_code=500, detail="POLY_API_KEY not configured on server")
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker.upper()}/prev"
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=headers)
    return r.json()
