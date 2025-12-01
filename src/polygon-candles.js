import {POLY_KEY,POLY_BASE} from '../public/config.js';

export async function getOneMonthCandles(ticker){
  const end=new Date();
  const start=new Date(); start.setDate(start.getDate()-30);
  const fmt=d=>d.toISOString().split('T')[0];
  const url=`${POLY_BASE}/v2/aggs/ticker/${ticker}/range/1/day/${fmt(start)}/${fmt(end)}?apiKey=${POLY_KEY}`;
  const r=await fetch(url); if(!r.ok) return null;
  const data=await r.json(); return data.results||[];
}