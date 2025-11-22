// Sign In Form Loading State
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('signinForm');
    const submitBtn = document.getElementById('submitBtn');
    
    if (form && submitBtn) {
        form.addEventListener('submit', function(e) {
            // Only show loading if form is valid
            if (form.checkValidity()) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    }
});


