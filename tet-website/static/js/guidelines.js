function openModal(guidelineID) {
    const modal = document.getElementById(`gModal${guidelineID}`);
    if (modal) {
        modal.style.display = 'block'; // Exibe o modal
    }
}

function closeModal() {
    // Fecha todos os modais abertos
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.style.display = 'none'; // Esconde o modal
    });
}

// Fecha o modal ao clicar fora dele
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none'; // Esconde o modal
        }
    });
};

