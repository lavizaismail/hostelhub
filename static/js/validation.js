// ============================================
// HOSTELHUB - Form Validation
// ============================================

// Email validation
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Phone validation (Indian format)
function validatePhone(phone) {
    const re = /^[6-9]\d{9}$/;
    return re.test(phone);
}

// Password strength checker
function checkPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 10) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z\d]/.test(password)) strength++;
    
    return strength;
}

// Real-time validation
document.addEventListener('DOMContentLoaded', function() {
    // Email fields
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validateEmail(this.value)) {
                this.style.borderColor = 'var(--danger)';
                showError(this, 'Please enter a valid email');
            } else {
                this.style.borderColor = 'var(--border)';
                hideError(this);
            }
        });
    });
    
    // Phone fields
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value && !validatePhone(this.value)) {
                this.style.borderColor = 'var(--danger)';
                showError(this, 'Please enter a valid 10-digit phone number');
            } else {
                this.style.borderColor = 'var(--border)';
                hideError(this);
            }
        });
    });
    
    // Password confirmation
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    if (passwordInputs.length === 2) {
        passwordInputs[1].addEventListener('blur', function() {
            if (this.value !== passwordInputs[0].value) {
                this.style.borderColor = 'var(--danger)';
                showError(this, 'Passwords do not match');
            } else {
                this.style.borderColor = 'var(--border)';
                hideError(this);
            }
        });
    }
});

function showError(input, message) {
    hideError(input);
    const error = document.createElement('small');
    error.className = 'error-text';
    error.style.color = 'var(--danger)';
    error.style.fontSize = '0.75rem';
    error.textContent = message;
    input.parentNode.appendChild(error);
}

function hideError(input) {
    const error = input.parentNode.querySelector('.error-text');
    if (error) error.remove();
}

console.log('Validation JS Loaded ✅');
