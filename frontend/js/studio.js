/**
 * LEVI-AI Studio Logic
 * Phase 6: Production Hardened
 */

(function() {
    let currentStyle = 'philosophical';
    let currentImage = null;
    let isGenerating = false;

    const insights = {
        philosophical: { text: 'prioritize ethereal lighting, high-contrast obsidian shadows, and golden particle dispersion.', stability: 67 },
        zen: { text: 'evoke bamboo mist, still water reflections, and morning light through ancient forests.', stability: 82 },
        cyberpunk: { text: 'generate neon-soaked cityscapes, rain-slicked streets, and holographic overlays.', stability: 74 },
        futuristic: { text: 'render clean white surfaces, cosmic voids, and geometric precision with bioluminescent accents.', stability: 91 },
        stoic: { text: 'depict marble columns, dawn light, classical architecture — austere and powerful.', stability: 88 },
        melancholic: { text: 'create rain-washed cobblestones, blue hour, soft bokeh with poetic melancholy.', stability: 79 }
    };

    function updateChar(el) {
        const n = el.value.length;
        const cc = document.getElementById('char-count');
        if (cc) {
            cc.textContent = n;
            cc.style.color = n > 260 ? '#f87171' : n > 200 ? '#f2ca50' : '';
        }
    }

    function setStyle(btn, style) {
        document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentStyle = style;
        
        const info = insights[style] || insights.philosophical;
        const styleName = style.charAt(0).toUpperCase() + style.slice(1);
        
        const insStyle = document.getElementById('insight-style');
        const insText = document.getElementById('insight-text');
        const stabBar = document.getElementById('stability-bar');
        const stabVal = document.getElementById('stability-val');

        if (insStyle) insStyle.textContent = styleName;
        if (insText) insText.innerHTML = `Synthesizing with <span class="text-primary italic">${styleName}</span> style will ${info.text}`;
        if (stabBar) stabBar.style.width = info.stability + '%';
        if (stabVal) stabVal.textContent = info.stability + '%';
    }

    async function synthesize() {
        if (isGenerating) return;
        
        const textInput = document.getElementById('wisdom-input');
        const authorInput = document.getElementById('author-input');
        const text = textInput ? textInput.value.trim() : '';
        
        if (!text) {
            if (window.api) window.api.apiFetch.showToast?.('Enter some wisdom first', 'error');
            else alert('Enter some wisdom first');
            return;
        }
        
        setLoading(true);
        try {
            const author = authorInput ? authorInput.value : 'LEVI-AI';
            const data = await window.api.generateImage(text, author, currentStyle);
            
            if (data.status === 'queued' || data.task_id) {
                pollTask(data.task_id || data.id, text);
            } else {
                const imgSrc = data.url || data.image_url || data.image_b64;
                if (imgSrc) displayImage(imgSrc, text);
                else throw new Error('No image in response');
            }
        } catch (e) {
            console.error("Synthesis failed", e);
            setLoading(false);
        } finally {
            if (window.syncUser) window.syncUser();
        }
    }

    function setLoading(on) {
        isGenerating = on;
        const synthBtn = document.getElementById('synth-btn');
        const synthIcon = document.getElementById('synth-icon');
        const synthSpinner = document.getElementById('synth-spinner');
        const overlay = document.getElementById('loading-overlay');
        const placeholder = document.getElementById('preview-placeholder');
        const hud = document.getElementById('hud-label');

        if (synthBtn) synthBtn.disabled = on;
        if (synthIcon) synthIcon.classList.toggle('hidden', on);
        if (synthSpinner) synthSpinner.classList.toggle('hidden', !on);
        if (overlay) overlay.classList.toggle('hidden', !on);
        if (placeholder) placeholder.classList.toggle('hidden', on);
        if (hud) hud.textContent = on ? 'Synthesizing' : 'Ready';
        
        if (on && window.ui && window.ui.showLoader) window.ui.showLoader();
        if (!on && window.ui && window.ui.finishLoader) window.ui.finishLoader();
    }

    async function pollTask(id, text) {
        let retryCount = 0;
        const maxRetries = 40;

        const poll = async () => {
            try {
                const d = await window.api.getTaskStatus(id);
                if ((d.status === 'completed' || d.status === 'done') && d.result) {
                    setLoading(false);
                    const imgSrc = d.result.url || d.result.image_url || d.result.image_b64;
                    displayImage(imgSrc, text);
                } else if (d.status === 'failed') {
                    setLoading(false);
                    console.error("Task failed", d.error);
                } else if (retryCount < maxRetries) {
                    retryCount++;
                    setTimeout(poll, 3000);
                } else {
                    setLoading(false);
                }
            } catch (e) {
                console.error("Poll error", e);
                setLoading(false);
            }
        };
        poll();
    }

    function displayImage(src, text) {
        currentImage = src;
        const img = document.getElementById('preview-img');
        const container = document.getElementById('preview-container');
        const placeholder = document.getElementById('preview-placeholder');
        const title = document.getElementById('preview-title');
        const overlay = document.getElementById('preview-bottom-overlay');
        const vidBtn = document.getElementById('video-btn');

        if (img) {
            img.src = src;
            img.onload = () => img.classList.remove('opacity-0');
        }
        if (container) container.classList.remove('hidden');
        if (placeholder) placeholder.classList.add('hidden');
        if (title) title.textContent = text.length > 42 ? text.slice(0, 42) + '...' : text;
        if (overlay) overlay.style.opacity = '1';
        if (vidBtn) vidBtn.disabled = false;
        
        addThumb(src);
    }

    function addThumb(src) {
        const strip = document.getElementById('thumb-strip');
        if (!strip) return;
        const div = document.createElement('div');
        div.className = 'thumb selected flex-shrink-0 w-24 h-24 rounded-2xl overflow-hidden border-2 border-primary/40';
        div.innerHTML = `<img src="${src}" class="w-full h-full object-cover"/>`;
        div.onclick = () => {
            const img = document.getElementById('preview-img');
            if (img) img.src = src;
            document.querySelectorAll('.thumb').forEach(t => t.classList.remove('selected', 'border-primary/40'));
            div.classList.add('selected', 'border-primary/40');
        };
        strip.prepend(div);
    }

    // Export to window
    window.setStyle = setStyle;
    window.updateChar = updateChar;
    window.synthesize = synthesize;
    window.newCanvas = () => window.location.reload();

    document.addEventListener('DOMContentLoaded', () => {
        const user = JSON.parse(localStorage.getItem('levi_user') || 'null');
        if (!user && window.location.hostname !== 'localhost') {
            window.location.href = 'auth.html';
        }
        if (user && document.getElementById('user-name')) {
            document.getElementById('user-name').textContent = user.username || 'Seeker';
        }
    });

})();
