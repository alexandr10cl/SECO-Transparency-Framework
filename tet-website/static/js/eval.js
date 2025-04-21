document.addEventListener("DOMContentLoaded", () => {
    console.log("teste");

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
                modal.style.display = "block"; // Garantir que o modal seja exibido
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
                modal.style.display = "block";
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
                modal.style.display = "block";
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
                modal.style.display = "block";
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
});




