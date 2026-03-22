import { generateImage, generateVideo, getCredits, getTaskStatus } from './api.js';

const studioPreview = document.getElementById('studio-preview');
const studioLoading = document.getElementById('studio-loading');
const emptyPreview = document.getElementById('empty-preview');
const generateBtn = document.getElementById('generate-studio');
const downloadBtn = document.getElementById('download-studio');
const saveBtn = document.getElementById('save-studio');
const generateVideoBtn = document.getElementById('generate-video-studio'); 
const creditsDisplay = document.getElementById('user-credits'); 

const quoteInput = document.getElementById('studio-quote');
const authorInput = document.getElementById('studio-author');
const keywordInput = document.getElementById('studio-bg-keywords');
const fileInput = document.getElementById('studio-bg-upload');
const styleButtons = document.querySelectorAll('.style-btn');

let currentMood = 'philosophical';
let customBgBase64 = null;

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

// Generation Logic (Image)
generateBtn.addEventListener('click', async () => {
    const text = quoteInput.value.trim();
    const token = localStorage.getItem('levi_token');
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
        
        const data = await generateImage(text, author, currentMood, customBgBase64, token);

        if (data.task_id) {
            window.ui.showToast("Synthesis started in cosmic background... 🌌");
            pollTask(data.task_id, (result) => {
                studioPreview.src = result.url;
                studioPreview.classList.remove('opacity-20', 'hidden');
                studioLoading.classList.add('hidden');
                generateBtn.disabled = false;
                downloadBtn.disabled = false;
                saveBtn.disabled = false;
                if (generateVideoBtn) generateVideoBtn.disabled = false;
                updateCredits();
                window.ui.showToast("Masterpiece rendered! ✨");
            }, (err) => {
                console.error(err);
                window.ui.showToast("Synthesis failed in the void.", "error");
                studioLoading.classList.add('hidden');
                generateBtn.disabled = false;
            });
            return; // Don't proceed to sync handling
        }

        studioPreview.src = data.image_b64;
        studioPreview.dataset.id = data.id;
        studioPreview.classList.remove('opacity-20', 'hidden');
        
        downloadBtn.disabled = false;
        saveBtn.disabled = false;
        if (generateVideoBtn) generateVideoBtn.disabled = false;
        
        updateCredits(); // Refresh credits
        window.ui.showToast("Masterpiece rendered! ✨");
    } catch (err) {
        console.error(err);
        window.ui.showToast(err.message || "Synthesis failed.", "error");
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
                    window.URL.revokeObjectURL(url);
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
