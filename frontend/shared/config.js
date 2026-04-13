const API_URL = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

if (typeof window !== 'undefined') {
    window.API_URL = API_URL;
    window.WS_URL = WS_URL;
}
