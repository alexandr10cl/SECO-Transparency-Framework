function openModal(id) {
    const modal = document.getElementById('gModal');
    const loading = document.getElementById('modal-loading');
    const mainContent = document.getElementById('modal-main-content');

    if (!modal) {
        console.error('Elemento #gModal não encontrado no DOM');
        return;
    }
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    
    // Mostra o modal e o indicador de carregamento, esconde o conteúdo
    modal.classList.remove('inv');
    modal.setAttribute('aria-hidden', 'false');
    if (loading) loading.style.display = 'block';
    if (mainContent) mainContent.style.display = 'none';
    
    // Focus trap - focus on close button
    const closeBtn = modal.querySelector('.close');
    if (closeBtn) {
        setTimeout(() => closeBtn.focus(), 100);
    }

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

            console.log('agora vamos para as notas');

            // Notes
            if (g.notes && g.notes.length > 0) {
                    const notesContainer = document.getElementById('modal-notes');
                    if (notesContainer) {
                        notesContainer.innerHTML = ''; // Limpa o container antes de preencher
                        const note = document.createElement('p');
                        note.className = 'note';
                        note.textContent = g.notes;
                        notesContainer.appendChild(note);
                    } else {
                        console.error('Elemento #modal-notes não encontrado no DOM');
                    }
                }

            // Esconde o loading e mostra o conteúdo
            if (loading) loading.style.display = 'none';
            if (mainContent) mainContent.style.display = 'block';
        })
        .catch(error => {
            if (loading) loading.style.display = 'none';
            if (mainContent) {
                mainContent.style.display = 'block';
                mainContent.innerHTML = `
                    <div style="text-align: center; padding: 2rem;">
                        <h3 style="color: #dc2626; margin-bottom: 1rem;">Error Loading Guideline</h3>
                        <p style="color: #6b7280; margin-bottom: 1.5rem;">Unable to load the guideline details. Please try again.</p>
                        <button onclick="closeModal()" style="padding: 0.75rem 1.5rem; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">Close</button>
                    </div>
                `;
            }
            console.error('Error loading guideline:', error);
        });
}

function closeModal() {
    // Fecha todos os modais abertos
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.classList.add('inv'); // Esconde o modal
        modal.setAttribute('aria-hidden', 'true');
    });
    
    // Restore body scroll
    document.body.style.overflow = '';
}

// Fecha o modal ao clicar fora dele
document.addEventListener('click', function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal && !modal.classList.contains('inv')) {
            closeModal();
        }
    });
});

// Close modal on ESC key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (!modal.classList.contains('inv')) {
                closeModal();
            }
        });
    }
});

