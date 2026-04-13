let socket = null;

function connectWebSocket(onMessage) {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("Connected to LEVI-AI WebSocket");
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Telemetry:", data);
        if (onMessage) onMessage(data);
    };

    socket.onclose = () => {
        console.log("Disconnected from LEVI-AI WebSocket, retrying...");
        setTimeout(() => connectWebSocket(onMessage), 3000);
    };

    socket.onerror = (error) => {
        console.error("WebSocket Error:", error);
    };
}

// Auto-connect if onMessage is not needed immediately, or export it
if (typeof window !== 'undefined') {
    window.connectWebSocket = connectWebSocket;
}
