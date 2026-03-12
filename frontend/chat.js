// Glassmorphism Chat Functionality for Quotes Bot

// DOM Elements
const messages = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");

// State
let isProcessing = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    chatForm.addEventListener('submit', handleSubmit);
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    });
}

// Handle form submission
function handleSubmit(e) {
    e.preventDefault();
    sendMessage();
}

// Add message to chat
function addMessage(text, type) {
    const msg = document.createElement("div");
    msg.className = `message ${type}`;
    
    // Format text with line breaks
    if (text.includes('\n')) {
        const lines = text.split('\n');
        msg.innerHTML = lines.map(line => `<p>${line}</p>`).join('');
    } else {
        msg.innerText = text;
    }
    
    messages.appendChild(msg);
    messages.scrollTop = messages.scrollHeight;
}

// Send message to bot
function sendMessage() {
    const text = userInput.value.trim();
    
    if (text === "" || isProcessing) return;
    
    // Add user message
    addMessage(text, "user");
    
    // Clear input
    userInput.value = "";
    
    // Show typing indicator
    showTyping();
    
    // Disable input during processing
    isProcessing = true;
    
    // Determine the API endpoint
    const API_URL = window.location.hostname === 'localhost' 
        ? 'http://localhost:5000' 
        : '';
    
    fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        removeTyping();
        
        if (data.reply) {
            addMessage(data.reply, "bot");
        } else if (data.responses && data.responses.length > 0) {
            data.responses.forEach(response => {
                if (response.text) {
                    addMessage(response.text, "bot");
                }
            });
        } else if (data.error) {
            addMessage(data.error, "bot");
        } else {
            addMessage("I'm here to share wisdom. What would you like to explore?", "bot");
        }
    })
    .catch(error => {
        console.error('Error:', error);
        removeTyping();
        addMessage("The universe seems quiet right now. Please try again.", "bot");
    })
    .finally(() => {
        isProcessing = false;
    });
}

// Quick action function
function quick(topic) {
    let text = "";
    
    switch(topic) {
        case 'motivation':
            text = "Give me a motivational quote";
            break;
        case 'love':
            text = "Give me a love quote";
            break;
        case 'life':
            text = "Give me a quote about life";
            break;
        case 'random':
            text = "Give me a random quote";
            break;
        default:
            text = topic;
    }
    
    userInput.value = text;
    sendMessage();
}

// Show typing indicator
function showTyping() {
    const typing = document.createElement("div");
    typing.className = "message bot";
    typing.id = "typing";
    typing.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    messages.appendChild(typing);
    messages.scrollTop = messages.scrollHeight;
}

// Remove typing indicator
function removeTyping() {
    const typing = document.getElementById("typing");
    if (typing) {
        typing.remove();
    }
}

// Expose functions to global scope
window.quick = quick;

