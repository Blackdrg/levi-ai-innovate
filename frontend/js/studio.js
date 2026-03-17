import { generateQuoteImage } from './api.js';

const studioPreview = document.getElementById('studio-preview');
const studioLoading = document.getElementById('studio-loading');
const emptyPreview = document.getElementById('empty-preview');
const generateBtn = document.getElementById('generate-studio');
const downloadBtn = document.getElementById('download-studio');
const saveBtn = document.getElementById('save-studio');

const quoteInput = document.getElementById('studio-quote');
const authorInput = document.getElementById('studio-author');
const keywordInput = document.getElementById('studio-bg-keywords');
const fileInput = document.getElementById('studio-bg-upload');
const styleButtons = document.querySelectorAll('.style-btn');

let currentMood = 'philosophical';
let customBgBase64 = null;

// Style Selection
styleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        styleButtons.forEach(b => b.classList.remove('border-violet-500', 'bg-white/10'));
        btn.classList.add('border-violet-500', 'bg-white/10');
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

// Generation Logic
generateBtn.addEventListener('click', async () => {
    const text = quoteInput.value.trim();
    if (!text) {
        window.ui.showToast("Please enter some wisdom first!", "error");
        return;
    }

    studioLoading.classList.remove('hidden');
    emptyPreview.classList.add('hidden');
    studioPreview.classList.add('opacity-20');
    generateBtn.disabled = true;

    try {
        const author = authorInput.value.trim() || "LEVI AI";
        const keywords = keywordInput.value.trim();
        
        const data = await generateQuoteImage(text, author, currentMood, {
            custom_bg: customBgBase64 || null,
            text: text // Note: api.js generateQuoteImage takes (text, author, mood)
        });

        studioPreview.src = data.image_b64;
        studioPreview.dataset.id = data.id;
        studioPreview.classList.remove('opacity-20', 'hidden');
        
        downloadBtn.disabled = false;
        saveBtn.disabled = false;
        
        window.ui.showToast("Masterpiece rendered! ✨");
    } catch (err) {
        console.error(err);
        window.ui.showToast("Synthesis failed. Try again.", "error");
    } finally {
        studioLoading.classList.add('hidden');
        generateBtn.disabled = false;
    }
});

// Action Buttons
downloadBtn.addEventListener('click', () => {
    const link = document.createElement('a');
    link.href = studioPreview.src;
    link.download = `levi-studio-${Date.now()}.png`;
    link.click();
});

saveBtn.addEventListener('click', () => {
    const user = localStorage.getItem('levi_user');
    if (!user) {
        window.ui.showToast("Please login to save your art!", "error");
        return;
    }

    const gallery = JSON.parse(localStorage.getItem(`levi_gallery_${user}`)) || [];
    gallery.unshift({
        id: studioPreview.dataset.id || Date.now(),
        image: studioPreview.src,
        text: quoteInput.value,
        timestamp: new Date().toISOString()
    });
    localStorage.setItem(`levi_gallery_${user}`, JSON.stringify(gallery));
    
    saveBtn.innerText = 'Saved! ✨';
    saveBtn.disabled = true;
});
