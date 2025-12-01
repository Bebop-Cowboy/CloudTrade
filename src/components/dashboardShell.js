export function dashboardShell(c){
return Object.assign(document.createElement('div'),{innerHTML:
`<div class='sidebar glass'>
 <div class='navlink' onclick='location.hash="#/summary"'>Summary</div>
 <div class='navlink' onclick='location.hash="#/trade"'>Trade</div>
 <div class='navlink' onclick='location.hash="#/portfolio"'>Portfolio</div>
 <div class='navlink' onclick='location.hash="#/admin"'>Admin</div>
</div>
<div class='main'>${c}</div>`});}