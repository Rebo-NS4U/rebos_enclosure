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
