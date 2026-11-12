export function splashFrame(direction){
 const length=Math.hypot(...direction)||1,d=direction.map(v=>v/length),horizontal=Math.hypot(d[0],d[2]),incidence=Math.min(1,Math.abs(d[1]));
 const tangent=horizontal>1e-6?[d[0]/horizontal,0,d[2]/horizontal]:[1,0,0];
 return {incidence,tangent,side:[-tangent[2],0,tangent[0]],bias:horizontal*1.65,up:.9+incidence*1.8,stretch:1+horizontal*.75};
}
export function splashVelocity(frame,azimuth,speed,jet=0){
 const along=Math.cos(azimuth)*speed+frame.bias,across=Math.sin(azimuth)*speed;
 return [frame.tangent[0]*along+frame.side[0]*across,frame.up+jet,frame.tangent[2]*along+frame.side[2]*across];
}
export function seededRandom(seed){return ()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return ((t^t>>>14)>>>0)/4294967296;};}
export function damageProfile(surface,seed,incidence=1){const rand=seededRandom(seed);return {seed,phase:rand()*Math.PI*2,aspect:surface==='wood'?1.65+rand()*.75: .78+rand()*.5,stretch:1+(1-incidence)*.65,scale:.8+rand()*.45,freshness:.75+rand()*.45,cracks:surface==='wood'?4:5+Math.floor(rand()*5),jaggedness:.10+rand()*.19};}
