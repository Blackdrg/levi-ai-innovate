/**
 * LeviBrain v8: Thought Streaming UI
 * Handles SSE (Server-Sent Events) from the cognitive pipeline.
 */

class LeviThoughtStream {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.eventSource = null;
    }

    start(requestId) {
        this.eventSource = new EventSource(`/api/v1/brain/stream/${requestId}`);
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.renderThought(data);
        };

        this.eventSource.onerror = () => {
            this.eventSource.close();
            console.log("[V8-UI] Thought stream closed.");
        };
    }

    renderThought(data) {
        if (!this.container) return;

        const thoughtEl = document.createElement('div');
        thoughtEl.className = 'thought-node p-2 mb-2 bg-gray-800 text-cyan-400 border-l-2 border-cyan-500 animate-pulse';
        
        let message = "";
        switch (data.event) {
            case 'perception': message = "🧠 Perceiving intent..."; break;
            case 'goal': message = `🎯 Objective: ${data.objective}`; break;
            case 'planning': message = "📋 Planning Task Graph..."; break;
            case 'execution': message = "⚙️ Executing Autonomous Agents..."; break;
            case 'reflection.retry': message = "⚠️ Reflection pass failed. Correcting reasoning..."; break;
            case 'reflection.success': message = "✅ Reflection quality verified."; break;
            default: message = data.data || "";
        }

        thoughtEl.innerText = message;
        this.container.appendChild(thoughtEl);
        this.container.scrollTop = this.container.scrollHeight;
    }
}

window.LeviThoughtStream = LeviThoughtStream;
