const navItems = document.querySelectorAll(".dashboard-navbar ul li");
  const containers = {
    "Overview": document.querySelector(".overview-container"),
    "Performed Tasks": document.querySelector(".performed-tasks-container"),
    "Hotspots": document.querySelector(".hotspots-container"),
    "Guidelines Score": document.querySelector(".guidelines-score-container"),
};

navItems.forEach(item => {
    item.addEventListener("click", () => {
        // Remove 'active' da navbar
        navItems.forEach(i => i.classList.remove("active"));
        item.classList.add("active");

        // Esconde todos os containers
        Object.values(containers).forEach(div => div.classList.remove("active-container"));

        // Mostra o container correspondente
        const texto = item.textContent.trim();
        if(containers[texto]){
            containers[texto].classList.add("active-container");
        }
    });
});

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
          responsive: false,
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

async function gerarNuvem(){

  fetch(`/api/wordcloud/${id}`)
    .then(response => response.json())
    .then(data => {

      words = data

      WordCloud(document.getElementById('word-cloud'), {
        list: words,
        gridSize: 10,
        weightFactor: 5,
        fontFamily: 'Montserrat',
        color: 'random-dark',
        backgroundColor: '#ffffff',
        rotateRatio: 0,
        rotationSteps: 2,
        shape: 'circle'
      });
    });

  

}

// Função para aplicar cores aos status baseado no texto
function applyStatusColors() {
    const statusElements = document.querySelectorAll('.guideline-status');
    
    statusElements.forEach(element => {
        const text = element.textContent.trim().toLowerCase();
        
        // Remove classes existentes
        element.classList.remove('status-fulfilled', 'status-partially', 'status-not-fulfilled', 'status-na');
        
        // Aplica classe baseada no texto
        if (text.includes('fulfilled') && !text.includes('not')) {
            element.classList.add('status-fulfilled');
        } else if (text.includes('partially')) {
            element.classList.add('status-partially');
        } else if (text.includes('not') || text.includes('unfulfilled')) {
            element.classList.add('status-not-fulfilled');
        } else if (text.includes('n/a') || text === 'na' || text === 'not applicable') {
            element.classList.add('status-na');
        }
    });
}

window.onload = function() {
    gerarNuvem();
    applyStatusColors();
};