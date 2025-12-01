import {dashboardShell} from './components/dashboardShell.js';
import {getOneMonthCandles} from './polygon-candles.js';
import {drawCandles} from './charts/candlestickChart.js';

const routes={}; const route=(p,v)=>routes[p]=v;

async function render(){
 const h=location.hash.replace('#','')||'/summary';
 const el=document.getElementById('app');
 el.innerHTML=''; el.appendChild(await routes[h]());
}

window.addEventListener('hashchange',render);
window.addEventListener('load',render);

route('/summary', async()=>dashboardShell(`<div class='glass'><h2>Summary</h2></div>`));

route('/portfolio', async ()=>{
 const tickers=['AAPL','MSFT']; // placeholder saved pf
 let out="";
 for(const t of tickers){
   out+=`<div class='glass'><h3>${t}</h3><canvas id='c_${t}' width='600' height='300'></canvas></div>`;
 }
 const shell=dashboardShell(`<h2>Your Portfolio</h2>${out}`);

 setTimeout(async()=>{
   for(const t of tickers){
     const data=await getOneMonthCandles(t);
     const c=document.getElementById('c_'+t);
     if(data) drawCandles(c,data);
   }
 },50);

 return shell;
});

route('/trade',async()=>dashboardShell(`<div class='glass'><h2>Trade</h2></div>`));
route('/admin',async()=>dashboardShell(`<div class='glass'><h2>Admin</h2></div>`));
