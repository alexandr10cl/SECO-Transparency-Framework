function openModal(id) {
    const modal = document.getElementById('gModal');
    const loading = document.getElementById('modal-loading');
    const mainContent = document.getElementById('modal-main-content');

    if (!modal) {
        console.error('Elemento #gModal não encontrado no DOM');
        return;
    }
    // Mostra o modal e o indicador de carregamento, esconde o conteúdo
    modal.classList.remove('inv');
    if (loading) loading.style.display = 'block';
    if (mainContent) mainContent.style.display = 'none';

    fetch(`/api/guideline/${id}`)
        .then(response => response.json())
        .then(g => {
            // Título e descrição
            document.getElementById('modal-title').textContent = `G${g.guidelineID}: ${g.title}`;
            document.getElementById('modal-description').textContent = g.description;

            // Helpers
            const fillList = (elementID, items, getText) => {
                const ul = document.getElementById(elementID);
                if (!ul) {
                    console.error(`Elemento #${elementID} não encontrado no DOM`);
                    return;
                }
                ul.innerHTML = ''; // Limpa a lista antes de preencher
                items.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = getText(item);
                    ul.appendChild(li);
                });
            };

            fillList('modal-processes', g.seco_processes, p => p.description);
            fillList('modal-dimensions', g.seco_dimensions, d => d.name);
            fillList('modal-cond', g.conditioning_factors, cf => cf.description);
            fillList('modal-dx', g.dx_factors, f => f.description);

            // Seccess Criteria
            const scContainer = document.getElementById('modal-ksc');
            if (!scContainer) {
                console.error('Elemento #modal-ksc não encontrado no DOM');
            } else {
                scContainer.innerHTML = ''; // Limpa o container antes de preencher
                g.key_success_criteria.forEach(ksc => {
                    const div = document.createElement('div');
                    div.className = 'success-criterion';

                    const title = document.createElement('h4');
                    title.textContent = ksc.title;
                    div.appendChild(title);

                    const desc = document.createElement('p');
                    desc.textContent = ksc.description;
                    div.appendChild(desc);

                    ksc.examples.forEach(e => {
                        const ex = document.createElement('div');
                        ex.className = 'example';
                        ex.innerHTML = `<strong>Example:</strong> ${e.description}`;
                        div.appendChild(ex);
                    });

                    scContainer.appendChild(div);
                });
            }

            // Esconde o loading e mostra o conteúdo
            if (loading) loading.style.display = 'none';
            if (mainContent) mainContent.style.display = 'block';
        })
        .catch(error => {
            if (loading) loading.style.display = 'none';
            if (mainContent) mainContent.style.display = 'block';
            alert('Erro ao carregar guideline.');
            console.error(error);
        });
}

function closeModal() {
    // Fecha todos os modais abertos
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.classList.add('inv'); // Esconde o modal
    });
}

// Fecha o modal ao clicar fora dele
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.classList.add('inv'); // Esconde o modal
        }
    });
};

