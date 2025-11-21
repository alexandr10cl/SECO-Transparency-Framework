document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('signupForm');
    const submitBtn = document.getElementById('submitBtn');
    const password = document.getElementById('passw');
    const confirmPassword = document.getElementById('confpass');

    if (form && submitBtn) {
        form.addEventListener('submit', function (event) {
            if (password && confirmPassword && password.value !== confirmPassword.value) {
                event.preventDefault();

                // Add error classes
                password.classList.add('input-error');
                confirmPassword.classList.add('input-error');

                // Display error message
                const errorMessage = document.getElementById('error-message');
                if (!errorMessage) {
                    const message = document.createElement('p');
                    message.id = 'error-message';
                    message.textContent = 'Passwords do not match.';
                    message.style.color = 'red';
                    message.setAttribute('role', 'alert');
                    confirmPassword.parentNode.insertBefore(message, confirmPassword.nextSibling);
                }
            } else {
                // Remove error highlighting if passwords match
                if (password) password.classList.remove('input-error');
                if (confirmPassword) confirmPassword.classList.remove('input-error');
                const errorMessage = document.getElementById('error-message');
                if (errorMessage) {
                    errorMessage.remove();
                }

                // Show loading state if form is valid
                if (form.checkValidity()) {
                    submitBtn.classList.add('loading');
                    submitBtn.disabled = true;
                }
            }
        });
    }
});
