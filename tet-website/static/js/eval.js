document.addEventListener("DOMContentLoaded", () => {

    const dropdownTglG = document.getElementById("dropdown-toggleG");
    const dropdownMenuG = document.getElementById("dropdown-menuG");
    const arrowG = document.getElementById("arrowG");
    const dropdownTglT = document.getElementById("dropdown-toggleT");
    const dropdownMenuT = document.getElementById("dropdown-menuT");
    const arrowT = document.getElementById("arrowT");

    dropdownTglG.addEventListener("click", () => {
        arrowG.classList.toggle("active");
        dropdownMenuG.classList.toggle("show");
    });

    dropdownTglT.addEventListener("click", () => {
        arrowT.classList.toggle("active");
        dropdownMenuT.classList.toggle("show");
    });

    // Modal functionality
    const modals = document.querySelectorAll(".modal");
    const closeButtons = document.querySelectorAll(".modal .close");

    // Open modal for guidelines
    document.querySelectorAll(".dropdown-itemG button").forEach(button => {
        button.addEventListener("click", () => {
            const modalId = `modalG${button.id.replace("openModal", "")}`;
            document.getElementById(modalId).classList.remove("inv");
        });
    });

    // Open modal for tasks
    document.querySelectorAll(".dropdown-itemT button").forEach(button => {
        button.addEventListener("click", () => {
            const modalId = `modalT${button.id.replace("openModal", "")}`;
            document.getElementById(modalId).classList.remove("inv");
        });
    });

    // Open modal for settings
    document.getElementById("openModalSettings").addEventListener("click", () => {
        document.getElementById("modalConfig").classList.remove("inv");
    });

    // Close modals when clicking the close button
    closeButtons.forEach(button => {
        button.addEventListener("click", () => {
            button.closest(".modal").classList.add("inv");
        });
    });

    // Close modals when clicking outside the modal content
    window.addEventListener("click", (e) => {
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.classList.add("inv");
            }
        });
    });

});




