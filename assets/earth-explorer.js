export default function({parentElement:root,data,setTriggerValue}) {
  const svg=root.querySelector('svg'), list=root.querySelector('select'), lock=root.querySelector('.lock');
  const state=svg.explorerState ??= {flat:false,rotation:[-55,-18,0],zoom:1,cursor:{lat:0,lon:0},selected:null};
  const ns='http://www.w3.org/2000/svg';
  let projection,path,down=null;
  function position(event) { return new DOMPoint(event.clientX,event.clientY).matrixTransform(svg.getScreenCTM().inverse()); }
  function visible(lon,lat) { return state.flat || d3.geoDistance([lon,lat],[-state.rotation[0],-state.rotation[1]])<Math.PI/2; }
  function draw() {
    const height=state.flat?360:480;
    svg.setAttribute('viewBox',`0 0 720 ${height}`);
    projection=state.flat?d3.geoEquirectangular().scale(720*state.zoom/(2*Math.PI)).translate([360,180]):d3.geoOrthographic().rotate(state.rotation).scale(206*state.zoom).translate([360,240]).clipAngle(90);
    path=d3.geoPath(projection);
    root.querySelector('.sphere').setAttribute('d',path({type:'Sphere'}));
    root.querySelector('.land').setAttribute('d',path(data.land));
    root.querySelector('.graticule').setAttribute('d',path(d3.geoGraticule10()));
    root.querySelector('.shade').setAttribute('d',state.flat?'':path({type:'Sphere'}));
    root.querySelector('.globe-mode').setAttribute('aria-pressed',!state.flat);
    root.querySelector('.flat-mode').setAttribute('aria-pressed',state.flat);
    root.querySelector('.map-help').textContent=state.flat?'Click to choose · arrows to refine':'Drag to turn · click to choose';
    for(const pilot of data.pilots) {
      const marker=root.querySelector(`[data-pilot="${pilot.id}"]`),p=projection([pilot.lon,pilot.lat]);
      marker.setAttribute('transform',`translate(${p[0]} ${p[1]})`);
      marker.style.display=visible(pilot.lon,pilot.lat)?'':'none';
    }
    if(state.selected) { const p=projection([state.selected.lon,state.selected.lat]); lock.setAttribute('transform',`translate(${p[0]} ${p[1]})`); lock.setAttribute('visibility',visible(state.selected.lon,state.selected.lat)?'visible':'hidden'); }
  }
  function select(lat,lon,pilot,emit=true) {
    const point={lat:+lat.toFixed(4),lon:+lon.toFixed(4),pilot:pilot?.id??null};
    state.selected=state.cursor=point;
    if(pilot&&!state.flat) state.rotation=[-lon,-lat,0];
    list.value=point.pilot??'';
    root.querySelector('output').textContent=(pilot?pilot.short+' pilot':'Climate location')+' · '+Math.abs(lat).toFixed(4)+'°'+(lat<0?'S':'N')+'  '+Math.abs(lon).toFixed(4)+'°'+(lon<0?'W':'E');
    const button=root.querySelector('.use'); button.disabled=false;
    button.textContent=pilot?'Open farm profile':'Explore this location';
    button.onclick=()=>setTriggerValue('chosen',point);
    draw();
    if(emit) { for(const [selector,cls] of [['.reticle','scan'],['.pulse','active']]) { const node=root.querySelector(selector);node.classList.remove(cls);node.getBoundingClientRect();node.classList.add(cls); } setTriggerValue('inspected',point); }
  }
  list.replaceChildren(new Option('Select a regional planner',''));
  root.querySelector('.pilots').replaceChildren();
  for(const pilot of data.pilots) {
    list.add(new Option(pilot.label,pilot.id));
    const group=document.createElementNS(ns,'g');
    for(const [k,v] of Object.entries({'data-pilot':pilot.id,tabindex:0,role:'button','aria-label':pilot.label})) group.setAttribute(k,v);
    group.innerHTML='<circle r="12" fill="transparent"/><circle class="dot" r="5" fill="#b9dca0" stroke="#f1fff5" stroke-width="1.5"/><text class="name" x="9" y="3"></text>';
    group.querySelector('text').textContent=pilot.short;
    group.onclick=e=>{e.stopPropagation();select(pilot.lat,pilot.lon,pilot);};
    group.onkeydown=e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();e.stopPropagation();select(pilot.lat,pilot.lon,pilot);}};
    root.querySelector('.pilots').append(group);
  }
  list.onchange=()=>{const p=data.pilots.find(p=>p.id===list.value);if(p)select(p.lat,p.lon,p);};
  root.querySelector('.globe-mode').onclick=()=>{state.flat=false;draw();};
  root.querySelector('.flat-mode').onclick=()=>{state.flat=true;draw();};
  function zoom(factor) { state.zoom=Math.max(.75,Math.min(3,state.zoom*factor));draw(); }
  root.querySelector('.zoomIn').onclick=()=>zoom(1.25);
  root.querySelector('.zoomOut').onclick=()=>zoom(.8);
  root.querySelector('.reset').onclick=()=>{state.rotation=[-55,-18,0];state.zoom=1;draw();};
  root.querySelector('.centre').onclick=()=>{if(state.selected){state.flat=false;state.rotation=[-state.selected.lon,-state.selected.lat,0];draw();}};
  svg.onwheel=e=>{e.preventDefault();state.zoom=Math.max(.75,Math.min(3,state.zoom*(e.deltaY<0?1.08:.92)));draw();};
  svg.onpointerdown=e=>{if(e.target.closest('[data-pilot]'))return;down={x:e.clientX,y:e.clientY,rotation:[...state.rotation],moved:false};svg.setPointerCapture(e.pointerId);};
  svg.onpointermove=e=>{if(!down||state.flat)return;const dx=e.clientX-down.x,dy=e.clientY-down.y;if(Math.hypot(dx,dy)>5)down.moved=true;state.rotation=[down.rotation[0]+dx*.35/state.zoom,Math.max(-85,Math.min(85,down.rotation[1]-dy*.35/state.zoom)),0];draw();};
  svg.onpointerup=e=>{if(!down)return;const dragged=down.moved;down=null;if(dragged)return;const p=position(e);if(!state.flat&&Math.hypot(p.x-360,p.y-240)>projection.scale())return;const ll=projection.invert([p.x,p.y]);if(ll&&ll.every(Number.isFinite)&&Math.abs(ll[1])<=90)select(ll[1],Math.max(-180,Math.min(180,ll[0])),null);};
  svg.onpointercancel=()=>{down=null;};
  svg.onkeydown=e=>{if(e.target!==svg)return;if(e.key==='Enter'){e.preventDefault();select(state.cursor.lat,state.cursor.lon,null);return;}if(!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))return;e.preventDefault();const step=1/state.zoom;const lat=Math.max(-90,Math.min(90,state.cursor.lat+(e.key==='ArrowUp'?step:e.key==='ArrowDown'?-step:0)));const lon=((state.cursor.lon+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0)+540)%360)-180;state.rotation=[-lon,-lat,0];select(lat,lon,null,false);};
  const incoming=JSON.stringify(data.selected??null);
  const changed=state.lastIncoming!==incoming;
  state.lastIncoming=incoming;
  const saved=changed?data.selected:state.selected;
  if(saved)select(saved.lat,saved.lon,data.pilots.find(p=>p.id===saved.pilot),false);else draw();
}
