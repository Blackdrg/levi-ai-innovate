function toggleMobileMenu(){const m=document.getElementById('mobile-menu');if(!m)return;m.classList.toggle('hidden');document.body.style.overflow=m.classList.contains('hidden')?'':'hidden'}
function showToast(msg, type = 'success') { const t = document.getElementById('toast'); const bg = type === 'error' ? 'rgba(147,0,10,.85)' : type === 'warning' ? 'rgba(120,90,0,.85)' : 'rgba(19,19,23,.9)'; const border = type === 'error' ? 'rgba(255,180,171,.3)' : type === 'warning' ? 'rgba(242,202,80,.4)' : 'rgba(242,202,80,.35)'; const icon = type === 'error' ? 'error' : type === 'warning' ? 'warning' : 'check_circle'; t.innerHTML = `<div style="background:${bg};border:.5px solid ${border};-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px)" class="flex items-center gap-2.5 px-5 py-3 rounded-full shadow-2xl"><span class="material-symbols-outlined icon-fill" style="font-size:16px;color:#f2ca50">${icon}</span><span style="font-size:12px;color:#e5e1e7;font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;letter-spacing:.04em">${msg}</span></div>`; t.classList.add('show'); clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('show'), 3200) }

// Inject spin keyframe
const s=document.createElement('style');s.textContent='@keyframes spin{to{transform:rotate(360deg)}}';document.head.appendChild(s);

const API_BASE = (['localhost', '127.0.0.1', '::1', '0.0.0.0'].includes(location.hostname)) ? `http://${location.hostname}:8000` : location.origin + '/api';
let currentMood='inspiring';
let lastBotText='';
let sessionId=localStorage.getItem('levi_session_id')||(()=>{const id='s_'+Date.now().toString(36);localStorage.setItem('levi_session_id',id);return id})();

window.setMood = function(btn,mood){
  document.querySelectorAll('.mood-chip').forEach(b=>{b.classList.remove('active')});
  btn.classList.add('active');
  currentMood=mood;
  document.getElementById('session-info').textContent=`Active · ${mood.charAt(0).toUpperCase()+mood.slice(1)}`;
};

window.autoResize = function(el){el.style.height='auto';el.style.height=Math.min(el.scrollHeight,160)+'px'};
window.handleKey = function(e){if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();window.sendMessage()}};

function appendMsg(content,role){
  const msgs=document.getElementById('messages');
  const div=document.createElement('div');
  div.className=(role==='user'?'msg-user':'msg-bot')+' p-4 fade-in';
  div.innerHTML=`<p class="text-sm ${role==='user'?'text-on-surface':'text-on-surface-variant'} font-light leading-relaxed">${content.replace(/\n/g,'<br/>')}</p>`;
  if(role==='bot'){
    const actions=document.createElement('div');
    actions.className='flex gap-3 mt-3 pt-2 border-t border-white/5';
    actions.innerHTML=`<button onclick="speakText(this.dataset.text)" data-text="${content.replace(/"/g,'&quot;')}" class="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-primary transition-colors uppercase tracking-wider"><span class="material-symbols-outlined icon-sm">volume_up</span>Speak</button><button onclick="copyText(this.dataset.text)" data-text="${content.replace(/"/g,'&quot;')}" class="flex items-center gap-1 text-[10px] text-zinc-500 hover:text-primary transition-colors uppercase tracking-wider"><span class="material-symbols-outlined icon-sm">content_copy</span>Copy</button>`;
    div.appendChild(actions);
  }
  msgs.appendChild(div);
  msgs.scrollTop=msgs.scrollHeight;
  return div;
}

function showTyping(){
  const msgs=document.getElementById('messages');
  const div=document.createElement('div');
  div.id='typing-indicator';
  div.className='msg-bot p-4 fade-in inline-flex items-center gap-1.5';
  div.innerHTML='<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  msgs.appendChild(div);
  msgs.scrollTop=msgs.scrollHeight;
}
function hideTyping(){document.getElementById('typing-indicator')?.remove()}

window.sendMessage = async function(){
  const input=document.getElementById('chat-input');
  const text=input.value.trim();
  if(!text)return;
  input.value='';input.style.height='auto';
  appendMsg(text,'user');
  document.getElementById('send-icon').classList.add('hidden');
  document.getElementById('send-loading').classList.remove('hidden');
  document.getElementById('send-btn').disabled=true;
  showTyping();
  try{
    const token=localStorage.getItem('levi_token');
    const headers={'Content-Type':'application/json'};
    if(token)headers['Authorization']='Bearer '+token;
    const r=await fetch(API_BASE+'/chat',{method:'POST',headers,body:JSON.stringify({message:text,mood:currentMood,session_id:sessionId})});
    hideTyping();
    if(!r.ok)throw new Error('API '+r.status);
    const d=await r.json();
    const reply=d.response||d.message||'I ponder your question…';
    lastBotText=reply;
    appendMsg(reply,'bot');
  }catch(err){
    hideTyping();
    const fallbacks=['Consciousness is the universe examining itself through individual experience.','In the depth of winter, I finally learned that within me there lay an invincible summer.','The obstacle is the path — what we resist, we become.'];
    const reply=fallbacks[Math.floor(Math.random()*fallbacks.length)];
    lastBotText=reply;
    appendMsg(reply,'bot');
  }finally{
    document.getElementById('send-icon').classList.remove('hidden');
    document.getElementById('send-loading').classList.add('hidden');
    document.getElementById('send-btn').disabled=false;
  }
};

window.speakText = function(text){if('speechSynthesis' in window){const u=new SpeechSynthesisUtterance(text);u.rate=0.9;u.pitch=0.95;window.speechSynthesis.speak(u);showToast('Speaking…')}else{showToast('TTS not supported','warning')}};
window.speakLast = function(){if(lastBotText)window.speakText(lastBotText);else showToast('Nothing to speak yet','warning')};
window.copyText = function(text){navigator.clipboard.writeText(text).then(()=>showToast('Copied!')).catch(()=>showToast('Copy failed','error'))};
window.clearChat = function(){document.getElementById('messages').innerHTML='';appendMsg('Greetings, seeker. I am LEVI — your philosophical companion. What mysteries shall we explore tonight?','bot');lastBotText=''};

// Voice input
window.startVoice = function(){
  if(!('webkitSpeechRecognition' in window||'SpeechRecognition' in window)){showToast('Voice not supported in this browser','warning');return}
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  const r=new SR();r.lang='en-US';r.interimResults=false;
  r.onstart=()=>{document.getElementById('voice-btn').style.color='#f2ca50'};
  r.onresult=e=>{document.getElementById('chat-input').value=e.results[0][0].transcript;window.autoResize(document.getElementById('chat-input'))};
  r.onend=()=>{document.getElementById('voice-btn').style.color=''};
  r.start();
};

// Auth
const u=localStorage.getItem('levi_user');if(u){try{const o=JSON.parse(u);document.getElementById('nav-auth-btn').textContent=o.username||'Account';document.getElementById('nav-auth-btn').href='my-gallery.html'}catch{}}

// Health check
fetch(API_BASE+'/health').then(r=>{if(!r.ok)throw 0}).catch(()=>{document.getElementById('status-dot').style.background='#f87171';document.getElementById('status-label').textContent='Offline'});

// Allow toggleMobileMenu to be global
window.toggleMobileMenu = toggleMobileMenu;
