/**
 * studio.js — Visual Studio page logic.
 * Fixed to use correct DOM IDs matching studio.html.
 *
 * ID map (studio.html → this file):
 *   preview-img           → previewImg
 *   preview-placeholder   → previewPlaceholder
 *   preview-container     → previewContainer
 *   studio-loading        → studioLoading
 *   generate-studio       → generateBtn
 *   generate-video-studio → generateVideoBtn
 *   download-btn          → downloadBtn
 *   share-btn             → shareBtn
 *   regenerate-btn        → regenerateBtn
 *   studio-quote          → quoteInput
 *   studio-author         → authorInput
 *   studio-bg-keywords    → keywordInput
 *   studio-bg-upload      → fileInput
 *   user-credits          → creditsDisplay
 *   .style-btn            → styleButtons
 */

import { generateImage, generateVideo, getCredits } from './api.js';

// ── DOM refs ──────────────────────────────────────────────────────────────────
const previewImg         = document.getElementById('preview-img');
const previewPlaceholder = document.getElementById('preview-placeholder');
const previewContainer   = document.getElementById('preview-container');
const studioLoading      = document.getElementById('studio-loading');
const generateBtn        = document.getElementById('generate-studio');
const generateVideoBtn   = document.getElementById('generate-video-studio');
const downloadBtn        = document.getElementById('download-btn');
const shareBtn           = document.getElementById('share-btn');
const regenerateBtn      = document.getElementById('regenerate-btn');
const quoteInput         = document.getElementById('studio-quote');
const authorInput        = document.getElementById('studio-author');
const keywordInput       = document.getElementById('studio-bg-keywords');
const fileInput          = document.getElementById('studio-bg-upload');
const creditsDisplay     = document.getElementById('user-credits');
const styleButtons       = document.querySelectorAll('.style-btn');
const charCount          = document.getElementById('char-count');
const errorMsg           = document.getElementById('error-msg');

let currentMood    = 'philosophical';
let customBgBase64 = null;

// ── Toast helper ──────────────────────────────────────────────────────────────
function showToast(message, type = 'info') {
    if (window.ui && window.ui.showToast) {
        window.ui.showToast(message, type);
        return;
    }
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = message;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 3000);
}

function showError(msg) {
    if (!errorMsg) return;
    errorMsg.textContent = msg;
    errorMsg.classList.remove('hidden');
    setTimeout(() => errorMsg.classList.add('hidden'), 5000);
}

// ── Credits ───────────────────────────────────────────────────────────────────
async function updateCredits() {
    const token = localStorage.getItem('levi_token');
    if (token && creditsDisplay) {
        try {
            const data = await getCredits(token);
            creditsDisplay.textContent = `${data.credits} Credits (${data.tier})`;
        } catch (err) {
            creditsDisplay.textContent = 'Sign in for credits';
        }
    } else if (creditsDisplay) {
        creditsDisplay.textContent = '10 Free Credits';
    }
}
updateCredits();

// ── Style selection ───────────────────────────────────────────────────────────
styleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        styleButtons.forEach(b => {
            b.classList.remove('border-yellow-400', 'bg-white/10');
            b.classList.add('border-white/5');
        });
        btn.classList.add('border-yellow-400', 'bg-white/10');
        btn.classList.remove('border-white/5');
        currentMood = btn.dataset.mood;
    });
});

// ── Character counter ─────────────────────────────────────────────────────────
if (quoteInput && charCount) {
    quoteInput.addEventListener('input', () => {
        const len = quoteInput.value.length;
        charCount.textContent = `${len} / 300`;
        charCount.classList.toggle('text-red-400', len > 280);
    });
}

// ── File upload ───────────────────────────────────────────────────────────────
if (fileInput) {
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (event) => {
            customBgBase64 = event.target.result;
            if (keywordInput) {
                keywordInput.value    = '✅ Custom upload active';
                keywordInput.disabled = true;
            }
            showToast('Background image uploaded!');
        };
        reader.readAsDataURL(file);
    });
}

// ── Show/hide preview helpers ────────────────────────────────────────────────
function showPreview(imageSrc) {
    previewImg.src = imageSrc;
    previewPlaceholder.classList.add('hidden');
    previewContainer.classList.remove('hidden');
    if (generateVideoBtn) generateVideoBtn.disabled = false;
}

function setGenerating(on) {
    if (on) {
        studioLoading.classList.remove('hidden');
        generateBtn.disabled = true;
        generateBtn.textContent = 'Synthesizing…';
        if (previewContainer && !previewContainer.classList.contains('hidden')) {
            previewImg.classList.add('opacity-20');
        }
    } else {
        studioLoading.classList.add('hidden');
        generateBtn.disabled = false;
        generateBtn.textContent = 'Synthesize Visual →';
        previewImg.classList.remove('opacity-20');
    }
}

// ── Generate image ────────────────────────────────────────────────────────────
generateBtn.addEventListener('click', async () => {
    const text   = quoteInput.value.trim();
    const author = authorInput.value.trim() || 'LEVI AI';
    const token  = localStorage.getItem('levi_token');

    if (!text) {
        showError('Please enter some wisdom first!');
        return;
    }
    if (text.length > 300) {
        showError('Quote is too long. Please keep it under 300 characters.');
        return;
    }

    setGenerating(true);
    errorMsg.classList.add('hidden');

    try {
        const data = await generateImage(text, author, currentMood, customBgBase64, token);
        showPreview(data.image_b64);
        previewImg.dataset.quote  = text;
        previewImg.dataset.author = author;
        previewImg.dataset.id     = data.id || '';
        updateCredits();
        showToast('Masterpiece rendered! ✨');
    } catch (err) {
        showError(err.message || 'Synthesis failed. Please try again.');
        showToast(err.message || 'Generation failed.', 'error');
    } finally {
        setGenerating(false);
    }
});

// ── Regenerate ────────────────────────────────────────────────────────────────
if (regenerateBtn) {
    regenerateBtn.addEventListener('click', () => generateBtn.click());
}

// ── Generate video ────────────────────────────────────────────────────────────
if (generateVideoBtn) {
    generateVideoBtn.addEventListener('click', async () => {
        const text   = quoteInput.value.trim();
        const author = authorInput.value.trim() || 'LEVI AI';
        const token  = localStorage.getItem('levi_token');

        if (!text) {
            showError('Please enter wisdom before generating a video.');
            return;
        }

        showToast('Generating video card… This may take a minute. 🎬');
        generateVideoBtn.disabled = true;

        try {
            const result = await generateVideo(text, currentMood, author, token);

            if (result instanceof Blob) {
                const url = URL.createObjectURL(result);
                const a   = document.createElement('a');
                a.href     = url;
                a.download = `levi-wisdom-${Date.now()}.mp4`;
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(url);
                showToast('Video ready! Check your downloads. 🎥');
            } else if (result && result.task_id) {
                showToast('Video queued! Processing in background.');
            }
            updateCredits();
        } catch (err) {
            showToast(err.message || 'Video generation failed.', 'error');
        } finally {
            generateVideoBtn.disabled = false;
        }
    });
}

// ── Download ──────────────────────────────────────────────────────────────────
if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
        if (!previewImg.src || previewImg.src === window.location.href) return;
        const a   = document.createElement('a');
        a.href     = previewImg.src;
        a.download = `levi-studio-${Date.now()}.png`;
        a.click();
        showToast('Image downloaded!');
    });
}

// ── Share ─────────────────────────────────────────────────────────────────────
if (shareBtn) {
    shareBtn.addEventListener('click', async () => {
        const text  = previewImg.dataset.quote  || quoteInput.value;
        const token = localStorage.getItem('levi_token');
        if (window.ui && window.ui.shareContent) {
            await window.ui.shareContent('LEVI Wisdom', text, window.location.href);
        } else {
            navigator.clipboard.writeText(text);
            showToast('Quote copied to clipboard!');
        }
    });
}

// ── Save to local gallery ─────────────────────────────────────────────────────
// Expose for use if a save button is added later
window.saveToGallery = function () {
    const user = localStorage.getItem('levi_user');
    if (!user) {
        showToast('Please sign in to save your art!', 'error');
        return;
    }
    if (!previewImg.src || previewImg.src === window.location.href) {
        showToast('Generate an image first.', 'error');
        return;
    }
    const galleryKey = `levi_gallery_${user}`;
    const gallery    = JSON.parse(localStorage.getItem(galleryKey) || '[]');
    gallery.unshift({
        id:        previewImg.dataset.id || Date.now(),
        image:     previewImg.src,
        text:      quoteInput.value,
        timestamp: new Date().toISOString(),
    });
    localStorage.setItem(galleryKey, JSON.stringify(gallery));
    showToast('Saved to your gallery! ✨');
};

// ── Quick-fill chips (called from studio.html onclick) ───────────────────────
window.prefill = function (quote, author, mood) {
    quoteInput.value  = quote;
    authorInput.value = author;
    currentMood       = mood;
    // Activate matching style button
    styleButtons.forEach(btn => {
        if (btn.dataset.mood === mood) {
            btn.click();
        }
    });
    if (charCount) {
        charCount.textContent = `${quote.length} / 300`;
    }
};

// ── Mobile menu toggle (reused from studio.html inline script) ───────────────
window.toggleMobileMenu = function () {
    const menu = document.getElementById('mobile-menu');
    if (menu) menu.classList.toggle('open');
};

// ── Nav: show username if logged in ──────────────────────────────────────────
const navAuthBtn = document.getElementById('nav-auth-btn');
if (navAuthBtn) {
    const user = localStorage.getItem('levi_user');
    if (user) {
        navAuthBtn.textContent = user;
        navAuthBtn.href        = 'my-gallery.html';
    }
}
