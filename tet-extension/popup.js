let starttestdiv = document.querySelector(".main_page");
let finalpage = document.querySelector(".final_page");
let questionnaire_page = document.querySelector(".questionnaire_page");
let final_questionnaire_page = document.querySelector(".final_questionnaire_page");
let login_page = document.querySelector(".login_page");
let sync_page = document.querySelector(".sync_page");
let overlay = document.getElementById('overlay');

// Variáveis globais
let data_collection = {
  "evaluation_code" : "123456",
  "uxt_cod" : "default",
  "uxt_sessionId" : "0",
  "performed_tasks" : [],
  "profile_questionnaire" : {},
  "final_questionnaire" : {},
  "navigation" : [] // Store all navigation events
}
let tasks_data = [];   // Armazena as respostas para envio
let todo_tasks = [];   // Armazena as tasks recebidas em formato de objeto para serem feitas
let processes = []; // Cada processo tem tarefas e perguntas do review
let currentProcessIndex = 0;
let currentTaskIndex = -1; // Índice da task atual (-1 significa página incial e 0 significa primeira task e por ai vai)
let currentPhase = "login"; // Pode ser "login", "sync","initial","questionnaire", "task", "review", "processreview" ,"finalquestionnaire" ou "final", serve para configurar a exibição na tela
let currentTaskTimestamp = "Erro ao obter o timestamp"; // Armazena o timestamp da task atual
let currentTaskStatus = "solving" // alterado para "solved" ou "couldntsolve" no botão de finalizar a task
let taskStartTime = null;
let taskEndTime = null;




// Navigation tracking
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  try {
    // Listen for page navigation events from background.js
    if (currentPhase === "task" || currentPhase === "review") { // Só captura navegação na etapa de resolução de tarefas ou revisão
      if (request.action === "pageNavigation" || request.action === "tab_switch") {
        data_collection.navigation.push({
          action : request.action,
          title: request.title,
          url: request.url,
          timestamp: request.timestamp,
          taskId: (currentTaskIndex >= 0 && todo_tasks.length > 0 && currentTaskIndex < todo_tasks.length) 
                  ? todo_tasks[currentTaskIndex].id 
                  : null
        });
        console.log("Navigation recorded:", request.url);
      }
    }
  } catch (error) {
    console.error("Error processing message:", error);
  }
});


document.getElementById("mainPageButton").addEventListener("click", function () {
  starttestdiv.style.display = "none";
  currentPhase = "questionnaire";

  updateDisplay();
});

// Botão de finalizar questionário de perfil
document.getElementById("questionnaireButton").addEventListener("click", function () {
  currentTaskIndex = 0;
  currentPhase = "task";
  
  data_collection.startTime = new Date().toISOString(); // Salva o timestamp inicial da avaliação

  updateDisplay();
});

// Autentificação
document.getElementById("verifyButton").addEventListener("click", function () {
  currentPhase = "sync";
  let authcode = document.getElementById("authcode").value;
  updateDisplay(); // Atualiza a exibição para a fase de sincronização

  auth_evaluation(authcode) // Envia o código para autenticação
    .then((isValid) => {
      if (isValid) {
        data_collection.evaluation_code = authcode; // Salva o código de avaliação na variável global
      } else {
        document.getElementById("errorMessage").style.display = "block";
      }
    });

});


// Sincronizar código com API DO UX-TRACKING
document.getElementById("syncButton").addEventListener("click", function () {
  overlay.style.display = 'block'; // Exibe o overlay de carregamento

  setTimeout(() => {
    overlay.style.display = 'none';
  }, 5000);

  let uxt_mode = false; // Opção de fazer a avaliação com UX-Tracking o não

  if (uxt_mode) {
    fetch("https://uxt-stage.liis.com.br/data/syncsession", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        cod: data_collection.evaluation_code
      })
    })
    .then(response => {
      if (response.status >= 200 && response.status < 300) {
        // Sucesso (qualquer 2xx)
        return response.json().then(data => {
          console.log("Success:", data);
          
          fetchtasks(data_collection.evaluation_code);
        });
      } else {
        return response.json().then(errorData => {
          console.error(`Error: ${response.status} - ${errorData.message || response.statusText}`);
  
          document.getElementById("syncStatus").style.display = "block"; // Exibe mensagem de erro
        }).catch(() => {
          console.error(`Error: ${response.status} - ${response.statusText}`);
  
          document.getElementById("syncStatus").style.display = "block"; // Exibe mensagem de erro
        });
      }
    })
    .catch(error => {
      console.error("Fetch error:", error);
      document.getElementById("syncStatus").style.display = "block"; // Exibe mensagem de erro
    });
  } else {
    // Se não for usar UX-Tracking, apenas salva os dados e avança
    data_collection.uxt_cod = "default";
    data_collection.uxt_sessionId = "0";

    currentPhase = "initial";
    updateDisplay();
    fetchtasks(data_collection.evaluation_code);
  }

});

function auth_evaluation(code) {
  return fetch("http://127.0.0.1:5000/auth_evaluation", {
    method: "POST",
    headers: {
        "Content-Type": "application/json"
    },
    body: JSON.stringify({ code: code })
  })
  .then(response => {
    console.log("Resposta do servidor:", response);
    if (!response.ok) {
      throw new Error("Erro na autenticação");
    }
    return response.json();
  })
  .then(data => {
    console.log("Mensagem do servidor:", data);
    return data.message === "Valid";
  })
  .catch(error => {
    console.error("Erro na requisição:", error);
    return false;
  });
}


document.addEventListener("DOMContentLoaded", function () {
  emotionRange(); //Ativa o UI da escala de emoção

  updateDisplay();
  
});

// Fetch tasks
// 1) Carrega os processos e tarefas e já adiciona listeners
function fetchtasks(code) {
  fetch("http://127.0.0.1:5000/load_tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code })
  })
    .then(res => res.json())
    .then(list => {
      processes = list;
      currentProcessIndex = 0;
      currentTaskIndex = 0;
      currentPhase = "initial";  
      renderAll();               // monta o HTML
      attachListenersAll();      // conecta todos os botões
      updateDisplay();
    })
    .catch(err => {
      console.error(err);
      currentPhase = "error";
      updateDisplay();
    });
}

// 2) Monta todo o HTML (igual ao código anterior)
function renderAll() {
  const container = document.querySelector("#taskscontainer");
  container.innerHTML = "";

  processes.forEach(proc => {
    const div = document.createElement("div");
    div.classList.add("process-container");
    div.id = `process${proc.process_id}`;

    proc.process_tasks.forEach(task => {
      div.insertAdjacentHTML("beforeend", `
        <div class="taskbox-container" id="taskbox${task.task_id}" style="display:none">
          <div class="task" id="task${task.task_id}">
            <h1 class="task-title" id="taskTitle${task.task_id}" style="display:none">${task.task_title}</h1>
            <div class="task-info">
              <p class="task-description" id="taskDescription${task.task_id}" style="display:none">${task.task_description}</p>
            </div>
            <p id="pendingText${task.task_id}" class="pending-tasks-text" style="margin-bottom:10px;">You still have pending tasks. Click the button to get started.</p>
            <button id="startTask${task.task_id}Button">Start Task</button>
            <p id="taskInstructions${task.task_id}" style="display:none; color: #1E3A8A;">How did the execution of this task go?</p>
            <button class="task-btn" id="finishTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">check</span>
              Solved it
            </button>
            <button class="task-btn" id="notSureTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">help</span>
              Not sure
            </button>
            <button class="task-btn" id="couldntSolveTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">close</span>
              Couldn't solve
            </button>
          </div>
          <div class="task_review" id="task${task.task_id}_review" style="display:none">
            <h1>Review: ${task.task_title}</h1>
            <p>How was your experience with this task?</p>
            <textarea class="custom-textarea" id="question-${task.task_id}" placeholder="Leave a comment about your experience..."></textarea>
            <button id="task${task.task_id}ReviewButton">Next</button>
          </div>
        </div>
      `);
    });

    // process review
    let html = `<div class="process-review" id="process${proc.process_id}_review" style="display:none">
          <div class="bluebg">
                  <div class="icon-circle">
                      <span class="material-symbols-outlined">assignment</span>
                  </div>
                  <h1 style="color: white;">Procedure Review</h1>
          </div>
        <h1>Review: ${proc.process_title}</h1>
        <div class="questionnaire" style="display: flex; align-items: center; flex-direction: column; padding: 10px;">
      `;

      proc.process_review.forEach((q, i) => {
        html += `
          <div class="question">
            <label for="process-question-${proc.process_id}-${i}">
              ${q.process_review_question_text}
            </label>
            <div class="radio-group">
              <label>
                <input type="radio" name="process-question-${proc.process_id}-${i}" value="yes">
                Yes
              </label>
              <label>
                <input type="radio" name="process-question-${proc.process_id}-${i}" value="partial">
                Partially
              </label>
              <label>
                <input type="radio" name="process-question-${proc.process_id}-${i}" value="no">
                No
              </label>
            </div>
          </div>
        `;
      });

      html += `
          <button id="process${proc.process_id}ReviewButton">Next</button>
        </div>
      </div>`;
    div.insertAdjacentHTML("beforeend", html);

    container.appendChild(div);
  });
}

// 3) Conecta todos os listeners de uma vez
function attachListenersAll() {
  processes.forEach((proc) => {
    proc.process_tasks.forEach((task) => {
      // Start Task
      document.getElementById(`startTask${task.task_id}Button`).addEventListener("click", () => {
        // Armazena timestamp de início
        taskStartTime = new Date().toISOString();
        taskEndTime = null;

        // Mostra título, descrição e instruções
        document.getElementById(`taskTitle${task.task_id}`).style.display = "block";
        document.getElementById(`taskDescription${task.task_id}`).style.display = "block";
        document.getElementById(`taskInstructions${task.task_id}`).style.display = "block";

        // Esconde o texto de pendentes e o botão Start
        document.getElementById(`pendingText${task.task_id}`).style.display = "none";
        document.getElementById(`startTask${task.task_id}Button`).style.display = "none";

        [
          `finishTask${task.task_id}Button`,
          `notSureTask${task.task_id}Button`,
          `couldntSolveTask${task.task_id}Button`
        ].forEach(id => document.getElementById(id).style.display = "inline-block");

        currentPhase = "task";
        updateDisplay();
      });

      // Conseguiu / Não tenho certeza / Não conseguiu
      const typeMap = {
        finish:     "solved",
        notSure:    "notSure",
        couldntSolve: "couldntsolve"
      };

      ["finish", "notSure", "couldntSolve"].forEach(type => {
        document.getElementById(`${type}Task${task.task_id}Button`).addEventListener("click", () => {
          currentTaskStatus = typeMap[type];

          taskEndTime = new Date().toISOString();

          currentPhase = "review";
          updateDisplay();
        });
      });

      // Next: salvar resposta e avançar
      document.getElementById(`task${task.task_id}ReviewButton`).addEventListener("click", () => {
        saveTaskAnswer(proc.process_id, task.task_id);
        if (currentTaskIndex < processes[currentProcessIndex].process_tasks.length - 1) {
          currentTaskIndex++;
          currentPhase = "task";
        } else {
          currentPhase = "processreview";
        }
        updateDisplay();
      });
    });

    // process review next
    document
      .getElementById(`process${proc.process_id}ReviewButton`)
      .addEventListener("click", () => {
        saveProcessAnswers(proc.process_id);
        // avança processo
        if (currentProcessIndex < processes.length - 1) {
          currentProcessIndex++;
          currentTaskIndex = 0;
          currentPhase = "task";
        } else {
          currentPhase = "finalquestionnaire";
        }
        updateDisplay();
      });
  });
}

function saveTaskAnswer(processId, taskId) {
  const answer = document.getElementById(`question-${taskId}`).value;

  tasks_data.push({
    type: "task_review",
    process_id: processId,
    task_id: taskId,
    answer: answer,
    status: currentTaskStatus,
    initialTimestamp: taskStartTime,
    finalTimestamp: taskEndTime
  });

}


function saveProcessAnswers(processId) {
  const proc = processes[currentProcessIndex];
  proc.process_review.forEach((q, i) => {
    const selected = document.querySelector(`input[name="process-question-${processId}-${i}"]:checked`);
    const answerValue = selected ? selected.value : null;
    
    console.log(`Processo ${processId} - Pergunta ${q.process_review_question_id}: ${answerValue}`);

    // Exemplo de armazenamento
    tasks_data.push({
      type: "process_review",
      process_id: processId,
      question_id: q.process_review_question_id,
      answer: answerValue
    });
  });
}

// Função que atualiza a exibição com base na fase e na task atual
function updateDisplay() {
  // 1) Esconde todas as telas principais
  login_page.style.display = "none";
  starttestdiv.style.display = "none";
  questionnaire_page.style.display = "none";
  sync_page.style.display = "none";
  final_questionnaire_page.style.display = "none";
  finalpage.style.display = "none";
  document.getElementById("progressBarContainer").style.display = "none";
  document.querySelectorAll(".taskbox-container").forEach(el => el.style.display = "none");

  // 2) Esconde todos os blocos de tarefa e review
  document.querySelectorAll(".task").forEach(el => el.style.display = "none");
  document.querySelectorAll(".task_review").forEach(el => el.style.display = "none");
  document.querySelectorAll(".process-review").forEach(el => el.style.display = "none");

  // 3) Fluxo de fases
  switch (currentPhase) {
    case "login":
      login_page.style.display = "block";
      break;

    case "sync":
      sync_page.style.display = "flex";
      break;

    case "initial":
      starttestdiv.style.display = "flex";
      break;

    case "questionnaire":
      questionnaire_page.style.display = "flex";
      break;

    case "task":
      // exibe a tarefa atual dentro do processo atual
      const proc = processes[currentProcessIndex];
      const task = proc && proc.process_tasks[currentTaskIndex];
      if (task) {
        // Mostra apenas a taskbox-container da task atual
        document.querySelectorAll(".taskbox-container").forEach(el => el.style.display = "none");
        document.getElementById(`taskbox${task.task_id}`).style.display = "block";

        document.getElementById(`task${task.task_id}`).style.display = "flex";
        updateProgressBar();
        document.getElementById("progressBarContainer").style.display = "block";
      }
    break;

    case "review":
      // exibe o review da tarefa atual
      const proc2 = processes[currentProcessIndex];
      const task2 = proc2 && proc2.process_tasks[currentTaskIndex];
      if (task2) {
        // Mostra apenas a taskbox-container da task atual
        document.querySelectorAll(".taskbox-container").forEach(el => el.style.display = "none");
        document.getElementById(`taskbox${task2.task_id}`).style.display = "block";

        document.getElementById(`task${task2.task_id}_review`).style.display = "flex";
        updateProgressBar();
        document.getElementById("progressBarContainer").style.display = "block";
      }
      break;

    case "processreview":
      // exibe o review completo do processo após todas as tarefas
      const proc3 = processes[currentProcessIndex];
      if (proc3) {
        document.getElementById(`process${proc3.process_id}_review`).style.display = "flex";
      }
      break;

    case "finalquestionnaire":
      final_questionnaire_page.style.display = "flex";
      break;

    case "final":
      finalpage.style.display = "flex";
      break;
  }
}


function getProfileData() {
  const getSelectedValue = (name) => {
    const selected = document.querySelector(`input[name="${name}"]:checked`);
    return selected ? selected.value : null;
  };

  const profileData = {
    academic_level: getSelectedValue("formacao"),
    segment: getSelectedValue("segment"),
    previus_experience: getSelectedValue("previus-experience"),
    years_of_experience: document.getElementById("question-experience").value || null
  };

  return profileData;
}

function getFinalQuestionnaireData() {
  const finalQuestionnaireData = {
    comments : document.getElementById("question-overall").value,
    emotion : document.getElementById("question-emotion").value,
  };
  return finalQuestionnaireData;
}

// Botão para finalizar o questionário final
document.getElementById("finalQuestionnaireButton").addEventListener("click", function () {
  currentPhase = "final";

  data_collection.endTime = new Date().toISOString(); // Salva o timestamp final da avaliação

  data_collection.profile_questionnaire = getProfileData(); // Salva os dados do questionário de perfil

  data_collection.final_questionnaire = getFinalQuestionnaireData(); // Salva os dados do questionário final

  data_collection.performed_tasks = tasks_data;

  updateDisplay();
});

// Botão para finalizar a avaliação e enviar os dados para o Flask
document.getElementById("finishevaluationbtn").addEventListener("click", function () {
    
  // Enviando os dados para o backend Flask

    sendData();
});

// Enviar dados da coleta para o Flask
function sendData() {
  fetch("http://127.0.0.1:5000/submit_tasks", {
    method: "POST",
    headers: {
        "Content-Type": "application/json" // informar ao flask que o dado que esta sendo enviado é um json
    },
    body: JSON.stringify(data_collection)
  })
  .then(response => response.json()) // converte a resposta recebida pela api em um json
  .then(data => { // Agora com os dados convertidos, exibe na tela que foi enviado com sucesso
    document.getElementById("finishevaluationbtn").disabled = true; // Desabilita o botão de finalizar
    console.log("Resposta do servidor:", data);
    alert("Dados enviados com sucesso");
  })
  .catch(error => { //tratamento de erro
    alert("Erro ao enviar os dados");
    console.error("Erro ao enviar os dados:", error);
  });
}

// UI FUNCTIONS
function emotionRange() {
  const rangeInput = document.getElementById('question-emotion');
  const emotionLabels = document.querySelectorAll('.emotion-label');

  function updateLabelStyle() {
    const value = rangeInput.value;

    emotionLabels.forEach(label => {
      const labelEmotion = parseInt(label.dataset.emotion);
      const currentEmotion = parseInt(value);

      const distance = Math.abs(labelEmotion - currentEmotion);
      const opacity = distance <= 1 ? 1 : 0.5;
      label.style.opacity = opacity;
    });
  }

  updateLabelStyle(); // Estilo inicial

  rangeInput.addEventListener('input', updateLabelStyle); // Atualizar opacidade

  emotionLabels.forEach(label => {
    label.addEventListener('click', () => {
      const emotion = label.dataset.emotion;
      rangeInput.value = emotion;
      
      rangeInput.dispatchEvent(new Event('input'));
    });
  });
}

// Função para atualizar a barra de progresso
function updateProgressBar() {
  if (processes.length === 0) return;

  const totalTasks = processes.reduce((sum, proc) => sum + proc.process_tasks.length, 0);

  // Conta quantas tarefas já passaram
  let completedTasks = 0;

  // Soma todas as tarefas dos processos anteriores
  for (let i = 0; i < currentProcessIndex; i++) {
    completedTasks += processes[i].process_tasks.length;
  }

  // Soma as tarefas do processo atual que já passaram
  if (currentPhase === "review" || currentPhase === "task") {
    completedTasks += currentTaskIndex;
  } else if (currentPhase === "processreview") {
    completedTasks += processes[currentProcessIndex].process_tasks.length;
  }

  const progressPercentage = (completedTasks / totalTasks) * 100;

  document.getElementById("progressBarFill").style.width = `${progressPercentage}%`;
  document.getElementById("progressText").textContent = `${completedTasks}/${totalTasks} Tasks Completed`;
}