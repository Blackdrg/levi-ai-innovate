// Add a robust showToast fallback for early-load calls
function showToast(msg, type = 'success') {
    if (window.ui && window.ui.showToast) { window.ui.showToast(msg, type); return; }
    if (window.LEVI && window.LEVI.toast) { window.LEVI.toast.show(msg, type); return; }
    const t = document.getElementById('toast');
    if (!t) return;
    t.innerHTML = `<div style="background:rgba(19,19,23,.92);border:.5px solid rgba(242,202,80,.35);backdrop-filter:blur(20px);padding:10px 20px;border-radius:9999px;color:#e5e1e7;font-size:12px;font-weight:600">${msg}</div>`;
    t.classList.add('show');
    clearTimeout(t._t);
    t._t = setTimeout(() => t.classList.remove('show'), 3200);
}

// Fixed API_BASE race condition with a lazy-eval getter
function getApiBase() {
    return window.API_BASE || (
        window.location.hostname === 'localhost'
            ? 'http://localhost:8000/api/v1'
            : `${window.location.origin}/api/v1`
    );
}

let currentStyle='philosophical';let currentImage=null;
let isGenerating = false;
const insights={philosophical:{text:'prioritize ethereal lighting, high-contrast obsidian shadows, and golden particle dispersion.',stability:67},zen:{text:'evoke bamboo mist, still water reflections, and morning light through ancient forests.',stability:82},cyberpunk:{text:'generate neon-soaked cityscapes, rain-slicked streets, and holographic overlays.',stability:74},futuristic:{text:'render clean white surfaces, cosmic voids, and geometric precision with bioluminescent accents.',stability:91},stoic:{text:'depict marble columns, dawn light, classical architecture — austere and powerful.',stability:88},melancholic:{text:'create rain-washed cobblestones, blue hour, soft bokeh with poetic melancholy.',stability:79}};

// 2. Robust Retry + Timeout Utility
async function fetchWithRetry(url, options, retries = 2, timeout = 25000) {
  for (let i = 0; i <= retries; i++) {
    try {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), timeout);
      const res = await fetch(url, { ...options, signal: controller.signal });
      clearTimeout(id);
      if (!res.ok) {
        if (res.status === 429) throw new Error("Too many requests. Please wait.");
        throw new Error("API error: " + res.status);
      }
      return await res.json();
    } catch (err) {
      if (i === retries) throw err;
      console.warn(`[LEVI] Retry ${i+1}/${retries} for ${url}`);
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}

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
  if (isGenerating) {
    showToast("Synthesis in progress...", "warning");
    return;
  }
  const text=document.getElementById('wisdom-input').value.trim();
  if(!text){showToast('Enter some wisdom first','error');return}
  
  setLoading(true);
  try{
    await window.waitForToken();
    const body={text,author:document.getElementById('author-input').value||'LEVI-AI',mood:currentStyle,background:document.getElementById('bg-input').value};
    
    // Using Retry Utility
    const d = await fetchWithRetry(`${getApiBase()}/studio/generate_image`, {
      method:'POST',
      body:JSON.stringify(body),
      headers:{'Content-Type':'application/json'}
    });
    
    if (d.status === 'queued') {
      showToast("Synthesis started...", "info");
      pollTask(d.task_id, text);
      return;
    }

    if(d.warnings && d.warnings.length > 0) {
      console.warn("[LEVI] Generation warnings:", d.warnings);
      if (d.warnings.some(w => w.toLowerCase().includes("fallback"))) {
         showToast("AI busy, used high-quality fallback", "info");
      }
    }

    const imgSrc = d.url || d.image_url || d.image_b64;
    if(imgSrc){ displayImage(imgSrc, text); }
    else throw new Error('No image in response');
  }catch(e){
    console.error("Synthesize error:", e);
    showToast(e.message || 'Generation error','error');
    setLoading(false);
  }finally{
     // Loading is handled in displayImage or catch
    if(!currentImage) setLoading(false);
  }
}

function setLoading(on){
  isGenerating = on;
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
      const d = await fetchWithRetry(`${getApiBase()}/studio/task_status/${id}`);

      if ((d.status === 'completed' || d.status === 'done') && d.result) {
        setLoading(false);
        const res = d.result;
        if(res.warnings && res.warnings.length > 0) {
           showToast("Render complete with optimization", "info");
        }
        const imgSrc = res.url || res.image_url || res.image_b64 || res.image;
        if (imgSrc) {
            displayImage(imgSrc, text);
        } else {
            showToast('Generation completed but no image returned', 'error');
        }
      } else if (d.status === 'failed') {
        showToast('Synthesis failed: ' + (d.error || 'Unknown error'), 'error');
        setLoading(false);
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
      retryCount++;
      if (retryCount >= maxRetries) {
        setLoading(false);
        showToast('Connection lost', 'error');
      } else {
        setTimeout(poll, 5000);
      }
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
  if(navigator.share)navigator.share({title:'LEVI-AI Wisdom',text:t,url:location.href});
  else{navigator.clipboard.writeText(t);showToast('Quote copied to clipboard')}
}
function regenerate(){if(document.getElementById('wisdom-input').value.trim())synthesize()}
async function makeVideo(){
  if (isGenerating) {
    showToast('Synthesis already in progress', 'warning');
    return;
  }
  const text=document.getElementById('wisdom-input').value.trim();
  if(!text){showToast('Enter some wisdom first','error');return}
  setLoading(true);
  showToast('Video generation queued...', 'info');
  try {
    const body={text,author:document.getElementById('author-input').value||'LEVI-AI',mood:currentStyle};
    
    // Using Retry Utility
    const d = await fetchWithRetry(`${getApiBase()}/studio/generate_video`, {
      method:'POST',
      body:JSON.stringify(body),
      headers:{'Content-Type':'application/json'}
    });
    
    if(d.status === 'queued') {
        showToast('Video synthesis in progress...', 'info');
    } else if (d.status === 'completed' || d.url || d.image_b64) {
        showToast('Video heavy, rendered as high-quality image fallback', 'info');
        displayImage(d.url || d.image_b64, text);
    }
  } catch(e) {
      console.error("Video request failed:", e);
      showToast('Video request failed: ' + e.message, 'error');
  } finally {
      if (!currentImage) setLoading(false);
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
