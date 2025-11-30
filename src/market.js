
import { store } from './utils.js';
if(!store.get('market')) store.set('market',{
  open:'09:30', close:'16:00', holidays:[]
});
export function setMarketHours(open,close,holidays){
  store.set('market',{open,close,holidays});
}
export function isMarketOpen(){
  const m=store.get('market');
  const now=new Date();
  if(now.getDay()==0||now.getDay()==6) return false;
  const today=now.toISOString().split('T')[0];
  if(m.holidays.includes(today)) return false;
  const [oH,oM]=m.open.split(':').map(Number);
  const [cH,cM]=m.close.split(':').map(Number);
  const o=new Date(),c=new Date();
  o.setHours(oH,oM,0,0); c.setHours(cH,cM,0,0);
  return now>=o && now<=c;
}
