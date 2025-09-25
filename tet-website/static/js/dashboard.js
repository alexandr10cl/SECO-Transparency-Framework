const navItems = document.querySelectorAll(".dashboard-navbar ul li");
  const containers = {
    "Overview": document.querySelector(".overview-container"),
    "Evaluated Procedures": document.querySelector(".evaluated-procedures-container"),
    "Hotspots": document.querySelector(".hotspots-container"),
};

navItems.forEach(item => {
    item.addEventListener("click", () => {
        // Remove 'active' da navbar
        navItems.forEach(i => i.classList.remove("active"));
        item.classList.add("active");

        // Esconde todos os containers
        Object.values(containers).forEach(div => {
            if(div) div.classList.remove("active-container");
        });

        // Mostra o container correspondente
        const texto = item.textContent.trim();
        if(containers[texto]){
            containers[texto].classList.add("active-container");
        }
    });
});

// Funcionalidade do menu lateral de procedimentos
function initProceduresSidebar() {
    const procedureItems = document.querySelectorAll('.procedure-item');
    const procedurePanels = document.querySelectorAll('.procedure-panel');

    if (!procedureItems.length || !procedurePanels.length) return;

    procedureItems.forEach(item => {
        item.addEventListener('click', () => {
            const processId = item.dataset.processId;

            // Atualizar items ativos no menu
            procedureItems.forEach(pi => pi.classList.remove('active'));
            item.classList.add('active');

            // Mostrar panel correspondente
            procedurePanels.forEach(panel => {
                if (panel.dataset.processId === processId) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });
}

// Funcionalidade accordion das tasks
function initTaskAccordions() {
    const accordionHeaders = document.querySelectorAll('.task-accordion-header');

    accordionHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const content = header.nextElementSibling;
            const toggle = header.querySelector('.task-toggle');

            if (content.classList.contains('show')) {
                content.classList.remove('show');
                header.classList.remove('expanded');
                if (toggle) toggle.textContent = 'expand_more';
            } else {
                // Fechar outros accordions no mesmo painel (opcional)
                const parentPanel = header.closest('.procedure-panel');
                if (parentPanel) {
                    parentPanel.querySelectorAll('.task-accordion-content.show').forEach(openContent => {
                        openContent.classList.remove('show');
                    });
                    parentPanel.querySelectorAll('.task-accordion-header.expanded').forEach(openHeader => {
                        openHeader.classList.remove('expanded');
                        const t = openHeader.querySelector('.task-toggle');
                        if (t) t.textContent = 'expand_more';
                    });
                }

                // Abrir o accordion clicado
                content.classList.add('show');
                header.classList.add('expanded');
                if (toggle) toggle.textContent = 'expand_less';
            }
        });
    });
}

const pathParts = window.location.pathname.split('/')
const id = pathParts[pathParts.length - 1];

// Gráfico de Pizza
fetch(`/api/satisfaction/${id}`)
  .then(response => response.json())
  .then(data => {
    const pieCtx = document.getElementById('pieChart').getContext('2d');
    new Chart(pieCtx, {
      type: 'pie',
      data: {
        labels: [
          'Very dissatisfied',
          'Dissatisfied',
          'Neither satisfied nor dissatisfied',
          'Satisfied',
          'Very satisfied'
        ],
        datasets: [{
          label: 'Quantity of developers',
          data: data.values,
          backgroundColor: [
            '#e74c3c',   // vermelho escuro
            '#f39c12',   // laranja
            '#95a5a6',   // cinza
            '#3498db',   // azul
            '#2ecc71'    // verde
          ]
        }]
      },
      options: {
          responsive: true,
          maintainAspectRatio: false
      }
    });
  })


// Gráfico de barras - Anos de experiência
fetch(`/api/experience-data/${id}`)
  .then(response => response.json())
  .then(data => {
    
    const experienceCtx = document.getElementById('experienceChart').getContext('2d');
    new Chart(experienceCtx, {
        type: 'bar',
        data: {
          labels: ['0-1 year', '2-3 years', '4-5 years', '6-10 years', '10+ years'],
          datasets: [{
            label: 'Number of developers',
            data: data.values,  // dados aleatórios
            backgroundColor: 'rgba(75, 192, 192, 0.7)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 5 }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            title: {
              display: true,
              text: 'Years of Experience in Software Development'
            }
          }
        }
    });
  })



// Gráfico de barras - Grau acadêmico
fetch(`/api/grau-academico/${id}`)
  .then(response => response.json())
  .then(data => {
    const educationCtx = document.getElementById('educationChart').getContext('2d');
    new Chart(educationCtx, {
        type: 'bar',
        data: {
          labels: ['High School', 'Graduation', 'Master', 'PhD'],
          datasets: [{
            label: 'Number of developers',
            data: data.values,
            backgroundColor: 'rgba(153, 102, 255, 0.7)',
            borderColor: 'rgba(153, 102, 255, 1)',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 5 }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            title: {
              display: true,
              text: 'Academic Degree of Developers'
            }
          }
        }
    });
  })

// Word cloud – responsive rendering
async function gerarNuvem(){
  const canvas = document.getElementById('word-cloud');
  if (!canvas) return;
  const container = canvas.parentElement;

  // Size canvas to container for crisp rendering
  const width = Math.max(300, container.clientWidth);
  const height = Math.max(250, Math.round(width * 0.55));
  canvas.width = width;
  canvas.height = height;

  fetch(`/api/wordcloud/${id}`)
    .then(response => response.json())
    .then(data => {
      const words = data || [];
      const maxWeight = words.length ? Math.max(...words.map(w => w[1])) : 1;

      // Scale font between min/max relative to canvas width
      const minFont = 12;
      const maxFont = Math.max(28, Math.min(72, Math.round(width / 8)));

      WordCloud(canvas, {
        list: words,
        gridSize: Math.max(8, Math.round(width / 64)),
        weightFactor: (size) => minFont + (size / (maxWeight || 1)) * (maxFont - minFont),
        fontFamily: 'Montserrat, sans-serif',
        color: 'random-dark',
        backgroundColor: '#ffffff',
        rotateRatio: 0,
        rotationSteps: 2,
        shape: 'circle',
        shuffle: true,
        drawOutOfBound: false,
        shrinkToFit: true,
      });
    });
}

// Re-render word cloud on resize (debounced)
let wcResizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(wcResizeTimer);
  wcResizeTimer = setTimeout(() => gerarNuvem(), 200);
});

// Função para aplicar cores aos status baseado no texto
function applyStatusColors() {
    const statusElements = document.querySelectorAll('.guideline-status');
    
    statusElements.forEach(element => {
        const text = element.textContent.trim().toLowerCase();
        
        // Remove classes existentes
        element.classList.remove('status-fulfilled', 'status-partially', 'status-not-fulfilled', 'status-na');
        
        // Aplica classe baseada no texto (COM ORDEM CORRIGIDA)
        if (text.includes('partially')) { // 1. Checa 'partially' primeiro
            element.classList.add('status-partially');
        } else if (text.includes('fulfilled') && !text.includes('not')) { // 2. Depois checa 'fulfilled'
            element.classList.add('status-fulfilled');
        } else if (text.includes('not')) { // 3. Depois o 'not'
            element.classList.add('status-not-fulfilled');
        } else if (text.includes('no answers')) { // 4. E por último o "sem respostas"
            element.classList.add('status-na');
        }
    });
}

// Enhanced task badge interactions
function enhanceTaskBadges() {
    const taskCards = document.querySelectorAll('.task-overview-card');
    const criticalTasks = document.querySelectorAll('.critical-task');
    
    // Add hover effects for all task cards
    taskCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-2px)';
            card.style.transition = 'all 0.3s ease';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
        });
    });
    
    // Enhanced critical task attention effects
    criticalTasks.forEach(task => {
        const attentionBadge = task.querySelector('.attention-badge');
        if (attentionBadge) {
            attentionBadge.addEventListener('click', () => {
                // Flash effect when clicked
                attentionBadge.style.animation = 'none';
                setTimeout(() => {
                    attentionBadge.style.animation = 'pulse 2s infinite';
                }, 100);
            });
        }
    });
    
    // Add badge tooltips with performance insights
    const badges = document.querySelectorAll('.badge');
    badges.forEach(badge => {
        let tooltipText = '';
        const badgeText = badge.textContent.toLowerCase();
        
        // Define tooltip messages based on badge type
        if (badgeText.includes('fast')) {
            tooltipText = 'Excellent performance - task completed quickly';
        } else if (badgeText.includes('moderate')) {
            tooltipText = 'Good performance - reasonable completion time';
        } else if (badgeText.includes('slow')) {
            tooltipText = 'Consider optimization - task takes longer than expected';
        } else if (badgeText.includes('very slow')) {
            tooltipText = 'Needs immediate attention - significantly long completion time';
        } else if (badgeText.includes('high success')) {
            tooltipText = 'Excellent success rate - most developers complete this task';
        } else if (badgeText.includes('good success')) {
            tooltipText = 'Good success rate - majority of developers succeed';
        } else if (badgeText.includes('low success')) {
            tooltipText = 'Concerning success rate - many developers struggle';
        } else if (badgeText.includes('poor success')) {
            tooltipText = 'Critical issue - most developers fail this task';
        }
        
        if (tooltipText) {
            badge.title = tooltipText;
        }
    });
    
    // Count and display summary statistics
    const totalTasks = taskCards.length;
    const criticalTasksCount = criticalTasks.length;
    
    if (criticalTasksCount > 0) {
        console.log(`Dashboard Alert: ${criticalTasksCount} out of ${totalTasks} tasks need attention`);
        
        // Create summary badge in the header if there are critical tasks
        const tasksHeader = document.querySelector('.tasks-header h2');
        if (tasksHeader && criticalTasksCount > 0) {
            const summaryBadge = document.createElement('span');
            summaryBadge.className = 'critical-summary-badge';
            summaryBadge.textContent = `${criticalTasksCount} Critical`;
            summaryBadge.style.cssText = `
                background-color: var(--critical-alert);
                color: white;
                padding: 0.25rem 0.5rem;
                border-radius: 9999px;
                font-size: 0.75rem;
                font-weight: 600;
                margin-left: 1rem;
                animation: pulse 2s infinite;
            `;
            tasksHeader.appendChild(summaryBadge);
        }
    }
}

// Funções do modal de métricas
function openMetricsModal() {
    const modal = document.getElementById('metricsModal');
    if (modal) {
        modal.style.display = 'block';
        // Previne o fechamento do accordion ao clicar no botão info
        event.stopPropagation();
    }
}

function closeMetricsModal() {
    const modal = document.getElementById('metricsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Fechar modal ao clicar fora dele
window.onclick = function(event) {
    const modal = document.getElementById('metricsModal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

window.onload = function() {
    gerarNuvem();
    applyStatusColors();
    enhanceTaskBadges();
    initProceduresSidebar();
    initTaskAccordions();
};
