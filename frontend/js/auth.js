import { login, register } from './api.js';

const form = document.getElementById('auth-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const messageBox = document.getElementById('auth-message');
const title = document.getElementById('auth-title');
const subtitle = document.getElementById('auth-subtitle');
const submitBtn = document.getElementById('submit-btn');
const toggleText = document.getElementById('toggle-text');

let isLogin = true;

window.toggleAuthMode = () => {
    isLogin = !isLogin;
    title.innerText = isLogin ? 'Welcome Back' : 'Create Account';
    subtitle.innerText = isLogin ? 'Enter your details to continue your journey.' : 'Join the wisdom circle and save your journey.';
    submitBtn.innerText = isLogin ? 'Login →' : 'Sign Up →';
    toggleText.innerHTML = isLogin ? 
        'Don\'t have an account? <button onclick="toggleAuthMode()" class="text-primary font-bold hover:underline">Create Account</button>' :
        'Already have an account? <button onclick="toggleAuthMode()" class="text-primary font-bold hover:underline">Login</button>';
    messageBox.classList.add('hidden');
};

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = usernameInput.value;
    const password = passwordInput.value;

    messageBox.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.innerText = 'Processing...';

    try {
        if (isLogin) {
            const data = await login(username, password);
            localStorage.setItem('levi_token', data.access_token);
            localStorage.setItem('levi_user', username);
            window.location.href = 'index.html';
        } else {
            await register(username, password);
            // After register, auto login
            const data = await login(username, password);
            localStorage.setItem('levi_token', data.access_token);
            localStorage.setItem('levi_user', username);
            window.location.href = 'index.html';
        }
    } catch (err) {
        messageBox.innerText = err.message;
        messageBox.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerText = isLogin ? 'Login →' : 'Sign Up →';
    }
});
