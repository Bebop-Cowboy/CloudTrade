
# Quickstart: Minimal Backend Integration

## 1) Install deps
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
pip install fastapi uvicorn httpx
```

## 2) Configure
```bash
cp .env.example .env
# edit .env to set POLY_API_KEY and (optionally) CORS_ORIGIN
export $(grep -v '^#' .env | xargs)  # on Windows, set env vars manually
```

## 3) Run API
```bash
uvicorn api_server:app --reload --port 8000
```

## 4) Wire the SPA (frontend)
- Add this before other scripts in `index.html`:
```html
<script>
  // Point SPA API to your backend
  window.API_BASE = "http://localhost:8000";
  window.POLY_PROXY_BASE = window.API_BASE + "/poly";
</script>
```
- Minimal fetch helper in `utils.js`:
```js
export async function api(path, opts={}){
  const base = window.API_BASE || "";
  const r = await fetch(base + path, { headers: {'Content-Type':'application/json'}, ...opts });
  if(!r.ok){ throw new Error(await r.text()); }
  return r.json();
}
export async function polyPrev(ticker){
  const base = window.POLY_PROXY_BASE || "/poly";
  const r = await fetch(`${base}/prev?ticker=${encodeURIComponent(ticker)}`);
  if(!r.ok){ throw new Error(await r.text()); }
  return r.json();
}
```
- Example usage in `app.js` summary route:
```js
import { api, polyPrev } from "./utils.js";
async function onSummary(){
  const data = await polyPrev("AAPL");
  const r = data.results?.[0];
  document.querySelector("#summary").innerHTML = r ?
    `<div class="card"><h3>AAPL</h3>
     <p>O:${r.o} H:${r.h} L:${r.l} C:${r.c} Vol:${r.v}</p></div>` : "No data";
}
```
## 5) Sample calls (curl)
```bash
curl -X POST http://localhost:8000/users -H 'Content-Type: application/json' \
  -d '{"full_name":"Ada Lovelace","username":"ada","email":"ada@example.com"}'

curl http://localhost:8000/stocks
curl -X POST http://localhost:8000/stocks -H 'Content-Type: application/json' \
  -d '{"company_name":"Apple","ticker":"AAPL","total_shares":1000000,"initial_price":180}'

curl -X POST http://localhost:8000/cash/1/deposit -H 'Content-Type: application/json' -d '{"amount":10000}'
curl -X POST http://localhost:8000/orders -H 'Content-Type: application/json' \
  -d '{"user_id":1,"ticker":"AAPL","quantity":5,"side":"buy"}'
```
