function toggleMobileMenu(){const m=document.getElementById('mobile-menu');if(!m)return;m.classList.toggle('hidden');document.body.style.overflow=m.classList.contains('hidden')?'':'hidden'}
              function showToast(msg, type = 'success') { const t = document.getElementById('toast'); const bg = type === 'error' ? 'rgba(147,0,10,.85)' : type === 'warning' ? 'rgba(120,90,0,.85)' : 'rgba(19,19,23,.9)'; const border = type === 'error' ? 'rgba(255,180,171,.3)' : type === 'warning' ? 'rgba(242,202,80,.4)' : 'rgba(242,202,80,.35)'; const icon = type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'check_circle'; t.innerHTML = `<div class="toast-inner-studio flex items-center gap-2.5 px-5 py-3 rounded-full shadow-2xl" style="background:${bg}; border-color:${border}"><span class="material-symbols-outlined icon-fill" style="font-size:16px;color:#f2ca50">${icon}</span><span class="toast-text-studio">${msg}</span></div>`; t.classList.add('show'); clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 3200) }

const API_BASE = window.API_BASE;
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
    await window.waitForToken();
    const body={text,author:document.getElementById('author-input').value||'LEVI AI',mood:currentStyle,background:document.getElementById('bg-input').value};
    const r=await fetch(`${window.API_BASE}/generate_image`,{method:'POST',body:JSON.stringify(body),headers:{'Content-Type':'application/json'}});
    
    const d=await r.json();
    if(!r.ok){
      showToast(d.error || "Generation failed", "error");
      displayDemo(text);
      return;
    }

    if (d.status === 'queued') {
      showToast("Synthesis started...", "info");
      pollTask(d.task_id, text);
      return; // pollTask handles setLoading(false) indirectly or we need to manage it
    }

    if(d.image_url||d.image_b64){displayImage(d.image_url||d.image_b64,text)}
    else throw new Error('No image in response');
  }catch(e){
    console.error("Synthesize error:", e);
    showToast(e.message || 'Generation error','error');
    displayDemo(text);
  }finally{
    // If queued, we don't want to hide the loader yet as pollTask will manage the UI
    // But synthesize() itself is done. Maybe pollTask should call setLoading(false)
  }
}

function setLoading(on){
  if (on && window.ui && window.ui.showLoader) window.ui.showLoader();
  if (!on && window.ui && window.ui.hideLoader) window.ui.hideLoader();
  document.getElementById('synth-icon').classList.toggle('hidden',on);
  document.getElementById('synth-spinner').classList.toggle('hidden',!on);
  document.getElementById('synth-btn').disabled=on;
  document.getElementById('loading-overlay').classList.toggle('hidden',!on);
  document.getElementById('preview-placeholder').classList.toggle('hidden',on);
  document.getElementById('hud-label').textContent=on?'Synthesizing':'Ready';
}

async function pollTask(id,text){
  let retryCount = 0;
  const maxRetries = 60; 
  let pollInterval = 3000; 

  const poll = async () => {
    try {
      await window.waitForToken();
      const r = await fetch(`${window.API_BASE}/task_status/${id}`);
      const d = await r.json();

      if (d.status === 'completed' && d.result) {
        setLoading(false);
        const res = d.result;
        displayImage(res.url || res.image_b64 || res.image || res, text);
      } else if (d.status === 'failed') {
        setLoading(false);
        showToast('Synthesis failed: ' + (d.error || 'Unknown error'), 'error');
      } else {
        retryCount++;
        if (retryCount >= maxRetries) {
          setLoading(false);
          showToast('Task timeout', 'error');
          return;
        }
        setTimeout(poll, pollInterval);
      }
    } catch (error) {
      console.error("Polling error:", error);
      setTimeout(poll, 5000);
    }
  };

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
async function makeVideo(){
  const text=document.getElementById('wisdom-input').value.trim();
  if(!text){showToast('Enter some wisdom first','error');return}
  showToast('Video generation queued...', 'info');
  try {
    const body={text,author:document.getElementById('author-input').value||'LEVI AI',mood:currentStyle};
    const r=await fetch(`${window.API_BASE}/generate_video`,{method:'POST',body:JSON.stringify(body),headers:{'Content-Type':'application/json'}});
    const d=await r.json();
    if(d.status === 'queued') {
        showToast('Synthesis in progress...', 'info');
        // Video might take longer, but we can poll for it too
        // For now, My Gallery is the intended place to see it, but we can use pollTask if we update it to handle videos
    }
  } catch(e) {
      showToast('Video request failed', 'error');
  }
}
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
