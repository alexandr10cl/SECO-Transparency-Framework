// ==========================================
// PAGE LOADER - Hide when everything is ready
// ==========================================
window.addEventListener('load', function() {
    const loader = document.getElementById('page-loader');
    if (loader) {
        // Small delay to ensure all content is rendered
        setTimeout(() => {
            loader.classList.add('hidden');
            // Remove from DOM after fade animation completes
            setTimeout(() => {
                if (loader.parentNode) {
                    loader.remove();
                }
            }, 400);
        }, 300);
    }
});

// Also hide loader if it takes too long (fallback after 10 seconds)
setTimeout(function() {
    const loader = document.getElementById('page-loader');
    if (loader && !loader.classList.contains('hidden')) {
        console.warn('Page loader timeout - forcing hide');
        loader.classList.add('hidden');
        setTimeout(() => {
            if (loader.parentNode) {
                loader.remove();
            }
        }, 400);
    }
}, 10000);

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
    const pathParts = window.location.pathname.split('/');
    const evaluationId = pathParts[pathParts.length - 1];

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
                    // Gerar word cloud ao trocar de scenario
                    gerarNuvemScenario(scenarioId, evaluationId);
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

// Modern Pie Chart Configuration for Developer Emotions
const pieChartConfig = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 1000,
    easing: 'easeOutQuart'
  },
  plugins: {
    legend: {
      display: true,
      position: 'bottom',
      align: 'center',
      labels: {
        usePointStyle: true,
        padding: window.innerWidth < 480 ? 8 : 12,
        boxWidth: 12,
        boxHeight: 12,
        font: {
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          size: window.innerWidth < 480 ? 10 : window.innerWidth < 768 ? 11 : 12,
          weight: '500'
        },
        color: '#404040',
        generateLabels: function(chart) {
          const data = chart.data;
          if (data.labels.length && data.datasets.length) {
            return data.labels.map((label, i) => {
              const value = data.datasets[0].data[i];
              return {
                text: `${label} (${value})`,
                fillStyle: data.datasets[0].backgroundColor[i],
                hidden: false,
                index: i
              };
            });
          }
          return [];
        }
      }
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.85)',
      padding: window.innerWidth < 480 ? 8 : 12,
      titleFont: {
        size: window.innerWidth < 480 ? 12 : 14,
        weight: '600'
      },
      bodyFont: {
        size: window.innerWidth < 480 ? 11 : 13
      },
      cornerRadius: 8,
      displayColors: true,
      callbacks: {
        label: function(context) {
          const label = context.label || '';
          const value = context.parsed || 0;
          const total = context.dataset.data.reduce((a, b) => a + b, 0);
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
          return `${label}: ${value} developer${value !== 1 ? 's' : ''} (${percentage}%)`;
        }
      }
    }
  }
};

// Gráfico de Pizza - Developer Emotions (Modern Professional Design)
fetch(`/api/satisfaction/${id}`)
  .then(response => response.json())
  .then(data => {
    const pieCtx = document.getElementById('pieChart').getContext('2d');
    const pieChart = new Chart(pieCtx, {
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
            'rgba(239, 68, 68, 0.85)',   // Red - Very dissatisfied
            'rgba(245, 158, 11, 0.85)',  // Orange - Dissatisfied
            'rgba(148, 163, 184, 0.85)', // Gray - Neither
            'rgba(59, 130, 246, 0.85)',  // Blue - Satisfied
            'rgba(34, 197, 94, 0.85)'    // Green - Very satisfied
          ],
          borderColor: [
            'rgba(239, 68, 68, 1)',
            'rgba(245, 158, 11, 1)',
            'rgba(148, 163, 184, 1)',
            'rgba(59, 130, 246, 1)',
            'rgba(34, 197, 94, 1)'
          ],
          borderWidth: 2,
          hoverOffset: 4
        }]
      },
      options: pieChartConfig
    });
    
    // Store instance for responsive updates
    chartInstances.pie = pieChart;
  })
  .catch(error => {
    console.error('Error loading satisfaction data:', error);
  });


// Helper function to get responsive chart height based on screen size
function getChartHeight() {
  const width = window.innerWidth;
  if (width < 480) return 220;
  if (width < 768) return 250;
  if (width < 1024) return 280;
  return 300;
}

// Modern Chart.js configuration shared by all charts
const modernChartConfig = {
  responsive: true,
  maintainAspectRatio: false,
  animation: {
    duration: 1000,
    easing: 'easeOutQuart'
  },
  onResize: function(chart, size) {
    // Adjust chart height on resize
    if (size.width < 480) {
      chart.canvas.parentElement.style.height = '220px';
    } else if (size.width < 768) {
      chart.canvas.parentElement.style.height = '250px';
    } else if (size.width < 1024) {
      chart.canvas.parentElement.style.height = '280px';
    } else {
      chart.canvas.parentElement.style.height = '300px';
    }
  },
  plugins: {
    legend: {
      display: true,
      position: 'top',
      labels: {
        usePointStyle: true,
        padding: window.innerWidth < 480 ? 10 : 15,
        font: {
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          size: window.innerWidth < 480 ? 11 : window.innerWidth < 768 ? 12 : 13,
          weight: '500'
        },
        color: '#404040'
      }
    },
    tooltip: {
      backgroundColor: 'rgba(0, 0, 0, 0.85)',
      padding: window.innerWidth < 480 ? 8 : 12,
      titleFont: {
        size: window.innerWidth < 480 ? 12 : 14,
        weight: '600'
      },
      bodyFont: {
        size: window.innerWidth < 480 ? 11 : 13
      },
      cornerRadius: 8,
      displayColors: true,
      callbacks: {
        label: function(context) {
          return `${context.dataset.label}: ${context.parsed.y} developer${context.parsed.y !== 1 ? 's' : ''}`;
        }
      }
    }
  },
  scales: {
    x: {
      grid: {
        display: false
      },
      ticks: {
        font: {
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          size: window.innerWidth < 480 ? 10 : window.innerWidth < 768 ? 11 : 12
        },
        color: '#737373',
        padding: window.innerWidth < 480 ? 6 : 10,
        maxRotation: window.innerWidth < 480 ? 45 : 0,
        minRotation: window.innerWidth < 480 ? 45 : 0
      }
    },
    y: {
      beginAtZero: true,
      grid: {
        color: 'rgba(0, 0, 0, 0.05)',
        drawBorder: false
      },
      ticks: {
        font: {
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
          size: window.innerWidth < 480 ? 10 : window.innerWidth < 768 ? 11 : 12
        },
        color: '#737373',
        padding: window.innerWidth < 480 ? 6 : 10,
        stepSize: 1
      }
    }
  }
};

// Gráfico de barras - Anos de experiência (Modern Professional Design)
fetch(`/api/experience-data/${id}`)
  .then(response => response.json())
  .then(data => {
    const experienceCtx = document.getElementById('experienceChart').getContext('2d');
    const experienceChart = new Chart(experienceCtx, {
        type: 'bar',
        data: {
          labels: ['0-1 year', '2-3 years', '4-5 years', '6-10 years', '10+ years'],
          datasets: [{
            label: 'Number of developers',
          data: data.values,
          backgroundColor: 'rgba(37, 99, 235, 0.85)', // Modern blue
          borderColor: 'rgba(37, 99, 235, 1)',
          borderWidth: 0,
          borderRadius: 8,
          borderSkipped: false
          }]
        },
        options: {
        ...modernChartConfig,
          plugins: {
          ...modernChartConfig.plugins,
            title: {
            display: false // Remove default title, use HTML heading instead
            }
          }
        }
    });
    chartInstances.experience = experienceChart;
  })



// Gráfico de barras - Grau acadêmico (Modern Professional Design)
fetch(`/api/grau-academico/${id}`)
  .then(response => response.json())
  .then(data => {
    const educationCtx = document.getElementById('educationChart').getContext('2d');
    const educationChart = new Chart(educationCtx, {
        type: 'bar',
        data: {
          labels: ['High School', 'Graduation', 'Master', 'PhD'],
          datasets: [{
            label: 'Number of developers',
            data: data.values,
          backgroundColor: 'rgba(139, 92, 246, 0.85)', // Modern purple
          borderColor: 'rgba(139, 92, 246, 1)',
          borderWidth: 0,
          borderRadius: 8,
          borderSkipped: false
          }]
        },
        options: {
        ...modernChartConfig,
          plugins: {
          ...modernChartConfig.plugins,
            title: {
            display: false
            }
          }
        }
    });
    chartInstances.education = educationChart;
  })

// Gráfico de barras - Familiaridade com o Portal (Modern Professional Design with Semantic Colors)
fetch(`/api/portal-familiarity/${id}`)
  .then(response => response.json())
  .then(data => {
    const familiarityCtx = document.getElementById('familiarityChart').getContext('2d');
    const familiarityChart = new Chart(familiarityCtx, {
        type: 'bar',
        data: {
          labels: ['Never', 'Rarely', 'Often', 'Always'],
          datasets: [{
            label: 'Number of developers',
            data: data.values,
            backgroundColor: [
            'rgba(239, 68, 68, 0.85)',   // Red - Never
            'rgba(245, 158, 11, 0.85)',  // Orange - Rarely
            'rgba(59, 130, 246, 0.85)',  // Blue - Often
            'rgba(34, 197, 94, 0.85)'    // Green - Always
            ],
            borderColor: [
              'rgba(239, 68, 68, 1)',
              'rgba(245, 158, 11, 1)',
              'rgba(59, 130, 246, 1)',
              'rgba(34, 197, 94, 1)'
            ],
          borderWidth: 0,
          borderRadius: 8,
          borderSkipped: false
          }]
        },
        options: {
        ...modernChartConfig,
          plugins: {
          ...modernChartConfig.plugins,
            title: {
            display: false
            }
          }
        }
    });
    chartInstances.familiarity = familiarityChart;
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
let chartResizeTimer;

// Store chart instances for responsive updates
const chartInstances = {
  experience: null,
  education: null,
  familiarity: null,
  pie: null
};

window.addEventListener('resize', () => {
  clearTimeout(wcResizeTimer);
  wcResizeTimer = setTimeout(() => gerarNuvem(), 200);
  
  // Update chart containers height on resize
  clearTimeout(chartResizeTimer);
  chartResizeTimer = setTimeout(() => {
    const width = window.innerWidth;
    let height = 300;
    if (width < 480) height = 220;
    else if (width < 768) height = 250;
    else if (width < 1024) height = 280;
    
    document.querySelectorAll('#experienceChart, #educationChart, #familiarityChart').forEach(canvas => {
      if (canvas && canvas.parentElement) {
        canvas.parentElement.style.height = height + 'px';
      }
    });
    
    // Update pie chart size responsively
    const pieCanvas = document.getElementById('pieChart');
    if (pieCanvas) {
      let pieHeight = 320;
      if (width < 480) pieHeight = 220;
      else if (width < 768) pieHeight = 240;
      else if (width < 1024) pieHeight = 280;
      else if (width >= 1400) pieHeight = 380;
      else if (width >= 1200) pieHeight = 340;
      else if (width >= 1025) pieHeight = 320;
      
      pieCanvas.style.height = pieHeight + 'px';
      pieCanvas.style.maxHeight = pieHeight + 'px';
      pieCanvas.style.width = pieHeight + 'px';
      pieCanvas.style.maxWidth = pieHeight + 'px';
    }
    
    // Resize all chart instances
    Object.values(chartInstances).forEach(chart => {
      if (chart) {
        chart.resize();
      }
    });
  }, 150);
});

// Word cloud por scenario específico
function gerarNuvemScenario(taskId, evaluationId) {
    const canvas = document.getElementById(`scenario-wordcloud-${taskId}`);
    if (!canvas) return;
    const container = canvas.parentElement;

    const width = Math.max(250, container.clientWidth);
    const height = 160;
    canvas.width = width;
    canvas.height = height;

    fetch(`/api/wordcloud/task/${evaluationId}/${taskId}`)
        .then(response => response.json())
        .then(data => {
            const words = data || [];

            if (words.length === 0) {
                // Mostrar mensagem se não houver palavras
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#999';
                ctx.font = '14px Montserrat';
                ctx.textAlign = 'center';
                ctx.fillText('No comments available', width / 2, height / 2);
                return;
            }

            const maxWeight = words.length ? Math.max(...words.map(w => w[1])) : 1;
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
        })
        .catch(error => {
            console.error('Error loading word cloud for task:', taskId, error);
        });
}

// Toggle para mostrar/esconder comentários
function toggleComments(taskId) {
    const commentsList = document.getElementById(`comments-list-${taskId}`);
    const hiddenComments = commentsList.querySelectorAll('.hidden-comment');
    const button = event.currentTarget;
    const textMore = button.querySelector('.btn-text-more');
    const textLess = button.querySelector('.btn-text-less');
    const icon = button.querySelector('.material-symbols-outlined');

    if (hiddenComments[0].style.display === 'none' || hiddenComments[0].classList.contains('hidden-comment')) {
        // Mostrar todos
        hiddenComments.forEach(comment => {
            comment.classList.remove('hidden-comment');
            comment.style.display = 'block';
        });
        textMore.style.display = 'none';
        textLess.style.display = 'inline';
        button.classList.add('expanded');
    } else {
        // Esconder extras
        hiddenComments.forEach(comment => {
            comment.classList.add('hidden-comment');
            comment.style.display = 'none';
        });
        textMore.style.display = 'inline';
        textLess.style.display = 'none';
        button.classList.remove('expanded');
    }
}

// Inicializar word clouds dos scenarios
function initScenarioWordClouds() {
    const pathParts = window.location.pathname.split('/');
    const evaluationId = pathParts[pathParts.length - 1];

    // Gerar word cloud do scenario ativo
    const activePanel = document.querySelector('.scenario-panel.active');
    if (activePanel) {
        const taskId = activePanel.dataset.scenarioId;
        gerarNuvemScenario(taskId, evaluationId);
    }
}

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
    initScenarioWordClouds();
};
