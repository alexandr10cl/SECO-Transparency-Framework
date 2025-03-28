document.addEventListener('DOMContentLoaded', function() {
    const slcts = document.querySelectorAll('.slct');
    const tables = document.querySelectorAll('.table-info');
    
    // Função para mostrar/esconder tabelas
    function showTable(tableId) {
        tables.forEach(table => {
            if (table.classList.contains(tableId)) {
                table.style.display = 'table';
            } else {
                table.style.display = 'none';
            }
        });
    }
    
    // Esconder todas as tabelas inicialmente
    tables.forEach(table => {
        table.style.display = 'none';
    });
    
    // Mostrar a tabela do item ativo inicial
    const activeSlct = document.querySelector('.slct.active');
    if (activeSlct) {
        showTable(activeSlct.id);
    }
    
    // Adicionar eventos de clique
    slcts.forEach(slct => {
        slct.addEventListener('click', function() {
            // Remove active class from all items
            slcts.forEach(item => item.classList.remove('active'));
            // Add active class to clicked item
            this.classList.add('active');
            // Show corresponding table
            showTable(this.id);
        });
    });

    // Novo código para a sidebar
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    const sections = document.querySelectorAll('[id$="-section"]');
    
    function showSection(sectionId) {
        sections.forEach(section => {
            if (section.id === sectionId) {
                section.style.display = 'block';
            } else {
                section.style.display = 'none';
            }
        });
    }
    
    sidebarItems.forEach(item => {
        item.addEventListener('click', function() {
            // Remove active class from all items
            sidebarItems.forEach(i => i.classList.remove('active'));
            // Add active class to clicked item
            this.classList.add('active');
            // Show corresponding section
            const sectionId = this.dataset.section + '-section';
            showSection(sectionId);
        });
    });
});

// Variável cont definida no escopo global para manter o contador entre chamadas da função
let criteriaCount = 1;

function addMoreCriteria() {
    criteriaCount++;  // Increments the global counter
    
    const criteriaContainer = document.querySelector('.criteria-container');
    const newCriteria = criteriaContainer.cloneNode(true);
    
    //Clean values and update names/IDs
    const input = newCriteria.querySelector('input');
    input.value = '';
    input.name = 'title' + criteriaCount;
    input.id = criteriaCount;  // Updates the ID also
    
    const textarea = newCriteria.querySelector('textarea');
    textarea.value = '';
    textarea.name = 'description' + criteriaCount;
    textarea.id = criteriaCount;  // Updates the ID also
    
    newCriteria.style.marginTop = '10px';
    criteriaContainer.parentNode.insertBefore(newCriteria, criteriaContainer.nextSibling);
}
