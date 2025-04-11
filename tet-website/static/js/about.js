const cards = document.querySelectorAll('.card-full');

cards.forEach((card) => {
    let isMouseOver = false;

    card.addEventListener("mouseenter", () => {
        isMouseOver = true;

        const cardRect = card.getBoundingClientRect();

        cards.forEach((otherCard) => {
            if (otherCard !== card) {
                const otherCardRect = otherCard.getBoundingClientRect();

                // Verifica se o card está à esquerda ou à direita
                if (otherCardRect.left < cardRect.left) {
                    // Move para a esquerda
                    otherCard.style.transform = "translateX(-100px)";
                } else {
                    // Move para a direita
                    otherCard.style.transform = "translateX(100px)";
                }

                otherCard.style.transition = "transform 0.2s ease-in-out"; // Transição suave
            }
        });
    });

    card.addEventListener("mouseleave", () => {
        isMouseOver = false;
        card.style.transform = ""; // Reseta a transformação ao sair

        cards.forEach((otherCard) => {
            if (otherCard !== card) {
                otherCard.style.transform = ""; // Reseta a posição dos outros cards
            }
        });
    });

    card.addEventListener("mousemove", (e) => {
        if (!isMouseOver) return;

        const { width, height, left, top } = card.getBoundingClientRect();
        
        // Captura a posição do mouse dentro da div
        const x = (e.clientX - (left + width / 2)) / width;
        const y = (e.clientY - (top + height / 2)) / height;

        // Define o ângulo de inclinação (quanto maior o valor, mais inclina)
        const targetX = -y * 20; // Inverte para manter a lógica intuitiva
        const targetY = x * 20;

        card.style.transition = "transform 0.1s ease-out"; // Adiciona uma transição suave
        card.style.transform = `perspective(1000px) rotateX(${targetX}deg) rotateY(${targetY}deg) scale(2)`;
    });
});