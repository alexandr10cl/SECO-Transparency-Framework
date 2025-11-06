const navItems = document.querySelectorAll(".dashboard-navbar ul li");
  const containers = {
    "Overview": document.querySelector(".overview-container"),
    "Evaluated Scenarios": document.querySelector(".evaluated-scenarios-container"),
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

// Funcionalidade do menu lateral de scenarios
function initScenariosSidebar() {
    const scenarioItems = document.querySelectorAll('.scenario-item');
    const scenarioPanels = document.querySelectorAll('.scenario-panel');

    if (!scenarioItems.length || !scenarioPanels.length) return;

    scenarioItems.forEach(item => {
        item.addEventListener('click', () => {
            const scenarioId = item.dataset.scenarioId;

            // Atualizar items ativos no menu
            scenarioItems.forEach(si => si.classList.remove('active'));
            item.classList.add('active');

            // Mostrar panel correspondente
            scenarioPanels.forEach(panel => {
                if (panel.dataset.scenarioId === scenarioId) {
                    panel.classList.add('active');
                } else {
                    panel.classList.remove('active');
                }
            });
        });
    });
}

// Funcionalidade accordion das guidelines
function initGuidelinesAccordion() {
    const accordionHeaders = document.querySelectorAll('.guideline-accordion-header');

    accordionHeaders.forEach(header => {
        header.addEventListener('click', () => {
            const item = header.parentElement;
            const isActive = item.classList.contains('active');

            // Fechar todos
            document.querySelectorAll('.guideline-accordion-item').forEach(i => {
                i.classList.remove('active');
            });

            // Abrir o clicado (se não estava ativo)
            if (!isActive) {
                item.classList.add('active');
            }
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

// Gráfico de barras - Familiaridade com o Portal
fetch(`/api/portal-familiarity/${id}`)
  .then(response => response.json())
  .then(data => {
    const familiarityCtx = document.getElementById('familiarityChart').getContext('2d');
    new Chart(familiarityCtx, {
        type: 'bar',
        data: {
          labels: ['Never', 'Rarely', 'Often', 'Always'],
          datasets: [{
            label: 'Number of developers',
            data: data.values,
            backgroundColor: [
              'rgba(239, 68, 68, 0.7)',   // vermelho - Never
              'rgba(245, 158, 11, 0.7)',  // laranja - Rarely
              'rgba(59, 130, 246, 0.7)',  // azul - Often
              'rgba(34, 197, 94, 0.7)'    // verde - Always
            ],
            borderColor: [
              'rgba(239, 68, 68, 1)',
              'rgba(245, 158, 11, 1)',
              'rgba(59, 130, 246, 1)',
              'rgba(34, 197, 94, 1)'
            ],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1 }
            }
          },
          plugins: {
            legend: {
              display: true,
              position: 'top'
            },
            title: {
              display: true,
              text: 'Familiarity with the Portal'
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

// Funções do modal de KSC
function openKscModal(name, description, score, weight, insight) {
    const modal = document.getElementById('kscModal');
    if (!modal) return;

    // Preencher os dados do modal
    document.getElementById('kscModalName').textContent = name;
    document.getElementById('kscModalDescription').textContent = description;
    document.getElementById('kscModalScore').textContent = `${score} / 100`;
    document.getElementById('kscModalWeight').textContent = `${weight} / 10`;
    document.getElementById('kscModalInsight').textContent = insight;

    // Determinar status baseado no score
    const statusElement = document.getElementById('kscModalStatus');
    let statusHTML = '';
    if (score >= 75) {
        statusHTML = '<span class="status-badge fulfilled"><span class="status-icon">●</span> Fulfilled</span>';
    } else if (score >= 50) {
        statusHTML = '<span class="status-badge partially-fulfilled"><span class="status-icon">●</span> Partially Fulfilled</span>';
    } else {
        statusHTML = '<span class="status-badge not-fulfilled"><span class="status-icon">●</span> Not Fulfilled</span>';
    }
    statusElement.innerHTML = statusHTML;

    // Mostrar modal
    modal.style.display = 'block';
}

function closeKscModal() {
    const modal = document.getElementById('kscModal');
    if (modal) {
        modal.style.display = 'none';
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

// Fechar modais ao clicar fora deles
window.onclick = function(event) {
    const metricsModal = document.getElementById('metricsModal');
    const kscModal = document.getElementById('kscModal');

    if (event.target === metricsModal) {
        metricsModal.style.display = 'none';
    }

    if (event.target === kscModal) {
        kscModal.style.display = 'none';
    }
}

// Função para animar barras de progresso
function animateProgressBars() {
    const progressBars = document.querySelectorAll('.progress-fill[data-pct]');

    progressBars.forEach(bar => {
        const percentage = parseFloat(bar.getAttribute('data-pct')) || 0;
        const maxPercentage = Math.min(percentage, 100);

        // Reset animation
        bar.style.width = '0%';

        // Animate with delay
        setTimeout(() => {
            bar.style.width = maxPercentage + '%';
        }, 300);
    });
}

window.onload = function() {
    gerarNuvem();
    applyStatusColors();
    enhanceTaskBadges();
    initScenariosSidebar();
    initGuidelinesAccordion();
    initTaskAccordions();
    animateProgressBars();
};
