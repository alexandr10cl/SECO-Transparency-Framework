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



// Gráfico de Pizza
const pieCtx = document.getElementById('pieChart').getContext('2d');
  new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels: [
        'Muito insatisfeito',
        'Insatisfeito',
        'Neutro',
        'Satisfeito',
        'Muito satisfeito'
      ],
      datasets: [{
        label: 'Nível de Satisfação',
        data: [3, 5, 10, 8, 4], // <- valores de exemplo
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


// Gráfico de barras - Anos de experiência
const experienceCtx = document.getElementById('experienceChart').getContext('2d');
new Chart(experienceCtx, {
    type: 'bar',
    data: {
      labels: ['0-1 ano', '2-3 anos', '4-5 anos', '6-10 anos', '10+ anos'],
      datasets: [{
        label: 'Número de desenvolvedores',
        data: [15, 30, 22, 18, 10],  // dados aleatórios
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
          text: 'Anos de Experiência em Desenvolvimento de Software'
        }
      }
    }
});

// Gráfico de barras - Grau acadêmico
const educationCtx = document.getElementById('educationChart').getContext('2d');
new Chart(educationCtx, {
    type: 'bar',
    data: {
      labels: ['Graduação', 'Especialização', 'Mestrado', 'Doutorado'],
      datasets: [{
        label: 'Número de pessoas',
        data: [35, 12, 8, 5], // dados aleatórios
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
          text: 'Grau Acadêmico'
        }
      }
    }
});