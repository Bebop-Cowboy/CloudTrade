export const $=(s,r=document)=>r.querySelector(s);
export const el=(t,a={},h='')=>Object.assign(document.createElement(t),a,h?{innerHTML:h}:{});
export const store={get:k=>JSON.parse(localStorage.getItem(k)||'null'),
set:(k,v)=>localStorage.setItem(k,JSON.stringify(v))};