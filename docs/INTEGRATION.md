# 🔌 The Glassmorphic Integration Interface

How the `React + Vite` Client talks to the `FastAPI + Celery` Backend Matrix.

---

## 📡 1. Deep Core SSE Brain Streaming

The frontend does not Wait 10 seconds for a response logic string. It uses `useBrain.js` to parse tokens identically out of the `EventSource` connection.

### How it works natively:
The `fetch` request uses `Accept: text/event-stream`.
Instead of JSON wrapping, the backend Uvicorn server yields chunks separated by `event: pulse_update` and `data: {json}`. The `readStream` function decodes bytes, appending characters directly into the React ChatWindow state buffer.

```javascript
// frontend/src/services/brainService.js
while(true) {
    const {done, value} = await reader.read();
    if (done) break;
    // ... parse out JSON components to trigger the UI intent changes.
}
```

## 🎥 2. Event Polling (Celery Background Renders)
Since SSE is purely text, rendering a 21-megabyte `.mp4` file via MoviePy stops the main event loop entirely.

**The Polling Handshake:**
1. UI fires `POST /api/v1/studio/generate_video`.
2. Backend triggers Celery and immediately responds with a `mission_id`.
3. UI mounts a `setInterval` checking `GET /api/v1/studio/mission_status/:mission_id` every 3.5 seconds.
4. When `status == "completed"`, it safely reads the generated signed URL from Google Cloud Storage.

## 🌌 3. The `Intent` UI Map
The MetaPlanner dictates the visual display. If the LLM generates JSON with `"intent": "generate_image"`, the frontend immediately drops the `MessageBubble.jsx` component and spawns the `StudioCanvas.jsx` layout seamlessly below the chat string.
