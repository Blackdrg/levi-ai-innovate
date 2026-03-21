/**
 * auth.js — Login & Register logic for auth.html
 * Handles form submission, mode toggling, token storage.
 */
import { login, register } from './api.js';

let isLoginMode = true;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const form        = document.getElementById('auth-form');
const usernameEl  = document.getElementById('username');
const passwordEl  = document.getElementById('password');
const submitBtn   = document.getElementById('submit-btn');
const msgEl       = document.getElementById('auth-message');
const titleEl     = document.getElementById('auth-title');
const subtitleEl  = document.getElementById('auth-subtitle');

// ── Helpers ───────────────────────────────────────────────────────────────────
function showMessage(text, isError = false) {
    msgEl.textContent = text;
    msgEl.className = `text-xs py-3 px-4 rounded-xl text-center ${
        isError
            ? 'bg-red-900/20 border border-red-500/20 text-red-400'
            : 'bg-emerald-900/20 border border-emerald-500/20 text-emerald-400'
    }`;
    msgEl.classList.remove('hidden');
}

function setLoading(loading) {
    submitBtn.disabled = loading;
    submitBtn.textContent = loading
        ? 'Processing…'
        : isLoginMode ? 'Login →' : 'Create Account →';
}

// ── Mode toggle (called by inline onclick in HTML) ────────────────────────────
window.toggleAuthMode = function () {
    isLoginMode = !isLoginMode;
    msgEl.classList.add('hidden');

    if (isLoginMode) {
        titleEl.textContent    = 'Welcome Back';
        subtitleEl.textContent = 'Enter your details to continue your journey.';
        submitBtn.textContent  = 'Login →';
        document.getElementById('toggle-text').innerHTML =
            `Don't have an account? <button onclick="toggleAuthMode()" class="text-gold font-bold hover:underline">Create Account</button>`;
    } else {
        titleEl.textContent    = 'Join the Circle';
        subtitleEl.textContent = 'Create your account to begin your journey.';
        submitBtn.textContent  = 'Create Account →';
        document.getElementById('toggle-text').innerHTML =
            `Already have an account? <button onclick="toggleAuthMode()" class="text-gold font-bold hover:underline">Sign In</button>`;
    }
};

// ── Form submit ───────────────────────────────────────────────────────────────
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = usernameEl.value.trim();
    const password = passwordEl.value.trim();

    if (!username || !password) {
        showMessage('Please fill in all fields.', true);
        return;
    }

    if (!isLoginMode && password.length < 8) {
        showMessage('Password must be at least 8 characters.', true);
        return;
    }

    setLoading(true);

    try {
        let data;
        if (isLoginMode) {
            data = await login(username, password);
        } else {
            data = await register(username, password);
        }

        // Store credentials
        localStorage.setItem('levi_token', data.access_token);
        localStorage.setItem('levi_user', username);

        showMessage(isLoginMode ? 'Welcome back! Redirecting…' : 'Account created! Redirecting…');

        // Redirect after short delay
        setTimeout(() => {
            const redirect = new URLSearchParams(window.location.search).get('redirect');
            window.location.href = redirect || 'index.html';
        }, 800);

    } catch (err) {
        showMessage(err.message || 'Authentication failed. Please try again.', true);
        setLoading(false);
    }
});

// ── Auto-fill from URL token (Google OAuth redirect) ─────────────────────────
const urlToken = new URLSearchParams(window.location.search).get('token');
if (urlToken) {
    localStorage.setItem('levi_token', urlToken);
    // Fetch username from /users/me
    fetch(`${window.location.origin}/api/users/me`, {
        headers: { 'Authorization': `Bearer ${urlToken}` }
    })
    .then(r => r.json())
    .then(user => {
        if (user.username) {
            localStorage.setItem('levi_user', user.username);
        }
        window.location.href = 'index.html';
    })
    .catch(() => {
        window.location.href = 'index.html';
    });
}

// ── Nav: if already logged in, redirect away ─────────────────────────────────
if (localStorage.getItem('levi_token') && !urlToken) {
    const existingUser = localStorage.getItem('levi_user');
    if (existingUser) {
        window.location.href = 'index.html';
    }
}
