document.querySelectorAll('.sidebarG a').forEach(link => {
    link.addEventListener('click', function (e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        const offset = 70; // Altura da navbar
        const elementPosition = targetElement.getBoundingClientRect().top + window.scrollY;
        window.scrollTo({
            top: elementPosition - offset,
            behavior: 'smooth'
        });
    });
});

document.querySelectorAll('.sidebarG ul li').forEach(li => {
    if (li.querySelector('a').classList.contains('active')) {
        console.log(`The active sidebar item is: ${li.textContent.trim()}`);
    }
});

// Função para verificar qual guideline está visível
function activateLinkOnScroll() {
    const offset = 70; // Altura da navbar
    const guidelines = document.querySelectorAll('.guideline');
    const links = document.querySelectorAll('.sidebarG ul li a');

    let activeGuidelineId = null;

    guidelines.forEach(guideline => {
        const rect = guideline.getBoundingClientRect();
        if (rect.top <= offset && rect.bottom > offset) {
            activeGuidelineId = guideline.id;
        }
    });

    links.forEach(link => {
        const targetId = link.getAttribute('href').substring(1);
        if (targetId === activeGuidelineId) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Adiciona o evento de scroll
window.addEventListener('scroll', activateLinkOnScroll);

