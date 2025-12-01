export function drawCandles(canvas,data){
 const ctx=canvas.getContext('2d');
 ctx.clearRect(0,0,canvas.width,canvas.height);

 const prices=data.map(d=>[d.o,d.h,d.l,d.c]).flat();
 const min=Math.min(...prices), max=Math.max(...prices);
 const candleWidth=canvas.width/data.length;

 data.forEach((d,i)=>{
   const x=i*candleWidth + candleWidth*0.1;
   const bodyWidth=candleWidth*0.8;

   const scale=y=>canvas.height - ((y-min)/(max-min))*canvas.height;
   const o=scale(d.o), c=scale(d.c), h=scale(d.h), l=scale(d.l);

   ctx.strokeStyle="#888"; ctx.beginPath(); ctx.moveTo(x+bodyWidth/2,h); ctx.lineTo(x+bodyWidth/2,l); ctx.stroke();

   ctx.fillStyle = d.c>=d.o ? "#2ecc71" : "#e74c3c";
   ctx.fillRect(x, Math.min(o,c), bodyWidth, Math.abs(c-o));
 });
}