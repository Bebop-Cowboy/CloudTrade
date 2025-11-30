
import { store } from './utils.js';

if(!store.get('stocks')) store.set('stocks',{});

export function createStock(company,ticker,volume,price){
  const s=store.get('stocks');
  s[ticker.toUpperCase()]={company,ticker:ticker.toUpperCase(),
    volume:+volume,price:+price,open:+price,high:+price,low:+price};
  store.set('stocks',s);
}
export function listStocks(){ return Object.values(store.get('stocks')||{}); }
export function getStock(t){ return store.get('stocks')[t.toUpperCase()]||null; }
