import { generateImage, generateVideo, getCredits, getTaskStatus } from './api.js';

// Elements
const previewImg = document.getElementById('preview-img');
const studioLoading = document.getElementById('studio-loading');
const previewPlaceholder = document.getElementById('preview-placeholder');
const previewContainer = document.getElementById('preview-container');
const generateBtn = document.getElementById('generate-studio');
const downloadBtn = document.getElementById('download-btn');
const generateVideoBtn = document.getElementById('generate-video-studio'); 
const pushSubscribeBtn = document.getElementById('push-subscribe-btn');
const creditsDisplay = document.getElementById('user-credits'); 
const quoteInput = document.getElementById('studio-quote');
const charCount = document.getElementById('char-count'); 
if (charCount && quoteInput) { 
  quoteInput.addEventListener('input', () => {
    charCount.innerText = `${quoteInput.value.length} / 300`;
  });
}
const authorInput = document.getElementById('studio-author');
const keywordInput = document.getElementById('studio-bg-keywords');
const fileInput = document.getElementById('studio-bg-upload');
const styleButtons = document.querySelectorAll('.style-btn');

let currentMood = 'philosophical';
let customBgBase64 = null;

// Helper: Poll Task Status
async function pollTask(taskId, onSuccess, onError) {
    const poll = async () => {
        try {
            const data = await getTaskStatus(taskId);
            if (data.status === 'completed') {
                onSuccess(data.result);
            } else if (data.status === 'failed') {
                onError(new Error("Task failed on server"));
            } else {
                setTimeout(poll, 2000); // Poll every 2s
            }
        } catch (err) {
            onError(err);
        }
    };
    poll();
}

// Update credits on load
async function updateCredits() {
    const token = localStorage.getItem('levi_token');
    if (token && creditsDisplay) {
        try {
            const data = await getCredits(token);
            creditsDisplay.innerText = `${data.credits} Credits (${data.tier})`;
        } catch (err) {
            console.error("Failed to fetch credits:", err);
        }
    }
}
updateCredits();

// Style Selection
styleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        styleButtons.forEach(b => b.classList.remove('border-yellow-400', 'bg-white/10'));
        btn.classList.add('border-yellow-400', 'bg-white/10');
        currentMood = btn.dataset.mood;
    });
});

// File Upload Handling
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
            customBgBase64 = event.target.result;
            keywordInput.value = "Custom Upload Active";
            keywordInput.disabled = true;
            window.ui.showToast("Background image uploaded!");
        };
        reader.readAsDataURL(file);
    }
});

// Generation Logic (Image)
generateBtn.addEventListener('click', async () => {
    const text = quoteInput.value.trim();
    const token = localStorage.getItem('levi_token');
    if (!text) {
        window.ui.showToast("Please enter some wisdom first!", "error");
        return;
    }

    studioLoading.classList.remove('hidden');
    previewPlaceholder.classList.add('hidden');
    previewContainer.classList.remove('hidden');
    previewImg.classList.add('opacity-20');
    generateBtn.disabled = true;

    try {
        const author = authorInput.value.trim() || "LEVI AI";
        
        const data = await generateImage(text, author, currentMood, customBgBase64, token);

        if (data.task_id) {
            window.ui.showToast("Synthesis started in cosmic background... 🌌");
            pollTask(data.task_id, (result) => {
                previewImg.src = result.url || result.image_b64;
                previewImg.classList.remove('opacity-20');
                studioLoading.classList.add('hidden');
                generateBtn.disabled = false;
                if (generateVideoBtn) generateVideoBtn.disabled = false;
                updateCredits();
                window.ui.showToast("Masterpiece rendered! ✨");
            }, (err) => {
                console.error(err);
                window.ui.showToast("Synthesis failed in the void.", "error");
                studioLoading.classList.add('hidden');
                generateBtn.disabled = false;
            });
            return;
        }

        previewImg.src = data.image_b64;
        previewImg.dataset.id = data.id;
        previewImg.classList.remove('opacity-20');
        
        if (generateVideoBtn) generateVideoBtn.disabled = false;
        
        updateCredits();
        window.ui.showToast("Masterpiece rendered! ✨");
    } catch (err) {
        console.error(err);
        window.ui.showToast(err.message || "Synthesis failed.", "error");
        studioLoading.classList.add('hidden');
        previewPlaceholder.classList.remove('hidden');
        previewContainer.classList.add('hidden');
    } finally {
        studioLoading.classList.add('hidden');
        generateBtn.disabled = false;
    }
});

// Generation Logic (Video)
if (generateVideoBtn) {
    generateVideoBtn.addEventListener('click', async () => {
        const text = quoteInput.value.trim();
        const author = authorInput.value.trim() || "LEVI AI";
        const token = localStorage.getItem('levi_token');

        window.ui.showToast("Generating video card... This may take a minute. 🎬");
        generateVideoBtn.disabled = true;

        try {
            const result = await generateVideo(text, currentMood, author, token);
            
            if (result.task_id) {
                window.ui.showToast("Video processing in background. You'll be notified when ready.");
                pollTask(result.task_id, (res) => {
                    const url = res.url;
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `levi-wisdom-${Date.now()}.mp4`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.ui.showToast("Video ready! Check your downloads. 🎥");
                    generateVideoBtn.disabled = false;
                    updateCredits();
                }, (err) => {
                    console.error(err);
                    window.ui.showToast("Video generation failed in the void.", "error");
                    generateVideoBtn.disabled = false;
                });
                return;
            }

            if (result instanceof Blob) {
                const url = window.URL.createObjectURL(result);
                const a = document.createElement('a');
                a.href = url;
                a.download = `levi-wisdom-${Date.now()}.mp4`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                window.ui.showToast("Video ready! Check your downloads. 🎥");
                updateCredits();
            }
        } catch (err) {
            console.error(err);
            window.ui.showToast("Video generation failed.", "error");
        } finally {
            generateVideoBtn.disabled = false;
        }
    });
}

// Push Notifications
if (pushSubscribeBtn) {
    pushSubscribeBtn.addEventListener('click', async () => {
        // We'll try to fetch the key from the backend or fallback to the provided one
        let vapidPublicKey = "B...YOUR_PUBLIC_VAPID_KEY_HERE..."; 
        try {
            const res = await fetch(`${window.location.origin.includes('localhost') ? 'http://localhost:8000' : ''}/push/vapid_public_key`);
            if (res.ok) {
                const data = await res.json();
                vapidPublicKey = data.public_key;
            }
        } catch (e) { console.warn("Could not fetch VAPID key, using fallback."); }
        
        const success = await window.ui.subscribeToPush(vapidPublicKey);
        if (success) {
            pushSubscribeBtn.innerText = "Notifications Enabled! ✨";
            pushSubscribeBtn.disabled = true;
        }
    });
}

// Action Buttons
if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
        const link = document.createElement('a');
        link.href = previewImg.src;
        link.download = `levi-studio-${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });
}

// Prefill Helper (Exposed to window for onclick handlers)
window.prefill = (text, author, mood) => {
    quoteInput.value = text;
    authorInput.value = author;
    currentMood = mood;
    
    // Update style button UI
    styleButtons.forEach(btn => {
        if (btn.dataset.mood === mood) {
            btn.classList.add('border-yellow-400', 'bg-white/10');
        } else {
            btn.classList.remove('border-yellow-400', 'bg-white/10');
        }
    });
    
    window.ui.showToast(`Prefilled ${author}'s wisdom`);
};

const shareBtn = document.getElementById('share-btn'); 
if (shareBtn) { 
  shareBtn.addEventListener('click', () => { 
    const text = quoteInput.value.trim(); 
    const author = authorInput.value.trim() || 'LEVI AI'; 
    window.ui.shareContent('LEVI Wisdom', `"${text}" — ${author}`, window.location.href); 
  }); 
} 
 
const regenBtn = document.getElementById('regenerate-btn'); 
if (regenBtn) { 
  regenBtn.addEventListener('click', () => { 
    document.getElementById('generate-studio').click(); 
  }); 
}
