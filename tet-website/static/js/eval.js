document.addEventListener("DOMContentLoaded", () => {
    const loader = document.getElementById("page-loader");

    // Modal functionality
    const modals = document.querySelectorAll(".modal");
    const closeButtons = document.querySelectorAll(".modal .close");

    // Open modal for guidelines
    document.querySelectorAll(".guidelines button").forEach(button => {
        button.addEventListener("click", () => {
            const modalId = `modalG${button.id.replace("openModal", "")}`;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove("inv");
                modal.style.display = "flex"; 
            } else {
                console.error(`Modal with ID ${modalId} not found.`);
            }
        });
    });

    // Open modal for tasks
    document.querySelectorAll(".tasks button").forEach(button => {
        button.addEventListener("click", () => {
            const modalId = `modalT${button.id.replace("openModal", "")}`;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove("inv");
                modal.style.display = "flex";
            } else {
                console.error(`Modal with ID ${modalId} not found.`);
            }
        });
    });

    // Open modal for collects
    document.querySelectorAll(".cData button").forEach(button => {
        button.addEventListener("click", () => {
            const modalId = `modalC${button.id.replace("openModal", "")}`;
            const modal = document.getElementById(modalId);
            if (modal) {
                modal.classList.remove("inv");
                modal.style.display = "flex";
            } else {
                console.error(`Modal with ID ${modalId} not found.`);
            }
        });
    });

    // Open modal for settings
    const settingsButton = document.getElementById("openModalSettings");
    if (settingsButton) {
        settingsButton.addEventListener("click", () => {
            const modal = document.getElementById("modalConfig");
            if (modal) {
                modal.classList.remove("inv");
                modal.style.display = "flex";
            } else {
                console.error("Settings modal not found.");
            }
        });
    }

    // Close modals when clicking the close button
    closeButtons.forEach(button => {
        button.addEventListener("click", () => {
            const modal = button.closest(".modal");
            if (modal) {
                modal.classList.add("inv");
                modal.style.display = "none"; // Garantir que o modal seja ocultado
            }
        });
    });

    // Close modals when clicking outside the modal content
    window.addEventListener("click", (e) => {
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.classList.add("inv");
                modal.style.display = "none";
            }
        });
    });

    // Show loading overlay immediately when clicking dashboard button
    const dashboardBtn = document.querySelector('.dashboard-btn[href*="eval_dashboard"]');
    if (loader && dashboardBtn) {
        dashboardBtn.addEventListener('click', () => {
            loader.style.display = 'flex';
        });
    }

    // Handle delete evaluation form submission
    const deleteForms = document.querySelectorAll('.delete-evaluation-form');
    deleteForms.forEach(form => {
        form.addEventListener('submit', (event) => {
            const message = form.dataset.confirmMessage || 'Are you sure you want to delete this evaluation? This action cannot be undone.';
            if (!window.confirm(message)) {
                event.preventDefault();
                return;
            }

            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('is-loading');
                submitBtn.innerHTML = '<span class="btn-icon">⏳</span>Deleting...';
            }

            if (loader) {
                loader.style.display = 'flex';
                const title = loader.querySelector('h3');
                const subtitle = loader.querySelector('p');
                if (title) {
                    title.textContent = 'Deleting Evaluation...';
                }
                if (subtitle) {
                    subtitle.textContent = 'Cleaning up related data';
                }
            }
        });
    });
});




