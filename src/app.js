
import { el, $, store } from './utils.js';
import { dashboardShell } from './components/dashboardShell.js';
import { listStocks, getStock, createStock } from './stocks.js';
import { isMarketOpen, setMarketHours } from './market.js';

const routes={};
function route(p,v){routes[p]=v;}

async function render(){
  const hash=location.hash.replace('#','')||'/login';
  const view=routes[hash]||routes['/login'];
  const mount=document.querySelector('#app');
  mount.innerHTML='';
  mount.appendChild(await view());
}
window.addEventListener('hashchange',render);
window.addEventListener('load',render);

route('/login',async()=>{
  const w=el('div',{className:'main glass'});
  w.innerHTML=`<h2>Login</h2>
  <input id='lu' placeholder='Username'>
  <input id='lp' type='password' placeholder='Password'>
  <button id='go'>Login</button>`;
  w.querySelector('#go').onclick=()=>location.hash='/summary';
  return w;
});

route('/signup',async()=>{
  const w=el('div',{className:'main glass'});
  w.innerHTML=`<h2>Create Account</h2>
  <input id='sn' placeholder='Name'>
  <input id='su' placeholder='Username'>
  <input id='sp' type='password' placeholder='Password'>
  <button id='sg'>Create</button>`;
  w.querySelector('#sg').onclick=()=>{
    store.set('name',$('#sn',w).value);
    location.hash='/summary';
  };
  return w;
});

route('/summary',async()=>{
  const rows=listStocks().map(s=>`
  <tr>
    <td>${s.company}</td>
    <td>${s.ticker}</td>
    <td>$${s.price}</td>
    <td>${s.volume}</td>
    <td>$${(s.price*s.volume).toFixed(2)}</td>
  </tr>`).join('');
  return dashboardShell(`
  <div class='glass'>
    <h2>Stocks</h2>
    <table>
    <thead><tr><th>Company</th><th>Ticker</th><th>Price</th><th>Volume</th><th>Market Cap</th></tr></thead>
    <tbody>${rows||'<tr><td colspan=5>No stocks</td></tr>'}</tbody>
    </table>
  </div>`);
});

route('/trade',async()=>{
  const html=`
  <div class='glass'>
    <h2>Trade</h2>
    <input id='ts' placeholder='Ticker'>
    <button id='sb'>Search</button>
    <div id='res'></div>
  </div>`;
  const shell=dashboardShell(html);
  shell.querySelector('#sb').onclick=()=>{
    const t=shell.querySelector('#ts').value.toUpperCase();
    const s=getStock(t);
    if(!s){$('#res',shell).innerHTML='Not found'; return;}
    $('#res',shell).innerHTML=`
      <p>${s.company} (${s.ticker})</p>
      <p>Price: $${s.price}</p>
      <button id='buy'>Buy</button>`;
    shell.querySelector('#buy').onclick=()=>{
      if(!isMarketOpen()) alert('Market Closed');
      else alert('Trade Executed');
    };
  };
  return shell;
});

route('/admin',async()=>{
  const html=`
  <div class='glass'>
    <h2>Admin</h2>
    <input id='co' placeholder='Company'>
    <input id='ti' placeholder='Ticker'>
    <input id='vo' placeholder='Volume'>
    <input id='pr' placeholder='Price'>
    <button id='cs'>Create Stock</button>
    <h3>Market Schedule</h3>
    <input id='mo' placeholder='09:30'>
    <input id='mc' placeholder='16:00'>
    <input id='mh' placeholder='YYYY-MM-DD,YYYY-MM-DD'>
    <button id='ms'>Save Market</button>
  </div>`;
  const shell=dashboardShell(html);
  shell.querySelector('#cs').onclick=()=>{
    createStock($('#co',shell).value,$('#ti',shell).value,$('#vo',shell).value,$('#pr',shell).value);
    alert("Created");
  };
  shell.querySelector('#ms').onclick=()=>{
    setMarketHours($('#mo',shell).value,$('#mc',shell).value,$('#mh',shell).value.split(','));
    alert("Saved");
  };
  return shell;
});
