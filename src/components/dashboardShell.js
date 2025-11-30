
export function dashboardShell(content){
  const w=document.createElement('div');
  w.innerHTML=`
  <div class='sidebar glass'>
    <div class='navlink' onclick='location.hash="#/summary"'>Summary</div>
    <div class='navlink' onclick='location.hash="#/trade"'>Trade</div>
    <div class='navlink' onclick='location.hash="#/admin"'>Admin</div>
  </div>
  <div class='main'>${content}</div>`;
  return w;
}
