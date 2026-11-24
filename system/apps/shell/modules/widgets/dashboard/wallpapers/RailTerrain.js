// Plot elevation contours from a fixed field so the survey does not shift on workspace changes.
function elevation(x, y) {
    const u=x+.08*Math.sin(y*12+x*3)+.025*Math.sin(y*29-x*8);
    const v=y+.07*Math.sin(x*10-y*2)+.017*Math.cos(x*27+y*6);
    function hill(cx,cy,rx,ry) {
        return Math.exp(-(((u-cx)/rx)**2 + ((v-cy)/ry)**2));
    }
    return hill(.03,.22,.24,.22) + .9*hill(.88,.85,.31,.22)
        + .56*hill(.72,.02,.22,.13) + .28*hill(.22,.94,.2,.13);
}

function draw(c,w,h) {
    const step=9, cols=Math.ceil(w/step)+1, rows=Math.ceil(h/step)+1;
    const field=new Float32Array(rows*cols);
    for (let j=0;j<rows;j++) for (let i=0;i<cols;i++)
        field[j*cols+i]=elevation(i*step/w,j*step/h);
    for (let level=1;level<=28;level++) {
        const threshold=level/30;
        c.strokeStyle=level%5===0 ? "#343434" : "#191919";
        c.lineWidth=level%5===0 ? 1 : .8;
        c.beginPath();
        for (let j=0;j<rows-1;j++) for (let i=0;i<cols-1;i++) {
            const k=j*cols+i, a=field[k], b=field[k+1], d=field[k+cols], e=field[k+cols+1];
            if (threshold<Math.min(a,b,d,e) || threshold>Math.max(a,b,d,e)) continue;
            let first=true;
            function cross(x,y) {
                if (first) c.moveTo(x*step,y*step); else c.lineTo(x*step,y*step);
                first=!first;
            }
            if ((a<threshold)!==(b<threshold)) cross(i+(threshold-a)/(b-a),j);
            if ((b<threshold)!==(e<threshold)) cross(i+1,j+(threshold-b)/(e-b));
            if ((e<threshold)!==(d<threshold)) cross(i+(threshold-d)/(e-d),j+1);
            if ((d<threshold)!==(a<threshold)) cross(i,j+(threshold-a)/(d-a));
        }
        c.stroke();
    }
}

// A river with two built-up banks, drawn in local survey coordinates.
function riverY(x, h) {
    return h*(.14*Math.sin(x/h*4.3)+.05*Math.sin(x/h*8.1));
}

function drawDistrict(c,w,h) {
    const lights=[];
    if (w<=0 || h<=0) return lights;
    const angle=-.34, cos=Math.cos(angle), sin=Math.sin(angle);
    const extent=Math.hypot(w,h)*.55;
    const scale=Math.min(w,h)/760, quay=10*scale;
    c.save();
    c.translate(w*.50,h*.49);
    c.rotate(angle);
    c.beginPath();
    for (let x=-extent;x<=extent;x+=4) {
        const y=riverY(x,h);
        if (x===-extent) c.moveTo(x,y); else c.lineTo(x,y);
    }
    for (const [width,color] of [[quay*2+3,"#565656"],[quay*2,"#070707"]]) {
        c.lineWidth=width; c.strokeStyle=color; c.stroke();
    }
    const pitch=18*scale;
    for (let col=-Math.ceil(extent/pitch);col<=extent/pitch;col++) {
        const x=col*pitch, bank=riverY(x,h);
        for (let row=-7;row<=7;row++) {
            const y=row*pitch;
            const seed=Math.abs(Math.sin(col*127.1+row*311.7)*43758.5453)%1;
            const along=Math.sin(x/h*7+1.3*Math.sign(y-bank));
            const distance=Math.abs(y-bank);
            if (distance<quay+pitch*1.35 || distance>pitch*(3.8+3*along) || seed<.14) continue;
            const bw=pitch*(.38+seed*.43), bh=pitch*(.30+(1-seed)*.43);
            c.fillStyle=seed>.70 ? "#252525" : "#171717";
            c.fillRect(x,y,bw,bh);
            c.fillStyle="#363636"; c.fillRect(x,y,bw,scale);
            c.fillStyle="#555555";
            for (let k=2*scale;k<bw-scale;k+=4*scale)
                c.fillRect(x+k,y+bh-2*scale,scale,scale);
            const lx=x+bw/2, ly=y+bh/2;
            lights.push({x:w*.50+lx*cos-ly*sin,y:h*.49+lx*sin+ly*cos});
        }
    }
    c.restore();
    return lights;
}

function illuminate(c,lights,x,y,radius,strength,ring) {
    c.save();
    c.fillStyle="#e0e0e0";
    for (const light of lights) {
        const distance=Math.hypot(light.x-x,light.y-y);
        const weight=ring ? 1-Math.abs(distance-radius)/30 : 1-distance/radius;
        if (weight<=0) continue;
        c.globalAlpha=strength*weight;
        c.fillRect(light.x-2,light.y-1,4,2);
        c.globalAlpha*=.18;
        c.fillRect(light.x-5,light.y-3,10,6);
    }
    c.restore();
}
