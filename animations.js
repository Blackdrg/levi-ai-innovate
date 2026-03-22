/**
 * LEVI Animation Engine v2.0
 * Particle constellation · Scroll reveals · 3D tilt · Morphing orbs
 * Page transitions · Chat animations · Studio effects · Typewriter
 */

'use strict';

// ─────────────────────────────────────────────
// 1. PARTICLE CONSTELLATION (Canvas)
// ─────────────────────────────────────────────
class ParticleConstellation {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d');
    this.particles = [];
    this.mouse = { x: -9999, y: -9999 };
    this.animFrame = null;
    this.maxParticles = window.innerWidth < 768 ? 50 : 100;
    this.connectionDist = 140;
    this.repelDist = 100;
    this.aiPulse = 0; // 0-1, driven externally when AI is responding

    this._resize();
    this._populate();
    this._bindEvents();
    this._loop();
  }

  _resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  _populate() {
    this.particles = [];
    for (let i = 0; i < this.maxParticles; i++) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        vx: (Math.random() - 0.5) * 0.4,
        vy: (Math.random() - 0.5) * 0.4,
        radius: Math.random() * 2 + 1,
        baseAlpha: Math.random() * 0.5 + 0.2,
        alpha: 0,
        hue: Math.random() < 0.6 ? 45 : 260, // gold or purple
        pulse: Math.random() * Math.PI * 2,
      });
    }
  }

  _bindEvents() {
    window.addEventListener('resize', () => { this._resize(); this._populate(); });
    document.addEventListener('mousemove', e => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
    });
    document.addEventListener('mouseleave', () => {
      this.mouse.x = -9999;
      this.mouse.y = -9999;
    });
  }

  setAIPulse(val) {
    // Call with values 0-1 while AI is responding
    this.aiPulse = Math.max(0, Math.min(1, val));
  }

  _loop() {
    this.animFrame = requestAnimationFrame(() => this._loop());
    this._update();
    this._draw();
  }

  _update() {
    const t = Date.now() * 0.001;
    this.particles.forEach(p => {
      // Pulsing alpha
      p.pulse += 0.02;
      p.alpha = p.baseAlpha + Math.sin(p.pulse) * 0.15 + this.aiPulse * 0.3;

      // Mouse repel
      const dx = p.x - this.mouse.x;
      const dy = p.y - this.mouse.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < this.repelDist) {
        const force = (this.repelDist - dist) / this.repelDist * 0.8;
        p.vx += (dx / dist) * force * 0.15;
        p.vy += (dy / dist) * force * 0.15;
      }

      // AI pulse attraction toward center
      if (this.aiPulse > 0.1) {
        const cx = this.canvas.width / 2;
        const cy = this.canvas.height / 2;
        p.vx += ((cx - p.x) / this.canvas.width) * this.aiPulse * 0.02;
        p.vy += ((cy - p.y) / this.canvas.height) * this.aiPulse * 0.02;
      }

      // Velocity damping
      p.vx *= 0.98;
      p.vy *= 0.98;

      // Movement
      p.x += p.vx;
      p.y += p.vy;

      // Wrap edges
      if (p.x < 0) p.x = this.canvas.width;
      if (p.x > this.canvas.width) p.x = 0;
      if (p.y < 0) p.y = this.canvas.height;
      if (p.y > this.canvas.height) p.y = 0;
    });
  }

  _draw() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw connections
    for (let i = 0; i < this.particles.length; i++) {
      for (let j = i + 1; j < this.particles.length; j++) {
        const a = this.particles[i];
        const b = this.particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < this.connectionDist) {
          const alpha = (1 - dist / this.connectionDist) * 0.18 + this.aiPulse * 0.12;
          this.ctx.beginPath();
          this.ctx.moveTo(a.x, a.y);
          this.ctx.lineTo(b.x, b.y);
          this.ctx.strokeStyle = `hsla(${(a.hue + b.hue) / 2}, 80%, 65%, ${alpha})`;
          this.ctx.lineWidth = 0.6;
          this.ctx.stroke();
        }
      }
    }

    // Draw particles
    this.particles.forEach(p => {
      this.ctx.beginPath();
      this.ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      this.ctx.fillStyle = `hsla(${p.hue}, 80%, 72%, ${p.alpha})`;
      this.ctx.fill();

      // Glow ring for gold particles during AI pulse
      if (this.aiPulse > 0.3 && p.hue === 45) {
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.radius + 3, 0, Math.PI * 2);
        this.ctx.strokeStyle = `hsla(45, 90%, 60%, ${this.aiPulse * 0.3})`;
        this.ctx.lineWidth = 0.5;
        this.ctx.stroke();
      }
    });
  }

  destroy() {
    cancelAnimationFrame(this.animFrame);
    if (this.canvas) this.canvas.getContext('2d').clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
}

// ─────────────────────────────────────────────
// 2. MORPHING ORB SYSTEM (CSS Variables)
// ─────────────────────────────────────────────
class MorphingOrbs {
  constructor() {
    this.orbs = document.querySelectorAll('.orb-morph');
    this.shapes = [
      'polygon(50% 0%, 80% 10%, 100% 35%, 90% 70%, 60% 100%, 30% 95%, 5% 70%, 0% 35%, 20% 8%)',
      'polygon(40% 0%, 85% 5%, 100% 45%, 85% 95%, 50% 100%, 10% 88%, 0% 50%, 15% 10%)',
      'polygon(55% 0%, 90% 15%, 95% 55%, 75% 100%, 35% 98%, 5% 65%, 0% 25%, 25% 3%)',
      'polygon(45% 0%, 95% 20%, 100% 60%, 80% 100%, 30% 100%, 0% 70%, 5% 20%, 25% 0%)',
    ];
    this.idx = 0;
    if (this.orbs.length) this._animate();
  }

  _animate() {
    this.idx = (this.idx + 1) % this.shapes.length;
    this.orbs.forEach((orb, i) => {
      const shapeIdx = (this.idx + i) % this.shapes.length;
      orb.style.clipPath = this.shapes[shapeIdx];
    });
    setTimeout(() => this._animate(), 4000);
  }
}

// ─────────────────────────────────────────────
// 3. SCROLL REVEAL MANAGER
// ─────────────────────────────────────────────
class ScrollReveal {
  constructor() {
    this.observer = new IntersectionObserver(this._onIntersect.bind(this), {
      threshold: 0.12,
      rootMargin: '0px 0px -40px 0px',
    });
    this._init();
  }

  _init() {
    // Auto-target elements with data-reveal
    document.querySelectorAll('[data-reveal]').forEach(el => {
      el.classList.add('sr-hidden');
      this.observer.observe(el);
    });

    // Auto-detect grids for stagger
    document.querySelectorAll('.sr-stagger').forEach(container => {
      Array.from(container.children).forEach((child, i) => {
        child.classList.add('sr-hidden');
        child.style.transitionDelay = `${i * 80}ms`;
        this.observer.observe(child);
      });
    });
  }

  _onIntersect(entries) {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const el = entry.target;
        const dir = el.dataset.reveal || 'up';
        el.classList.remove('sr-hidden');
        el.classList.add(`sr-show-${dir}`);
        this.observer.unobserve(el);
      }
    });
  }

  // Manually add an element to be watched
  watch(el, dir = 'up', delay = 0) {
    el.classList.add('sr-hidden');
    el.style.transitionDelay = `${delay}ms`;
    el.dataset.reveal = dir;
    this.observer.observe(el);
  }
}

// ─────────────────────────────────────────────
// 4. 3D TILT CARDS
// ─────────────────────────────────────────────
class TiltCards {
  constructor(selector = '.tilt-card') {
    this.cards = document.querySelectorAll(selector);
    this._bind();
  }

  _bind() {
    this.cards.forEach(card => {
      card.addEventListener('mousemove', e => this._onMove(e, card));
      card.addEventListener('mouseleave', e => this._onLeave(card));
      card.addEventListener('mouseenter', e => this._onEnter(card));
    });
  }

  _onEnter(card) {
    card.style.transition = 'transform 0.1s ease, box-shadow 0.3s ease';
  }

  _onLeave(card) {
    card.style.transition = 'transform 0.6s cubic-bezier(.03,.98,.52,.99), box-shadow 0.6s ease';
    card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1,1,1)';
    card.style.boxShadow = '';
    const shine = card.querySelector('.tilt-shine');
    if (shine) shine.style.opacity = '0';
  }

  _onMove(e, card) {
    const rect = card.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const rotY = ((x - cx) / cx) * 8;
    const rotX = -((y - cy) / cy) * 8;

    card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale3d(1.02,1.02,1.02)`;
    card.style.boxShadow = `${-rotY * 1.5}px ${rotX * 1.5}px 40px rgba(242,202,80,0.12)`;

    // Shine effect
    let shine = card.querySelector('.tilt-shine');
    if (!shine) {
      shine = document.createElement('div');
      shine.className = 'tilt-shine';
      shine.style.cssText = 'position:absolute;inset:0;border-radius:inherit;pointer-events:none;transition:opacity 0.3s;';
      card.style.position = 'relative';
      card.style.overflow = 'hidden';
      card.appendChild(shine);
    }
    const shineX = (x / rect.width) * 100;
    const shineY = (y / rect.height) * 100;
    shine.style.background = `radial-gradient(circle at ${shineX}% ${shineY}%, rgba(255,255,255,0.08) 0%, transparent 60%)`;
    shine.style.opacity = '1';
  }
}

// ─────────────────────────────────────────────
// 5. TYPEWRITER EFFECT
// ─────────────────────────────────────────────
class Typewriter {
  constructor(el, options = {}) {
    this.el = typeof el === 'string' ? document.querySelector(el) : el;
    if (!this.el) return;
    this.speed = options.speed || 38;
    this.deleteSpeed = options.deleteSpeed || 22;
    this.pauseEnd = options.pauseEnd || 2200;
    this.pauseStart = options.pauseStart || 400;
    this.texts = options.texts || [this.el.textContent];
    this.loop = options.loop !== false;
    this.cursor = options.cursor !== false;
    this.idx = 0;
    this.charIdx = 0;
    this.isDeleting = false;
    this.el.textContent = '';
    if (this.cursor) {
      this.el.style.borderRight = '2px solid #f2ca50';
      this.el.style.animation = 'leviCursorBlink 0.8s step-end infinite';
    }
    this._tick();
  }

  _tick() {
    const text = this.texts[this.idx % this.texts.length];
    if (!this.isDeleting) {
      this.el.textContent = text.slice(0, ++this.charIdx);
      if (this.charIdx === text.length) {
        if (!this.loop && this.idx === this.texts.length - 1) return;
        this.isDeleting = true;
        setTimeout(() => this._tick(), this.pauseEnd);
        return;
      }
    } else {
      this.el.textContent = text.slice(0, --this.charIdx);
      if (this.charIdx === 0) {
        this.isDeleting = false;
        this.idx++;
        setTimeout(() => this._tick(), this.pauseStart);
        return;
      }
    }
    setTimeout(() => this._tick(), this.isDeleting ? this.deleteSpeed : this.speed);
  }
}

// ─────────────────────────────────────────────
// 6. ANIMATED NUMBER COUNTER
// ─────────────────────────────────────────────
class NumberCounter {
  constructor(selector = '[data-count]') {
    this.elements = document.querySelectorAll(selector);
    if (!this.elements.length) return;
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          this._animate(e.target);
          obs.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });
    this.elements.forEach(el => obs.observe(el));
  }

  _animate(el) {
    const target = parseInt(el.dataset.count, 10);
    const suffix = el.dataset.suffix || '';
    const duration = parseInt(el.dataset.duration || '2000', 10);
    const start = Date.now();
    const from = 0;

    const step = () => {
      const elapsed = Date.now() - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease out cubic
      el.textContent = Math.round(from + (target - from) * eased).toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
}

// ─────────────────────────────────────────────
// 7. PAGE TRANSITION SYSTEM
// ─────────────────────────────────────────────
class PageTransitions {
  constructor() {
    this._injectOverlay();
    this._bindLinks();
    this._enterAnimation();
  }

  _injectOverlay() {
    this.overlay = document.createElement('div');
    this.overlay.id = 'levi-page-overlay';
    this.overlay.style.cssText = `
      position: fixed; inset: 0; z-index: 9999; pointer-events: none;
      background: #0e0e12; opacity: 0; transition: opacity 0.35s cubic-bezier(0.4,0,0.2,1);
    `;
    document.body.appendChild(this.overlay);
  }

  _bindLinks() {
    document.addEventListener('click', e => {
      const link = e.target.closest('a[href]');
      if (!link) return;
      const href = link.getAttribute('href');
      if (!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('mailto') || link.target === '_blank') return;
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      this._exit(() => { window.location.href = href; });
    });
  }

  _exit(cb) {
    this.overlay.style.pointerEvents = 'all';
    this.overlay.style.opacity = '1';
    document.body.style.transform = 'scale(0.97)';
    document.body.style.transition = 'transform 0.35s cubic-bezier(0.4,0,0.2,1)';
    setTimeout(cb, 360);
  }

  _enterAnimation() {
    document.body.style.transform = 'scale(0.97)';
    document.body.style.opacity = '0';
    document.body.style.transition = 'none';
    this.overlay.style.opacity = '1';

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.body.style.transition = 'transform 0.5s cubic-bezier(0.16,1,0.3,1), opacity 0.4s ease';
        document.body.style.transform = 'scale(1)';
        document.body.style.opacity = '1';
        this.overlay.style.transition = 'opacity 0.5s ease';
        this.overlay.style.opacity = '0';
        setTimeout(() => { this.overlay.style.pointerEvents = 'none'; }, 500);
      });
    });
  }
}

// ─────────────────────────────────────────────
// 8. CHAT ANIMATION HELPERS
// ─────────────────────────────────────────────
class ChatAnimator {
  constructor() {}

  // Animate a new message bubble appearing
  animateMessage(el, role = 'bot') {
    const origin = role === 'user' ? 'right' : 'left';
    el.style.opacity = '0';
    el.style.transform = `translateX(${origin === 'right' ? '20px' : '-20px'}) translateY(8px)`;
    el.style.transition = 'opacity 0.35s ease, transform 0.35s cubic-bezier(0.34,1.56,0.64,1)';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateX(0) translateY(0)';
      });
    });
  }

  // Animate typing indicator (3 dots with wave)
  createTypingIndicator() {
    const wrap = document.createElement('div');
    wrap.className = 'levi-typing-indicator';
    wrap.innerHTML = `
      <div class="typing-dot" style="animation-delay:0ms"></div>
      <div class="typing-dot" style="animation-delay:160ms"></div>
      <div class="typing-dot" style="animation-delay:320ms"></div>
    `;
    return wrap;
  }

  // Flash/pulse the chat container while AI responds
  startResponsePulse(containerEl, particles) {
    containerEl.classList.add('ai-responding');
    if (particles) particles.setAIPulse(0.8);
    return () => {
      containerEl.classList.remove('ai-responding');
      if (particles) {
        let p = 0.8;
        const fade = setInterval(() => {
          p -= 0.08;
          if (p <= 0) { clearInterval(fade); particles.setAIPulse(0); }
          else particles.setAIPulse(p);
        }, 50);
      }
    };
  }

  // Animate send button press
  animateSend(btn) {
    btn.style.transform = 'scale(0.88)';
    btn.style.transition = 'transform 0.1s';
    setTimeout(() => {
      btn.style.transform = 'scale(1.08)';
      setTimeout(() => {
        btn.style.transform = 'scale(1)';
        btn.style.transition = 'transform 0.3s cubic-bezier(0.34,1.56,0.64,1)';
      }, 100);
    }, 100);
  }
}

// ─────────────────────────────────────────────
// 9. STUDIO CANVAS ANIMATIONS
// ─────────────────────────────────────────────
class StudioAnimator {
  constructor() {}

  // Shimmer loading skeleton on preview
  startShimmer(el) {
    el.classList.add('levi-shimmer');
  }
  stopShimmer(el) {
    el.classList.remove('levi-shimmer');
  }

  // Particle burst when image generates
  burstParticles(originEl, count = 28) {
    const rect = originEl.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;

    for (let i = 0; i < count; i++) {
      const p = document.createElement('div');
      p.style.cssText = `
        position: fixed; width: ${Math.random() * 6 + 3}px; height: ${Math.random() * 6 + 3}px;
        border-radius: 50%; pointer-events: none; z-index: 9999;
        left: ${cx}px; top: ${cy}px;
        background: ${Math.random() < 0.6 ? '#f2ca50' : '#c3c0ff'};
        transition: none;
      `;
      document.body.appendChild(p);
      const angle = (i / count) * Math.PI * 2;
      const dist = Math.random() * 180 + 60;
      const dx = Math.cos(angle) * dist;
      const dy = Math.sin(angle) * dist;

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          p.style.transition = `transform ${0.5 + Math.random() * 0.5}s cubic-bezier(0.165,0.84,0.44,1), opacity 0.6s ease ${0.2 + Math.random() * 0.3}s`;
          p.style.transform = `translate(${dx}px, ${dy}px) scale(0)`;
          p.style.opacity = '0';
        });
      });
      setTimeout(() => p.remove(), 1200);
    }
  }

  // Animated generation progress ring
  animateProgressRing(canvas, onComplete) {
    const ctx = canvas.getContext('2d');
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const r = Math.min(cx, cy) - 10;
    let progress = 0;
    let frame;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      // Background track
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 3;
      ctx.stroke();
      // Progress arc
      const angle = -Math.PI / 2;
      const end = angle + (progress / 100) * Math.PI * 2;
      const grad = ctx.createLinearGradient(cx - r, cy, cx + r, cy);
      grad.addColorStop(0, '#f2ca50');
      grad.addColorStop(1, '#c3c0ff');
      ctx.beginPath();
      ctx.arc(cx, cy, r, angle, end);
      ctx.strokeStyle = grad;
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.stroke();

      progress = Math.min(progress + 0.8, 100);
      if (progress < 100) {
        frame = requestAnimationFrame(draw);
      } else {
        onComplete && onComplete();
      }
    };
    draw();
    return () => cancelAnimationFrame(frame);
  }

  // Image reveal animation
  revealImage(imgEl) {
    imgEl.style.opacity = '0';
    imgEl.style.filter = 'blur(12px)';
    imgEl.style.transform = 'scale(1.04)';
    imgEl.style.transition = 'none';
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        imgEl.style.transition = 'opacity 0.8s ease, filter 0.8s ease, transform 0.8s cubic-bezier(0.16,1,0.3,1)';
        imgEl.style.opacity = '1';
        imgEl.style.filter = 'blur(0)';
        imgEl.style.transform = 'scale(1)';
      });
    });
  }
}

// ─────────────────────────────────────────────
// 10. MOOD SELECTOR RIPPLE
// ─────────────────────────────────────────────
class MoodRipple {
  constructor(selector = '.mood-chip, .style-btn') {
    document.querySelectorAll(selector).forEach(btn => {
      btn.addEventListener('click', e => this._ripple(e, btn));
    });
  }

  _ripple(e, btn) {
    const r = document.createElement('span');
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    r.style.cssText = `
      position: absolute; border-radius: 50%; pointer-events: none;
      width: ${size}px; height: ${size}px;
      left: ${e.clientX - rect.left - size / 2}px;
      top: ${e.clientY - rect.top - size / 2}px;
      background: rgba(242,202,80,0.25);
      transform: scale(0); opacity: 1;
      transition: transform 0.45s cubic-bezier(0.4,0,0.2,1), opacity 0.35s ease 0.1s;
    `;
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(r);
    requestAnimationFrame(() => {
      r.style.transform = 'scale(1)';
      r.style.opacity = '0';
    });
    setTimeout(() => r.remove(), 500);
  }
}

// ─────────────────────────────────────────────
// 11. LIVE GRADIENT BACKGROUND (responds to scroll + time)
// ─────────────────────────────────────────────
class LiveBackground {
  constructor() {
    this.t = 0;
    this.scrollY = 0;
    window.addEventListener('scroll', () => { this.scrollY = window.scrollY; }, { passive: true });
    this._update();
  }

  _update() {
    requestAnimationFrame(() => this._update());
    this.t += 0.003;
    const hue1 = 40 + Math.sin(this.t) * 8;         // gold range
    const hue2 = 260 + Math.cos(this.t * 0.7) * 15; // purple range
    const shift = (this.scrollY / document.body.scrollHeight) * 20;
    document.documentElement.style.setProperty('--live-bg-hue1', `${hue1 + shift}`);
    document.documentElement.style.setProperty('--live-bg-hue2', `${hue2 - shift * 0.5}`);
  }
}

// ─────────────────────────────────────────────
// 12. FEEDBACK TOAST (enhanced)
// ─────────────────────────────────────────────
class LeviToast {
  constructor() {
    this.queue = [];
    this.active = false;
    this._injectStyles();
  }

  show(msg, type = 'success', duration = 3200) {
    this.queue.push({ msg, type, duration });
    if (!this.active) this._next();
  }

  _next() {
    if (!this.queue.length) { this.active = false; return; }
    this.active = true;
    const { msg, type, duration } = this.queue.shift();
    const t = document.createElement('div');
    t.className = `levi-toast levi-toast-${type}`;
    t.innerHTML = `<span class="levi-toast-icon">${type === 'error' ? '✕' : type === 'warning' ? '⚠' : '✓'}</span><span class="levi-toast-msg">${msg}</span>`;
    document.body.appendChild(t);

    requestAnimationFrame(() => requestAnimationFrame(() => t.classList.add('levi-toast-show')));
    setTimeout(() => {
      t.classList.remove('levi-toast-show');
      setTimeout(() => { t.remove(); this._next(); }, 400);
    }, duration);
  }

  _injectStyles() {
    if (document.getElementById('levi-toast-styles')) return;
    const s = document.createElement('style');
    s.id = 'levi-toast-styles';
    s.textContent = `
      .levi-toast {
        position: fixed; bottom: 5rem; left: 50%; transform: translateX(-50%) translateY(16px);
        opacity: 0; z-index: 9998; pointer-events: none;
        background: rgba(19,19,23,0.92); border: 0.5px solid rgba(242,202,80,0.35);
        backdrop-filter: blur(20px); border-radius: 9999px;
        display: flex; align-items: center; gap: 10px;
        padding: 10px 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        transition: opacity 0.35s ease, transform 0.35s cubic-bezier(0.34,1.56,0.64,1);
        font-family: 'Plus Jakarta Sans', sans-serif; font-size: 12px;
        font-weight: 600; letter-spacing: 0.04em; color: #e5e1e7;
      }
      .levi-toast-show { opacity: 1; transform: translateX(-50%) translateY(0); }
      .levi-toast-error { border-color: rgba(255,180,171,0.35); }
      .levi-toast-warning { border-color: rgba(242,202,80,0.5); }
      .levi-toast-icon { font-size: 14px; color: #f2ca50; }
      .levi-toast-error .levi-toast-icon { color: #fca5a5; }
    `;
    document.head.appendChild(s);
  }
}

// ─────────────────────────────────────────────
// 13. INJECT GLOBAL CSS
// ─────────────────────────────────────────────
function injectAnimationCSS() {
  if (document.getElementById('levi-anim-css')) return;
  const s = document.createElement('style');
  s.id = 'levi-anim-css';
  s.textContent = `
    /* Cursor blink */
    @keyframes leviCursorBlink { 0%,100%{border-color:#f2ca50} 50%{border-color:transparent} }

    /* Scroll reveal hidden states */
    .sr-hidden {
      opacity: 0 !important;
      transition: opacity 0.6s ease, transform 0.6s cubic-bezier(0.16,1,0.3,1) !important;
    }
    [data-reveal="up"].sr-hidden    { transform: translateY(32px); }
    [data-reveal="down"].sr-hidden  { transform: translateY(-32px); }
    [data-reveal="left"].sr-hidden  { transform: translateX(-32px); }
    [data-reveal="right"].sr-hidden { transform: translateX(32px); }
    [data-reveal="scale"].sr-hidden { transform: scale(0.88); }
    [data-reveal="fade"].sr-hidden  { transform: none; }
    .sr-show-up, .sr-show-down, .sr-show-left, .sr-show-right, .sr-show-scale, .sr-show-fade {
      opacity: 1 !important; transform: none !important;
    }

    /* Typing indicator */
    .levi-typing-indicator {
      display: inline-flex; align-items: center; gap: 5px;
      padding: 12px 16px;
    }
    .typing-dot {
      width: 6px; height: 6px; border-radius: 50%;
      background: #f2ca50;
      animation: leviTypingWave 1.2s ease-in-out infinite;
    }
    @keyframes leviTypingWave {
      0%,60%,100% { transform: translateY(0); opacity: 0.4; }
      30% { transform: translateY(-6px); opacity: 1; }
    }

    /* Shimmer skeleton */
    .levi-shimmer {
      background: linear-gradient(90deg,
        rgba(255,255,255,0.04) 25%,
        rgba(242,202,80,0.08) 50%,
        rgba(255,255,255,0.04) 75%
      );
      background-size: 200% 100%;
      animation: leviShimmer 1.6s ease-in-out infinite;
    }
    @keyframes leviShimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }

    /* AI responding pulse */
    .ai-responding {
      animation: leviResponsePulse 1.8s ease-in-out infinite;
    }
    @keyframes leviResponsePulse {
      0%,100% { box-shadow: 0 0 0 0 rgba(242,202,80,0); }
      50% { box-shadow: 0 0 0 6px rgba(242,202,80,0.08); }
    }

    /* Orb morphing */
    .orb-morph {
      transition: clip-path 4s cubic-bezier(0.4,0,0.2,1);
    }

    /* Live background gradient variables */
    :root {
      --live-bg-hue1: 40;
      --live-bg-hue2: 260;
    }

    /* Smooth focus rings */
    *:focus-visible {
      outline: 2px solid rgba(242,202,80,0.6);
      outline-offset: 3px;
    }

    /* Hover states for nav links */
    nav a { transition: color 0.2s ease, opacity 0.2s ease; }

    /* Glass panel hover */
    .glass-panel, .glass-card {
      transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    .glass-panel:hover {
      border-color: rgba(242,202,80,0.12) !important;
      box-shadow: 0 0 40px rgba(242,202,80,0.04);
    }

    /* Button press */
    .btn-gold:active { transform: scale(0.96) !important; }

    /* Feed card image hover */
    .gallery-card img, .glass-card img {
      transition: transform 0.7s cubic-bezier(0.4,0,0.2,1), filter 0.5s ease;
    }
    .gallery-card:hover img, .glass-card:hover img {
      transform: scale(1.06);
      filter: brightness(1.05);
    }

    /* Quote card appear */
    @keyframes leviQuoteAppear {
      from { opacity: 0; transform: translateY(16px) scale(0.97); }
      to   { opacity: 1; transform: translateY(0) scale(1); }
    }
    .quote-appear { animation: leviQuoteAppear 0.4s cubic-bezier(0.34,1.56,0.64,1) both; }

    /* Floating nav island */
    nav > div {
      transition: box-shadow 0.3s ease, background 0.3s ease;
    }

    /* Gradient text animation */
    .gold-text, .gold-gradient-text {
      background-size: 200% auto;
      animation: leviGoldShift 5s linear infinite;
    }
    @keyframes leviGoldShift {
      0%  { background-position: 0% center; }
      50% { background-position: 100% center; }
      100%{ background-position: 0% center; }
    }

    /* Mood chip active state */
    .mood-chip.active {
      animation: leviMoodPop 0.3s cubic-bezier(0.34,1.56,0.64,1);
    }
    @keyframes leviMoodPop {
      0%  { transform: scale(1); }
      50% { transform: scale(1.12); }
      100%{ transform: scale(1); }
    }

    /* Scroll-triggered nav shrink (added via JS class) */
    .nav-scrolled > div {
      box-shadow: 0 8px 30px rgba(0,0,0,0.5) !important;
    }
  `;
  document.head.appendChild(s);
}

// ─────────────────────────────────────────────
// 14. NAV SCROLL BEHAVIOUR
// ─────────────────────────────────────────────
function initNavScroll() {
  const nav = document.querySelector('nav.fixed');
  if (!nav) return;
  let lastY = 0;
  window.addEventListener('scroll', () => {
    const y = window.scrollY;
    if (y > 60) nav.classList.add('nav-scrolled');
    else nav.classList.remove('nav-scrolled');
    // Hide nav on fast scroll down, show on scroll up
    if (y > lastY + 8 && y > 200) nav.style.transform = 'translateY(-120%)';
    else nav.style.transform = 'translateY(0)';
    nav.style.transition = 'transform 0.4s cubic-bezier(0.4,0,0.2,1)';
    lastY = y;
  }, { passive: true });
}

// ─────────────────────────────────────────────
// 15. AUTO-INIT ON DOMContentLoaded
// ─────────────────────────────────────────────
const LEVI = {};

document.addEventListener('DOMContentLoaded', () => {
  injectAnimationCSS();

  // Universal across all pages
  LEVI.pageTransitions = new PageTransitions();
  LEVI.scrollReveal    = new ScrollReveal();
  LEVI.tiltCards       = new TiltCards('.glass-card, .glass-panel, .tilt-card');
  LEVI.counter         = new NumberCounter('[data-count]');
  LEVI.moodRipple      = new MoodRipple('.mood-chip, .style-btn, .filter-btn');
  LEVI.liveBackground  = new LiveBackground();
  LEVI.toast           = new LeviToast();
  initNavScroll();

  // Override showToast globally with the new system
  window.showToast = (msg, type = 'success') => LEVI.toast.show(msg, type);

  // Particle canvas — inject into body if not present
  const page = document.body.dataset.page || location.pathname.split('/').pop().replace('.html', '');

  if (!document.getElementById('levi-particle-canvas')) {
    const canvas = document.createElement('canvas');
    canvas.id = 'levi-particle-canvas';
    canvas.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:0;opacity:0.6;';
    document.body.insertBefore(canvas, document.body.firstChild);
  }
  LEVI.particles = new ParticleConstellation('levi-particle-canvas');

  // Morphing orbs: add class to existing orbs
  document.querySelectorAll('.orb-1, .orb-2').forEach(el => el.classList.add('orb-morph'));
  LEVI.morphOrbs = new MorphingOrbs();

  // Page-specific inits
  if (page === 'index' || page === '') {
    // Typewriter on hero headline
    const hero = document.querySelector('h1 .gold-text, h1 .gold-gradient-text');
    if (hero) {
      const original = hero.textContent;
      LEVI.typewriter = new Typewriter(hero, {
        texts: [original, 'Creates Wisdom.', 'Synthesizes Art.', 'Inspires Souls.'],
        loop: true, speed: 55, deleteSpeed: 28, pauseEnd: 2800,
      });
    }
    // Mark all feature cards for scroll reveal
    document.querySelectorAll('.feature-card, .glass-card').forEach((el, i) => {
      LEVI.scrollReveal.watch(el, 'up', i * 80);
    });
  }

  if (page === 'chat') {
    LEVI.chatAnimator = new ChatAnimator();
    LEVI.studioAnimator = null;
    // Patch the global sendMessage to animate
    const origSend = window.sendMessage;
    if (typeof origSend === 'function') {
      window.sendMessage = async function(...args) {
        const btn = document.getElementById('send-btn');
        if (btn) LEVI.chatAnimator.animateSend(btn);
        const msgs = document.getElementById('messages');
        const stopPulse = msgs ? LEVI.chatAnimator.startResponsePulse(msgs, LEVI.particles) : () => {};
        await origSend.apply(this, args);
        stopPulse();
      };
    }
    // Patch appendMsg to animate new messages
    const origAppend = window.appendMsg;
    if (typeof origAppend === 'function') {
      window.appendMsg = function(content, role) {
        const el = origAppend.apply(this, arguments);
        if (el && LEVI.chatAnimator) LEVI.chatAnimator.animateMessage(el, role);
        return el;
      };
    }
  }

  if (page === 'studio') {
    LEVI.studioAnimator = new StudioAnimator();
    // Patch synthesize to use animations
    const origSynth = window.synthesize;
    if (typeof origSynth === 'function') {
      window.synthesize = async function(...args) {
        const preview = document.getElementById('preview-wrap');
        if (preview) LEVI.studioAnimator.startShimmer(preview);
        LEVI.particles && LEVI.particles.setAIPulse(0.9);
        try {
          await origSynth.apply(this, args);
          // Burst + reveal after generation
          const img = document.getElementById('preview-img');
          if (img && preview) {
            LEVI.studioAnimator.stopShimmer(preview);
            LEVI.studioAnimator.revealImage(img);
            LEVI.studioAnimator.burstParticles(img);
          }
        } finally {
          if (preview) LEVI.studioAnimator.stopShimmer(preview);
          let p = 0.9;
          const fade = setInterval(() => {
            p -= 0.1;
            if (p <= 0) { clearInterval(fade); LEVI.particles && LEVI.particles.setAIPulse(0); }
            else LEVI.particles && LEVI.particles.setAIPulse(p);
          }, 80);
        }
      };
    }
  }

  // Scroll-reveal all main content sections
  document.querySelectorAll('section, article, .glass-panel:not(nav *)').forEach((el, i) => {
    if (!el.dataset.reveal) {
      el.dataset.reveal = 'up';
      LEVI.scrollReveal.watch(el, 'up', 0);
    }
  });

  console.log('[LEVI Animations] Engine v2.0 ready');
});

// Expose globally
window.LEVI = LEVI;
export { ParticleConstellation, ScrollReveal, TiltCards, Typewriter, NumberCounter, PageTransitions, ChatAnimator, StudioAnimator, MoodRipple, LeviToast, LiveBackground };
