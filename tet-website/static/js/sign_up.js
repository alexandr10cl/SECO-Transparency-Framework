document.querySelector('.signinForm').addEventListener('submit', function (event) {
    const password = document.getElementById('passw');
    const confirmPassword = document.getElementById('confpass');

    if (password.value !== confirmPassword.value) {
        event.preventDefault(); // Impede o envio do formulário

        // Adiciona classes para destacar os campos com erro
        password.classList.add('input-error');
        confirmPassword.classList.add('input-error');

        // Exibe uma mensagem de erro abaixo do campo de confirmação
        const errorMessage = document.getElementById('error-message');
        if (!errorMessage) {
            const message = document.createElement('p');
            message.id = 'error-message';
            message.textContent = 'Passwords do not match.';
            message.style.color = 'red';
            confirmPassword.parentNode.insertBefore(message, confirmPassword.nextSibling);
        }
    } else {
        // Remove o destaque de erro caso as senhas coincidam
        password.classList.remove('input-error');
        confirmPassword.classList.remove('input-error');
        const errorMessage = document.getElementById('error-message');
        if (errorMessage) {
            errorMessage.remove();
        }
    }
});
