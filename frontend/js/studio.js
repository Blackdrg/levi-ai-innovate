function toggleMobileMenu(){const m=document.getElementById('mobile-menu');if(!m)return;m.classList.toggle('hidden');document.body.style.overflow=m.classList.contains('hidden')?'':'hidden'}
              function showToast(msg, type = 'success') { const t = document.getElementById('toast'); const bg = type === 'error' ? 'rgba(147,0,10,.85)' : type === 'warning' ? 'rgba(120,90,0,.85)' : 'rgba(19,19,23,.9)'; const border = type === 'error' ? 'rgba(255,180,171,.3)' : type === 'warning' ? 'rgba(242,202,80,.4)' : 'rgba(242,202,80,.35)'; const icon = type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'check_circle'; t.innerHTML = `<div class="toast-inner-studio flex items-center gap-2.5 px-5 py-3 rounded-full shadow-2xl" style="background:${bg}; border-color:${border}"><span class="material-symbols-outlined icon-fill" style="font-size:16px;color:#f2ca50">${icon}</span><span class="toast-text-studio">${msg}</span></div>`; t.classList.add('show'); clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 3200) }

  const API_BASE = (['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(location.hostname)) ? `http://${location.hostname}:8000` : location.origin + '/api';
let currentStyle='philosophical';let currentImage=null;
const insights={philosophical:{text:'prioritize ethereal lighting, high-contrast obsidian shadows, and golden particle dispersion.',stability:67},zen:{text:'evoke bamboo mist, still water reflections, and morning light through ancient forests.',stability:82},cyberpunk:{text:'generate neon-soaked cityscapes, rain-slicked streets, and holographic overlays.',stability:74},futuristic:{text:'render clean white surfaces, cosmic voids, and geometric precision with bioluminescent accents.',stability:91},stoic:{text:'depict marble columns, dawn light, classical architecture — austere and powerful.',stability:88},melancholic:{text:'create rain-washed cobblestones, blue hour, soft bokeh with poetic melancholy.',stability:79}};

function updateChar(el){const n=el.value.length;document.getElementById('char-count').textContent=n;const cc=document.getElementById('char-count');cc.style.color=n>260?'#f87171':n>200?'#f2ca50':''}

function setStyle(btn,style){
  document.querySelectorAll('.style-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');currentStyle=style;
  const info=insights[style]||insights.philosophical;
  const styleName=style.charAt(0).toUpperCase()+style.slice(1);
  document.getElementById('insight-style').textContent=styleName;
  document.getElementById('insight-text').innerHTML=`Synthesizing with <span class="text-primary italic" id="insight-style">${styleName}</span> style will ${info.text}`;
  document.getElementById('stability-bar').style.width=info.stability+'%';
  document.getElementById('stability-val').textContent=info.stability+'%';
}

function prefill(text,author,style){
  document.getElementById('wisdom-input').value=text;updateChar(document.getElementById('wisdom-input'));
  document.getElementById('author-input').value=author;
  const btn=document.querySelector(`.style-btn[onclick*="${style}"]`);
  if(btn)setStyle(btn,style);
  showToast('Prefilled: '+author);
}

window.prefill=prefill;

async function synthesize(){
  const text=document.getElementById('wisdom-input').value.trim();
  if(!text){showToast('Enter some wisdom first','error');return}
  setLoading(true);
  try{
    const token=localStorage.getItem('levi_token');
    const headers={'Content-Type':'application/json'};if(token)headers['Authorization']='Bearer '+token;
    const body={text,author:document.getElementById('author-input').value||'LEVI AI',mood:currentStyle,background:document.getElementById('bg-input').value};
    const r=await fetch(API_BASE+'/generate_image',{method:'POST',headers,body:JSON.stringify(body)});
    if(!r.ok)throw new Error('HTTP '+r.status);
    const d=await r.json();
    if(d.task_id){setLoading(false);showToast('Synthesis queued — generating…');pollTask(d.task_id,text);return}
    if(d.image_url||d.image_b64){displayImage(d.image_url||d.image_b64,text)}
    else throw new Error('No image in response');
  }catch(e){
    showToast('Showing demo preview (backend offline)','warning');
    displayDemo(document.getElementById('wisdom-input').value.trim());
  }finally{setLoading(false)}
}

function setLoading(on){
  document.getElementById('synth-icon').classList.toggle('hidden',on);
  document.getElementById('synth-spinner').classList.toggle('hidden',!on);
  document.getElementById('synth-btn').disabled=on;
  document.getElementById('loading-overlay').classList.toggle('hidden',!on);
  document.getElementById('preview-placeholder').classList.toggle('hidden',on);
  document.getElementById('hud-label').textContent=on?'Synthesizing':'Ready';
}

async function pollTask(id,text){
  let tries=0;
  const poll=async()=>{
    if(tries++>40){showToast('Task timeout','error');return}
    try{
      const r=await fetch(API_BASE+'/task_status/'+id);
      const d=await r.json();
      if(d.status==='completed'&&d.result){displayImage(d.result.url||d.result.image_b64||d.result,text);document.getElementById('loading-overlay').classList.add('hidden')}
      else if(d.status==='failed'){showToast('Synthesis failed','error');document.getElementById('loading-overlay').classList.add('hidden')}
      else setTimeout(poll,2000);
    }catch{setTimeout(poll,2500)}
  };
  document.getElementById('loading-overlay').classList.remove('hidden');
  poll();
}

function displayImage(src,text){
  currentImage=src;
  const img=document.getElementById('preview-img');
  img.src=src;img.onload=()=>{img.classList.remove('opacity-0')};
  document.getElementById('preview-container').classList.remove('hidden');
  document.getElementById('preview-placeholder').classList.add('hidden');
  document.getElementById('preview-title').textContent=text.length>42?text.slice(0,42)+'…':text;
  document.getElementById('preview-bottom-overlay').style.opacity='1';
  document.getElementById('video-btn').disabled=false;
  addThumb(src);showToast('Masterpiece rendered ✦');
}

function displayDemo(text){
  const cv=document.createElement('canvas');cv.width=512;cv.height=512;
  const ctx=cv.getContext('2d');
  const palettes={philosophical:['#0a0a18','#1a1040'],zen:['#081210','#0f2820'],cyberpunk:['#0a0018','#200040'],futuristic:['#080c18','#0c1e38'],stoic:['#0e0c0a','#20201a'],melancholic:['#080c14','#0c1828']};
  const p=palettes[currentStyle]||palettes.philosophical;
  const g=ctx.createLinearGradient(0,0,512,512);g.addColorStop(0,p[0]);g.addColorStop(1,p[1]);
  ctx.fillStyle=g;ctx.fillRect(0,0,512,512);
  ctx.fillStyle='rgba(242,202,80,.06)';ctx.fillRect(0,0,512,512);
  ctx.strokeStyle='rgba(242,202,80,.15)';ctx.lineWidth=1;ctx.strokeRect(16,16,480,480);
  ctx.fillStyle='rgba(242,202,80,.6)';ctx.font='italic 18px Newsreader,serif';ctx.textAlign='center';
  const words=text.split(' ');let lines=[],line='';
  for(const w of words){const t=line+(line?' ':'')+w;if(ctx.measureText(t).width>420){lines.push(line);line=w}else line=t}
  lines.push(line);
  const startY=256-(lines.length*28)/2;
  lines.forEach((l,i)=>ctx.fillText(l,256,startY+i*28));
  displayImage(cv.toDataURL(),text);
}

function addThumb(src){
  const strip=document.getElementById('thumb-strip');
  const newBtn=strip.querySelector('button');
  const div=document.createElement('div');
  div.className='thumb selected flex-shrink-0 w-24 h-24 rounded-2xl overflow-hidden border-2';
  div.onclick=()=>{document.getElementById('preview-img').src=src;document.getElementById('preview-container').classList.remove('hidden');document.querySelectorAll('.thumb').forEach(t=>t.classList.remove('selected'));div.classList.add('selected')};
  div.innerHTML=`<img src="${src}" class="w-full h-full object-cover"/>`;
  strip.insertBefore(div,newBtn);
  document.querySelectorAll('.thumb').forEach(t=>t.classList.remove('selected'));
  div.classList.add('selected');
}

function downloadImg(){
  if(!currentImage)return;
  const a=document.createElement('a');a.href=currentImage;a.download='levi-synthesis-'+Date.now()+'.png';a.click();showToast('Downloading…');
}
function shareImg(){
  const t=document.getElementById('wisdom-input').value;
  if(navigator.share)navigator.share({title:'LEVI AI Wisdom',text:t,url:location.href});
  else{navigator.clipboard.writeText(t);showToast('Quote copied to clipboard')}
}
function regenerate(){if(document.getElementById('wisdom-input').value.trim())synthesize()}
function makeVideo(){showToast('Video generation queued — check My Gallery')}
function newCanvas(){
  currentImage=null;
  document.getElementById('preview-container').classList.add('hidden');
  document.getElementById('preview-placeholder').classList.remove('hidden');
  document.getElementById('preview-bottom-overlay').style.opacity='';
  document.getElementById('wisdom-input').value='';document.getElementById('author-input').value='';
  updateChar(document.getElementById('wisdom-input'));
  document.getElementById('video-btn').disabled=true;
  document.getElementById('hud-label').textContent='Awaiting';
}

// Auth
const u=localStorage.getItem('levi_user');
if(u){try{const o=JSON.parse(u);document.getElementById('user-name').textContent=o.username||'Seeker';document.getElementById('user-avatar').textContent=(o.username||'S').charAt(0).toUpperCase();document.getElementById('nav-auth-btn').textContent=o.username||'Account';document.getElementById('nav-auth-btn').onclick=()=>{window.location.href='my-gallery.html'};document.querySelectorAll('[data-credits]').forEach(el=>el.textContent=(o.credits||0)+' credits')}catch{}}
