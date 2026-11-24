// Survey coordinates are block corners. The east side follows an older parish road.
function corner(i,j) {
    const east=Math.min(1,Math.max(0,(i-13)/5));
    return [i*40+7*Math.sin(j*.55+i*.22)+east*12*Math.sin(j*.65),
        j*37.5+6*Math.sin(i*.42+j*.14)+east*9*Math.sin(i*.8+j*.48)];
}
function river(y) { return 775+60*Math.sin(y/125+.6)-.10*y; }
function draw(c,w,h) {
    c.save(); c.scale(w/1200,h/750);
    let seed=5318;
    function rand(){ seed=(seed*1664525+1013904223)>>>0; return seed/4294967296; }
    function path(points){c.beginPath();c.moveTo(...points[0]);for(let i=1;i<points.length;i++)c.lineTo(...points[i]);}
    function stroke(points,color,size){path(points);c.strokeStyle=color;c.lineWidth=size;c.stroke();}
    function polygon(points,color){path(points);c.closePath();c.fillStyle=color;c.fill();}
    c.fillStyle="#18262a";c.fillRect(0,0,1200,750);
    const lamps=[];
    for(let j=-1;j<21;j++) for(let i=-1;i<31;i++) {
        const a=corner(i,j),b=corner(i+1,j),d=corner(i,j+1);
        const pos=(u,v)=>[a[0]+(b[0]-a[0])*u+(d[0]-a[0])*v,a[1]+(b[1]-a[1])*u+(d[1]-a[1])*v];
        const yard=j>11&&i<15, villas=i>20,park=(i-24)**2+(j-5)**2<6 || (i-5)**2+(j-14)**2<4;
        if(park){polygon([pos(.08,.08),pos(.92,.08),pos(.92,.92),pos(.08,.92)],"#203c36");
            for(let k=0;k<14;k++){const p=pos(rand(),rand());c.fillStyle=rand()<.5?"#294a40":"#19392f";c.beginPath();c.arc(...p,2+rand()*3,0,6.29);c.fill();}continue;}
        const cols=yard?1:villas?3:2, rows=yard?2:villas?3:2;
        for(let l=0;l<rows;l++)for(let k=0;k<cols;k++){
            if(rand()<.09)continue;
            const u=.12+k*.8/cols,v=.12+l*.8/rows,dx=(.55+.19*rand())/cols,dy=(.49+.23*rand())/rows;
            polygon([pos(u,v),pos(u+dx,v),pos(u+dx,v+dy),pos(u+dx*.4,v+dy),pos(u+dx*.4,v+dy*.8),pos(u,v+dy*.8)],
                ["#394044","#34434a","#354447","#404448","#303c42"][Math.floor(rand()*5)]);
            stroke([pos(u,v),pos(u+dx,v)],"#53595a",.65);
            if(rand()<.28){const p=pos(u+.02,v+.04);c.fillStyle="#9a8060";c.fillRect(...p,2,1);if(Math.abs(p[0]-river(p[1]))>39)lamps.push({x:p[0]*w/1200,y:p[1]*h/750});}
        }
    }
    function street(pts,major){stroke(pts,major?"#172226":"#202b30",major?8:4);stroke(pts,major?"#63615a":"#454e50",major?5:1.8);}
    for(let i=0;i<=30;i++){let pts=[];for(let j=-1;j<=21;j++)pts.push(corner(i,j));street(pts,[4,11,23,28].includes(i));}
    for(let j=0;j<=20;j++){let pts=[];for(let i=-1;i<=31;i++)pts.push(corner(i,j));street(pts,[4,10,16].includes(j));}
    const flow=[];for(let y=-50;y<810;y+=5)flow.push([river(y),y]);
    stroke(flow,"#696659",67);stroke(flow,"#203f45",63);stroke(flow,"#16353e",55);
    for(let k=0;k<420;k++){const y=rand()*750,x=river(y)+(rand()-.5)*47;stroke([[x,y],[x+1,y+3]],"#23434b",.75);}
    for(const j of [4,10,16]){const pts=[];for(let i=15;i<=23;i++)pts.push(corner(i,j));stroke(pts,"#969080",9);street(pts,true);}
    // The Exchange occupies two former market blocks around a glass-roofed hall.
    polygon([[174,218],[244,217],[243,258],[175,258]],"#474b46");
    polygon([[182,225],[233,224],[238,232],[232,248],[183,249],[178,240]],"#64706b");
    for(let x=186;x<231;x+=6)stroke([[x,228],[x-2,245]],"#414e50",2);
    // Long sawtooth sheds back onto a fan of loading tracks.
    for(let row=0;row<3;row++){
        const x=84+row*12,y=496+row*23;
        c.fillStyle="#2d373b";c.fillRect(x-3,y-3,222-row*14,22);
        c.fillStyle="#535451";c.fillRect(x,y,211-row*14,14);
        for(let off=2;off<204-row*14;off+=11)
            stroke([[x+off,y+1],[x+off-2,y+12]],"#39454a",3);
    }
    // Tidal loading fingers and bonded stores at the southeast quay.
    for(let k=0;k<5;k++){
        const y=499+k*14,x=river(y)+36;
        stroke([[x-20,y+3],[x+13,y-3]],"#283237",6);
        stroke([[x-20,y+2],[x+13,y-4]],"#787166",3);
        c.fillStyle="#515959";c.fillRect(x+8,y-6,30+k%2*12,7);
    }
    for(let k=0;k<6;k++)stroke([[95,570+k*5],[300-k*8,570+k*5],[335,590]],"#605953",1.5);
    function label(x,y,s,size,ink,face){c.font=size+"px "+face;c.fillStyle="#17262b";c.fillRect(x-4,y-size+1,c.measureText(s).width+8,size+4);c.fillStyle=ink;c.fillText(s,x,y);}
    label(40,49,"Vesper Reach",32,"#c6c1a9","serif");
    label(42,68,"MUNICIPAL SURVEY  /  NIGHT EDITION",9,"#9aab9f","sans-serif");
    for(const [x,y,s] of [[178,271,"EXCHANGE"],[939,91,"LINDEN HILL"],[96,628,"FOUNDRY YARD"],[930,578,"SALT QUAY"]])label(x,y,s,13,"#b4b8a9","serif");
    label(752,365,"Bell Bridge",10,"#a5b9b5","serif");label(43,717,"N ↑     ├────┤  200 m",11,"#a6b2ad","sans-serif");
    c.restore();return lamps;
}
