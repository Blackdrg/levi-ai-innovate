// pricing.js - Subscription and Payment flow for LEVI AI
const PLANS = {
    pro: { amount: 29900, name: 'LEVI Pro', description: '100 credits per month' },
    creator: { amount: 59900, name: 'LEVI Creator', description: '500 credits per month' }
};

document.addEventListener('DOMContentLoaded', () => {
    // Initial UI check for exhausted state
    if (window.location.search.includes('exhausted=true')) {
        setTimeout(() => {
            if (window.ui && window.ui.showWarning) {
                window.ui.showWarning("Your credits have been spent. Choose a plan to continue your journey.");
            }
        }, 500);
    }
});

async function subscribe(plan) {
    try {
        await window.waitForToken();
        const token = window.levi_user_token;
        if (!token) {
            if (window.ui) window.ui.showWarning('Please sign in to subscribe.');
            setTimeout(() => window.location.href = 'auth.html', 1500);
            return;
        }

        const user = JSON.parse(localStorage.getItem('levi_user') || '{}');
        const btnId = `${plan}-btn`;
        const btn = document.getElementById(btnId);
        
        if (btn) {
            btn.disabled = true;
            btn.dataset.originalText = btn.textContent;
            btn.textContent = 'Preparing Gateway…';
        }

        if (window.ui && window.ui.showLoader) window.ui.showLoader();

        // 1. Create Order on Backend
        const d = await window.api.apiFetch('/user/payments/create_order', {
            method: "POST",
            body: { plan }
        });

        if (!d || !d.order_id) throw new Error("Could not initialize payment gateway.");

        const options = {
            key: d.key_id || 'rzp_test_placeholder',
            amount: PLANS[plan].amount,
            currency: 'INR',
            name: 'LEVI-AI',
            description: PLANS[plan].description,
            order_id: d.order_id,
            prefill: {
                name: user.username || '',
                email: user.email || ''
            },
            theme: { color: '#f2ca50' },
            handler: async function (response) {
                if (window.ui && window.ui.showLoader) window.ui.showLoader();
                try {
                    // 2. Verify Payment on Backend
                    const vd = await window.api.apiFetch('/user/payments/verify_payment', {
                        method: 'POST',
                        body: response
                    });

                    if (vd.success) {
                        if (window.ui) window.ui.showSuccess('Celestial upgrade complete! Your plan is now active.');
                        if (window.syncUser) await window.syncUser();
                        setTimeout(() => window.location.href = 'my-gallery.html', 2000);
                    } else {
                        throw new Error(vd.error || 'Payment verification failed.');
                    }
                } catch (e) {
                    console.error("[Payment] Verification error:", e);
                    if (window.ui) window.ui.showError('Verification failed. Please contact support.');
                } finally {
                    if (window.ui && window.ui.hideLoader) window.ui.hideLoader();
                }
            },
            modal: {
                ondismiss: function() {
                    if (btn) {
                        btn.disabled = false;
                        btn.textContent = btn.dataset.originalText;
                    }
                    if (window.ui && window.ui.hideLoader) window.ui.hideLoader();
                }
            }
        };

        const rzp = new Razorpay(options);
        rzp.on('payment.failed', e => {
            if (window.ui) window.ui.showError(`Payment failed: ${e.error.description}`);
        });
        rzp.open();

    } catch (e) {
        console.error("[Payment] Error:", e);
        if (window.ui) window.ui.showError(e.message || 'Payment failed to initialize.');
        const btn = document.getElementById(`${plan}-btn`);
        if (btn) {
            btn.disabled = false;
            btn.textContent = btn.dataset.originalText || 'Try Again';
        }
    } finally {
        if (window.ui && window.ui.hideLoader) window.ui.hideLoader();
    }
}

// Attach to window for the onclick handlers in HTML
window.subscribe = subscribe;
