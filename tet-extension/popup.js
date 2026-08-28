let starttestdiv = document.querySelector(".main_page");
let finalpage = document.querySelector(".final_page");
let questionnaire_page = document.querySelector(".questionnaire_page");
let final_questionnaire_page = document.querySelector(".final_questionnaire_page");
let login_page = document.querySelector(".login_page");
let sync_page = document.querySelector(".sync_page");
let overlay = document.getElementById('overlay');
let questions_page = document.getElementById("questionsPage");

// API Configuration
// Change isDevelopment to false for production deployment
const CONFIG = {
  isDevelopment: true, // Set to false for production
  DEVELOPMENT_URL: "http://127.0.0.1:5000",
  PRODUCTION_URL: "https://seco-tranp-website.vercel.app/", // deployed URL
  get API_BASE_URL() {
    return this.isDevelopment ? this.DEVELOPMENT_URL : this.PRODUCTION_URL;
  }
};

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
let question_data = []; // usa let porque pode ser que eu tenha que reatribuir a variaveldepois, 
// array armanzena as duvidas recebidas, entao quando comeca a avaliacao ta como null = nenhim,a registrada
let nextQuestionId = 1 // variavel guarda qual vai ser o id da proxima duvida criada
let todo_tasks = [];   // Armazena as tasks recebidas em formato de objeto para serem feitas
let processes = []; // Cada processo tem tarefas e perguntas do review
let currentProcessIndex = 0;
let currentTaskIndex = -1; // Índice da task atual (-1 significa página incial e 0 significa primeira task e por ai vai)
let currentPhase = "login"; // Pode ser "login", "sync","initial","questionnaire", "task", "review", "processreview" ,"finalquestionnaire" ou "final", serve para configurar a exibição na tela
let currentTaskTimestamp = "Erro ao obter o timestamp"; // Armazena o timestamp da task atual
let currentTaskStatus = "solving" // alterado para "solved" ou "couldntsolve" no botão de finalizar a task
let taskStartTime = null; // Armazena o timestamp da task atual
let taskEndTime = null; // Armazena o timestamp da task atual
let isSubmitting = false; // Evita envios duplicados do resultado

// Task context tracking for navigation
let activeTaskContext = {
  taskId: null,
  processId: null,
  startTime: null,
  endTime: null
};

// Task boundary tracking
let taskBoundaries = {
  isTaskActive: false,
  pendingNavigationEvents: [],
  lastTaskId: null
};

function resolveCurrentTaskId() {
  if (activeTaskContext.taskId) {
    return activeTaskContext.taskId;
  }

  if (currentPhase === "task" && currentProcessIndex >= 0 && currentTaskIndex >= 0) {
    const currentProcess = processes[currentProcessIndex];
    if (currentProcess && currentProcess.process_tasks[currentTaskIndex]) {
      return currentProcess.process_tasks[currentTaskIndex].task_id;
    }
  }

  if (taskBoundaries.lastTaskId) {
    return taskBoundaries.lastTaskId;
  }

  return null;
}

function addQuestion(text) { // o parametro text indica que pra executar a funcao, eh necessario receber o texto da duvida
  const taskId = resolveCurrentTaskId(); // cria a constante task puxando o valor que indica a task atual com a funcao criada no codigo
  const process = processes[currentProcessIndex]; // queremos registrar na pergunta process_id e task_id e nao um so, pra saber a rota certinha feita pelo usuario
  if (!taskId || !process) { // traducao: se nao existir id de tarefa ou processo
    console.error("n existe tarefa ou processo atuaç") // imprime mensagem de erro no console
    return; // como nao tem nenhum valor (nem null), a funcao so eh encerrada, entao nao vamo registrar dados incompletos/sujos
  }
  const question = {
    id: nextQuestionId,
    task_id: taskId,
    process_id: process.process_id,
    text: text,
    status: "open"
  };

  questions_data.push(question); // push serve p adicionar a duvida
  nextQuestionId++; // aumenta a contagem da variavel pra que a proxima duvida seja enumerada corretamente
}

function getCurrentTaskQuestions() { // funcao pra puxar as duvidas da task atual do usuario
  const taskId = resolveCurrentTaskId();
  if (!taskId) {
    return []; // array em vez de nada porque a intencao eh devolver lista de duvidas, o array vazio mostra que a lista ta vazua
  } // mesmos acontecimentos da anterior, mas sem puxar processo atual dessa vez, ja que nao precisamos do id dele

  const currentQuestions = []; // armazena temporariamente as duvdas da tarefa atual

  for (let i = 0; i < questions_data.lenght; // enquanro a variavel criada for menor que o tamanho do array de perguntas
    i++) { // incrementa
    if (questions_data[i].task_id === taskId) { // pega o objeto da duvida na posicao indicada e acessa o task_id 
    // depois compara se o id da tarefa da duvida eh exatamente igual ao id da tarefa atual ou nao
      currentQuestions.push(questions_data[i]); // adiciona a duvida que passou na comparacao ao final do array currentQuestions
    }
  }
  return currentQuestions; // devolve o array ja filtrado com as duvidas da tarefa atual só
}

function openQuestionsPage() { // funcao pra abrir a pagina de my questions apos o clique no botao
  const tasksContainer = document.getElementById("taskscontainer"); // declara a variavel e procura o elemento do container do html
  const questionsPage = document.getElementById("questionsPage"); // mesma coisa mas com o questionsPage do html
  tasksContainer.style.display = "none";  //  esconde o container de tarefas
  questionsPage.style.display = "block"; // faz a pagina de duvs aparecer
}

function recordNavigationEvent({
  action = "pageNavigation",
  url,
  title = "",
  timestamp = new Date().toISOString(),
  taskId,
  phase = currentPhase,
  taskIndex = currentTaskIndex,
  processIndex = currentProcessIndex,
  source = "event"
}) {
  if (!url || !taskId) {
    console.warn("⚠️ Skipping navigation record due to missing url/taskId", { url, taskId, source });
    return false;
  }

  if (source === "finalSnapshot") {
    const hasSameEntry = data_collection.navigation.some(entry => entry.taskId === taskId && entry.url === url);
    if (hasSameEntry) {
      console.log("🛑 Final snapshot skipped (duplicate for task)", { url, taskId });
      return false;
    }
  }

  const lastEntry = data_collection.navigation[data_collection.navigation.length - 1];
  if (lastEntry && lastEntry.url === url && lastEntry.taskId === taskId && lastEntry.action === action) {
    const lastTs = new Date(lastEntry.timestamp).getTime();
    const currentTs = new Date(timestamp).getTime();
    if (!Number.isNaN(lastTs) && !Number.isNaN(currentTs) && Math.abs(currentTs - lastTs) < 2000) {
      console.log("🔁 Navigation deduplicated", { url, taskId, source });
      return false;
    }
  }

  const entry = {
    action,
    title,
    url,
    timestamp,
    taskId,
    phase,
    taskIndex,
    processIndex,
    source
  };

  data_collection.navigation.push(entry);
  console.log("🧭 Navigation recorded:", entry, { navigationCount: data_collection.navigation.length });
  return true;
}

function captureCurrentTabNavigation({ source = "snapshot", taskIdOverride = null } = {}) {
  const resolvedTaskId = taskIdOverride || resolveCurrentTaskId();
  if (!resolvedTaskId) {
    console.warn("⚠️ No task id available for navigation snapshot", { source });
    return;
  }

  try {
    chrome.tabs.query({ active: true, currentWindow: true }, function(tabs) {
      if (chrome.runtime.lastError) {
        console.error("❌ Error capturing tab navigation:", chrome.runtime.lastError.message);
        return;
      }

      const activeTab = tabs && tabs[0];
      if (!activeTab || !activeTab.url) {
        console.warn("⚠️ No active tab information available for snapshot", { source });
        return;
      }

      recordNavigationEvent({
        url: activeTab.url,
        title: activeTab.title || "",
        timestamp: new Date().toISOString(),
        taskId: resolvedTaskId,
        phase: currentPhase,
        taskIndex: currentTaskIndex,
        processIndex: currentProcessIndex,
        source
      });
    });
  } catch (error) {
    console.error("❌ Exception capturing tab navigation:", error);
  }
}


// Enhanced Navigation tracking with precise task boundary detection
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  try {
    const shouldTrackNavigation = currentPhase === "task" || currentPhase === "review" || currentPhase === "processreview" || currentPhase === "initial";

    if (shouldTrackNavigation) {
      if (request.action === "pageNavigation" || request.action === "tabSwitch") {
        const currentTaskId = resolveCurrentTaskId();
        const recorded = recordNavigationEvent({
          action: request.action,
          url: request.url,
          title: request.title,
          timestamp: request.timestamp,
          taskId: currentTaskId,
          phase: currentPhase,
          taskIndex: currentTaskIndex,
          processIndex: currentProcessIndex,
          source: "runtimeEvent"
        });

        sendResponse(recorded ? { status: "success", navigationCount: data_collection.navigation.length } : { status: "skipped" });
      }
    } else {
      console.log("🚫 Navigation not tracked - Current phase:", currentPhase);
    }
  } catch (error) {
    console.error("❌ Error processing navigation message:", error);
    sendResponse({status: "error", error: error.message});
  }
});


document.getElementById("mainPageButton").addEventListener("click", function () {
  starttestdiv.style.display = "none";
  currentPhase = "questionnaire";

  updateDisplay();
});

// Botão de finalizar questionário de perfil
document.getElementById("questionnaireButton").addEventListener("click", function () {
  // Validação do formulário de perfil
  const requiredRadios = [
    "formacao",
    "segment",
    "previus-experience"
  ];
  let valid = true;

  // Remove erros anteriores
  requiredRadios.forEach(name => {
    // Remove erro de todos os radio groups antes de validar
    document.querySelectorAll(`input[name="${name}"]`).forEach(input => {
      input.closest('.radio-group').classList.remove("input-error");
    });
  });

  requiredRadios.forEach(name => {
    const checked = document.querySelector(`input[name="${name}"]:checked`);
    if (!checked) {
      valid = false;
      // Adiciona erro ao grupo de radio correspondente
      const group = document.querySelector(`input[name="${name}"]`).closest('.radio-group');
      if (group) group.classList.add("input-error");
    }
  });

  const yearsInput = document.getElementById("question-experience");
  if (!yearsInput.value || yearsInput.value < 0 || yearsInput.value > 100) {
    valid = false;
    yearsInput.classList.add("input-error");
  } else {
    yearsInput.classList.remove("input-error");
  }

  if (!valid) {
    alert("Please fill in all required fields before starting the evaluation.");
    return;
  }


  currentTaskIndex = 0;
  currentPhase = "task";
  data_collection.startTime = new Date().toISOString(); // Salva o timestamp inicial da avaliação
  updateDisplay();
});

// Autentificação
document.getElementById("verifyButton").addEventListener("click", function () {
  let authcode = document.getElementById("authcode").value;

  auth_evaluation(authcode) // Envia o código para autenticação
    .then((isValid) => {
      if (isValid) {
        console.log("Código de avaliação válido");
        currentPhase = "sync";
        data_collection.evaluation_code = authcode; // Salva o código de avaliação na variável global
        updateDisplay(); // Atualiza a exibição para a fase de sincronização
      } else {
        console.error("Código de avaliação inválido");
        document.getElementById("errorMessage").style.display = "block";
      }
    });

});


// Sincronizar código com API DO UX-TRACKING
document.getElementById("syncButton").addEventListener("click", function () {
  const syncButton = document.getElementById("syncButton");
  const buttonText = syncButton.querySelector(".sync-button-text");
  const buttonLoader = syncButton.querySelector(".sync-button-loader");
  const syncStatus = document.getElementById("syncStatus");
  const syncSuccess = document.getElementById("syncSuccess");
  
  // Hide previous messages
  syncStatus.style.display = "none";
  syncSuccess.style.display = "none";
  
  // Show loading state
  syncButton.disabled = true;
  buttonText.style.display = "none";
  buttonLoader.style.display = "inline-flex";
  
  overlay.style.display = 'block'; // Exibe o overlay de carregamento

  setTimeout(() => {
    overlay.style.display = 'none';
  }, 5000);

  let uxt_mode = false; // Opção de fazer a avaliação com UX-Tracking o não

  if (uxt_mode) {
    fetch("https://uxt.liis.com.br/data/syncsession", {
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
          console.log("Sync response:", data);
          
          // VALIDATE: Check if UX-Tracking is actually synchronized
          // The sync is only successful if we have a valid sessionId and cod
          const hasValidSessionId = data.sessionId && 
                                    data.sessionId !== "0" && 
                                    data.sessionId !== 0 && 
                                    data.sessionId !== null && 
                                    data.sessionId !== undefined;
          
          const hasValidCod = data.cod && 
                             data.cod !== "" && 
                             data.cod !== null && 
                             data.cod !== undefined;
          
          if (!hasValidSessionId || !hasValidCod) {
            // UX-Tracking not synchronized - show error
            console.warn("Sync failed: Invalid session data", { sessionId: data.sessionId, cod: data.cod });
            
            buttonText.style.display = "inline-flex";
            buttonLoader.style.display = "none";
            syncButton.disabled = false;
            syncStatus.style.display = "flex";
            
            // Update error message
            const statusText = syncStatus.textContent || syncStatus.innerText;
            if (statusText) {
              syncStatus.textContent = "UX-Tracking is not active. Please start the session in UX-Tracking first, then try again.";
            }
            return;
          }
          
          // Valid sync - proceed
          data_collection.uxt_cod = data.cod;
          data_collection.uxt_sessionId = data.sessionId; 

          // Show success state
          buttonText.style.display = "inline-flex";
          buttonLoader.style.display = "none";
          syncButton.disabled = false;
          syncSuccess.style.display = "flex";
          
          // Navigate after short delay
          setTimeout(() => {
            fetchtasks(data_collection.evaluation_code);
          }, 1500);
        });
      } else {
        return response.json().then(errorData => {
          console.error(`Error: ${response.status} - ${errorData.message || response.statusText}`);
  
          // Show error state
          buttonText.style.display = "inline-flex";
          buttonLoader.style.display = "none";
          syncButton.disabled = false;
          syncStatus.style.display = "flex";
        }).catch(() => {
          console.error(`Error: ${response.status} - ${response.statusText}`);
  
          // Show error state
          buttonText.style.display = "inline-flex";
          buttonLoader.style.display = "none";
          syncButton.disabled = false;
          syncStatus.style.display = "flex";
        });
      }
    })
    .catch(error => {
      console.error("Fetch error:", error);
      
      // Show error state
      buttonText.style.display = "inline-flex";
      buttonLoader.style.display = "none";
      syncButton.disabled = false;
      syncStatus.style.display = "flex";
    });
  } else {
    // Se não for usar UX-Tracking, apenas salva os dados e avança
    data_collection.uxt_cod = "default";
    data_collection.uxt_sessionId = "0";

    // Show success state
    buttonText.style.display = "inline-flex";
    buttonLoader.style.display = "none";
    syncButton.disabled = false;
    syncSuccess.style.display = "flex";

    setTimeout(() => {
      currentPhase = "initial";
      fetchtasks(data_collection.evaluation_code);
    }, 1500);
  }

});

function auth_evaluation(code) {
  return fetch(`${CONFIG.API_BASE_URL}/auth_evaluation`, {
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
  fetch(`${CONFIG.API_BASE_URL}/load_tasks`, {
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
            <p id="pendingText${task.task_id}" class="pending-tasks-text" style="margin-bottom:10px;">You still have pending scenarios. Click the button to get started.</p>
            <button id="startTask${task.task_id}Button">Start Scenario</button>
            
            <p id="questionsText${task.task_id}" style="display:none; color: #1E3A8A">
            Post any questions regarding the scenario here: 
            </p>

            <button class="task-btn" name="duvidas-botao" id="questionsTask${task.task_id}Button" style="display:none;" type="button">
            <span class="material-symbols-outlined icon-botao">help</span>
            Your Questions
            </button>

            <p id="taskInstructions${task.task_id}" style="display:none; color: #1E3A8A;">Do you believe you have achieved the goal of this scenario?</p>
            <button class="task-btn" id="finishTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">check</span>
              Yes, completely
            </button>
            <button class="task-btn" id="notSureTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">help</span>
              Partially
            </button>
            <button class="task-btn" id="couldntSolveTask${task.task_id}Button" style="display:none">
              <span class="material-symbols-outlined icon-botao">close</span>
              No
            </button>
          </div>
          <div class="task_review" id="task${task.task_id}_review" style="display:none">
            <h1>Review: ${task.task_title}</h1>
            <p>Briefly describe your experience in this scenario: what helped or hindered you in finding the information you needed?</p>
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
            <div class="slider-container">
              <div class="slider-labels">
                <span class="slider-label-left">Not perceived</span>
                <span class="slider-label-right">Fully perceived</span>
              </div>
              <input type="range" 
                     id="process-question-${proc.process_id}-${i}" 
                     name="process-question-${proc.process_id}-${i}" 
                     min="0" 
                     max="100" 
                     value="50" 
                     class="slider">
              <div class="slider-value">
                <span id="slider-value-${proc.process_id}-${i}" style="display: none;">50</span>
              </div>
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
  // Adiciona listeners para os sliders dos process reviews
  processes.forEach((proc) => {
    proc.process_review.forEach((q, i) => {
      const sliderId = `process-question-${proc.process_id}-${i}`;
      const valueId = `slider-value-${proc.process_id}-${i}`;
      
      // Wait a bit for DOM to be ready
      setTimeout(() => {
        const slider = document.getElementById(sliderId);
        const valueSpan = document.getElementById(valueId);
        
        if (slider && valueSpan) {
          slider.addEventListener('input', function() {
            valueSpan.textContent = this.value;
          });
        }
      }, 100);
    });
  });

  processes.forEach((proc) => {
    proc.process_tasks.forEach((task) => {
      // Start Task
      document.getElementById(`startTask${task.task_id}Button`).addEventListener("click", () => {
        // Armazena timestamp de início
        taskStartTime = new Date().toISOString();
        taskEndTime = null;

        // Set active task context for navigation tracking
        activeTaskContext = {
          taskId: task.task_id,
          processId: proc.process_id,
          startTime: taskStartTime,
          endTime: null
        };

        // Update task boundaries
        taskBoundaries.isTaskActive = true;
        taskBoundaries.lastTaskId = task.task_id;

        console.log("🎯 Task started:", {
          taskId: task.task_id,
          processId: proc.process_id,
          startTime: taskStartTime,
          taskBoundaries: taskBoundaries
        });

        // Mostra título, descrição e instruções
        document.getElementById(`taskTitle${task.task_id}`).style.display = "block";
        document.getElementById(`taskDescription${task.task_id}`).style.display = "block";
        document.getElementById(`taskInstructions${task.task_id}`).style.display = "block";

        // mostr a texto de duvidas e o botao "my questions"
        document.getElementById(`questionsText${task.task_id}`).style.display = "block";
        document.getElementById(`questionsTask${task.task_id}Button`).style.display = "flex";

        // Esconde o texto de pendentes e o botão Start
        document.getElementById(`pendingText${task.task_id}`).style.display = "none";
        document.getElementById(`startTask${task.task_id}Button`).style.display = "none";

        [
          `finishTask${task.task_id}Button`,
          `notSureTask${task.task_id}Button`,
          `couldntSolveTask${task.task_id}Button`
        ].forEach(id => document.getElementById(id).style.display = "flex");

        currentPhase = "task";
        updateDisplay();
        captureCurrentTabNavigation({ source: "initialSnapshot", taskIdOverride: task.task_id });
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

          if (activeTaskContext.taskId === task.task_id) {
            activeTaskContext.endTime = taskEndTime;
            console.log("🏁 Task ended:", {
              taskId: task.task_id,
              processId: proc.process_id,
              endTime: taskEndTime,
              status: typeMap[type]
            });
          }

          captureCurrentTabNavigation({ source: "finalSnapshot", taskIdOverride: task.task_id });

          taskBoundaries.isTaskActive = false;

          currentPhase = "review";
          updateDisplay();
        });
      });

      const questionsButton = document.getElementById(
        `questionsTask${task.task_id}Button`
      );

      if (questionsButton) {
        questionsButton.addEventListener("click", function () {
          currentPhase = "questions";
          updateDisplay();
        });
      }


      // Next: salvar resposta e avançar
      document.getElementById(`task${task.task_id}ReviewButton`).addEventListener("click", () => {
        saveTaskAnswer(proc.process_id, task.task_id);
        
        // Clear active task context when moving to next task
        activeTaskContext = {
          taskId: null,
          processId: null,
          startTime: null,
          endTime: null
        };
        
        // Clear task boundaries
        taskBoundaries.isTaskActive = false;
        taskBoundaries.lastTaskId = null;
        
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
        
        // Clear active task context when moving to next process
        activeTaskContext = {
          taskId: null,
          processId: null,
          startTime: null,
          endTime: null
        };
        
        // Clear task boundaries
        taskBoundaries.isTaskActive = false;
        taskBoundaries.lastTaskId = null;
        
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
    const slider = document.getElementById(`process-question-${processId}-${i}`);
    const answerValue = slider ? parseInt(slider.value) : null;
    
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
  questions_page.style.display = "none";
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

    case "questions": 
      openQuestionsPage()
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

  const commentsInput = document.getElementById("question-overall");

  // Validação do formulário final
  const comments = document.getElementById("question-overall").value.trim();

  let valid = true;

  if (!comments) {
    commentsInput.classList.add("input-error");
    valid = false;
    alert("Please fill in all fields before finishing the evaluation.");
    return;
  }

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
  // Evita envios duplicados
  if (isSubmitting) {
    return Promise.resolve();
  }
  isSubmitting = true;

  const btn = document.getElementById("finishevaluationbtn");
  if (btn) {
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.dataset.originalText = originalText;
    btn.textContent = "Submitting...";
    btn.classList.add('btn-loading');
  }
  console.log("📤 Sending data to backend:", {
    evaluation_code: data_collection.evaluation_code,
    navigation_count: data_collection.navigation.length,
    performed_tasks_count: data_collection.performed_tasks.length,
    navigation_samples: data_collection.navigation.slice(0, 3) // Show first 3 navigation entries
  });

  return fetch(`${CONFIG.API_BASE_URL}/submit_tasks`, {
    method: "POST",
    headers: {
        "Content-Type": "application/json" // informar ao flask que o dado que esta sendo enviado é um json
    },
    body: JSON.stringify(data_collection)
  })
  .then(response => response.json()) // converte a resposta recebida pela api em um json
  .then(data => { // Agora com os dados convertidos, exibe na tela que foi enviado com sucesso
    const btnGuard = document.getElementById("finishevaluationbtn");
    if (btnGuard) {
      btnGuard.disabled = true;
      btnGuard.classList.remove('btn-loading');
      btnGuard.textContent = "Submitted";
    }
    // Mostrar aviso de finalizar UX-Tracking somente após envio com sucesso
    const notice = document.getElementById("uxtEndBlock");
    if (notice) notice.style.display = "block";
    // Esconder instrução inicial após envio
    const instruction = document.getElementById("submitInstruction");
    if (instruction) instruction.style.display = "none";
    console.log("Resposta do servidor:", data);
    alert("Dados enviados com sucesso");
    // Toast feedback
    const toast = document.getElementById('toast');
    if (toast) {
      toast.textContent = 'Submission successful. You may stop UX‑tracking now.';
      toast.style.display = 'block';
      setTimeout(() => { toast.style.display = 'none'; }, 3000);
    }
  })
  .catch(error => { //tratamento de erro
    alert("Erro ao enviar os dados");
    console.error("Erro ao enviar os dados:", error);
    const btnReenable = document.getElementById("finishevaluationbtn");
    if (btnReenable) {
      btnReenable.disabled = false;
      btnReenable.classList.remove('btn-loading');
      btnReenable.textContent = btnReenable.dataset.originalText || btnReenable.textContent || "Submit and Finish evaluation";
    }
    isSubmitting = false;
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

  let completedTasks = 0;

  for (let i = 0; i < currentProcessIndex; i++) {
    completedTasks += processes[i].process_tasks.length;
  }

  if (currentPhase === "review" || currentPhase === "task") {
    completedTasks += currentTaskIndex;
  } else if (currentPhase === "processreview") {
    completedTasks += processes[currentProcessIndex].process_tasks.length;
  }

  const progressPercentage = (completedTasks / totalTasks) * 100;

  // Atualiza a barra de progresso
  document.getElementById("progressBarFill").style.width = `${progressPercentage}%`;

  const currentTaskNumber = Math.min(completedTasks + 1, totalTasks);
  document.getElementById("progressText").textContent = `Scenario ${currentTaskNumber} of ${totalTasks}`;
}

// Extension Help Widget functionality
(function () {
  const widget = document.getElementById("extensionHelpWidget");
  if (!widget) return;

  const launcher = widget.querySelector(".extension-help__launcher");
  const closeBtn = widget.querySelector(".extension-help__close");
  const videoPlayer = document.getElementById("extensionVideoPlayer");

  const setCollapsed = (collapsed) => {
    widget.classList.toggle("extension-help--collapsed", collapsed);
    if (launcher) {
      launcher.setAttribute("aria-hidden", collapsed ? "false" : "true");
      launcher.tabIndex = collapsed ? 0 : -1;
    }
    if (closeBtn) {
      closeBtn.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }
    
    // When opening, start video and enter picture-in-picture
    if (!collapsed && videoPlayer) {
      // Start playing the video
      videoPlayer.play().catch(err => {
        console.log("Autoplay prevented:", err);
      });
      
      // Enter picture-in-picture mode after a short delay
      // Note: PiP requires user interaction, so we trigger it after the click event
      setTimeout(() => {
        if (videoPlayer.requestPictureInPicture && document.pictureInPictureElement !== videoPlayer) {
          videoPlayer.requestPictureInPicture().catch(err => {
            console.log("Picture-in-picture not available:", err);
          });
        }
      }, 500);
    } else if (collapsed && videoPlayer) {
      // Pause video when closing
      videoPlayer.pause();
      // Exit picture-in-picture if active
      if (document.pictureInPictureElement === videoPlayer && document.exitPictureInPicture) {
        document.exitPictureInPicture().catch(err => {
          console.log("Exit picture-in-picture error:", err);
        });
      }
    }
  };

  launcher?.addEventListener("click", () => setCollapsed(false));
  closeBtn?.addEventListener("click", () => setCollapsed(true));

  // Initialize state - start collapsed
  setCollapsed(true);
})();

// Tutorial Carousel functionality
(function () {
  const carousel = document.querySelector(".tutorial-carousel");
  if (!carousel) return;

  const images = Array.from(carousel.querySelectorAll(".tutorial-carousel__image"));
  const dots = Array.from(carousel.querySelectorAll(".tutorial-carousel__dot"));
  const prevBtn = carousel.querySelector(".tutorial-carousel__arrow--prev");
  const nextBtn = carousel.querySelector(".tutorial-carousel__arrow--next");
  
  let currentStep = 1;
  const totalSteps = images.length;
  let direction = 1; // 1 = forward, -1 = backward
  let autoAdvanceInterval = null;
  let userInteracted = false;

  const showStep = (step) => {
    // Update images
    images.forEach((img, index) => {
      if (index + 1 === step) {
        img.classList.add("tutorial-carousel__image--active");
      } else {
        img.classList.remove("tutorial-carousel__image--active");
      }
    });

    // Update dots
    dots.forEach((dot, index) => {
      if (index + 1 === step) {
        dot.classList.add("tutorial-carousel__dot--active");
      } else {
        dot.classList.remove("tutorial-carousel__dot--active");
      }
    });

    currentStep = step;
  };

  const nextStep = () => {
    if (currentStep >= totalSteps) {
      direction = -1; // Switch to backward
      showStep(currentStep - 1);
    } else {
      showStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep <= 1) {
      direction = 1; // Switch to forward
      showStep(currentStep + 1);
    } else {
      showStep(currentStep - 1);
    }
  };

  const autoAdvance = () => {
    if (direction === 1) {
      nextStep();
    } else {
      prevStep();
    }
  };

  const startAutoAdvance = () => {
    if (autoAdvanceInterval) clearInterval(autoAdvanceInterval);
    autoAdvanceInterval = setInterval(autoAdvance, 4000); // Change every 4 seconds
  };

  const stopAutoAdvance = () => {
    if (autoAdvanceInterval) {
      clearInterval(autoAdvanceInterval);
      autoAdvanceInterval = null;
    }
  };

  const handleUserInteraction = () => {
    if (!userInteracted) {
      userInteracted = true;
      stopAutoAdvance();
      // Resume after 10 seconds of no interaction
      setTimeout(() => {
        if (userInteracted) {
          userInteracted = false;
          startAutoAdvance();
        }
      }, 10000);
    }
  };

  // Button events
  nextBtn?.addEventListener("click", () => {
    nextStep();
    handleUserInteraction();
  });
  prevBtn?.addEventListener("click", () => {
    prevStep();
    handleUserInteraction();
  });

  // Dot events
  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => {
      showStep(index + 1);
      handleUserInteraction();
    });
  });

  // Keyboard navigation
  carousel.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") {
      e.preventDefault();
      prevStep();
      handleUserInteraction();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      nextStep();
      handleUserInteraction();
    }
  });

  // Pause on hover
  carousel.addEventListener("mouseenter", stopAutoAdvance);
  carousel.addEventListener("mouseleave", () => {
    if (!userInteracted) {
      startAutoAdvance();
    }
  });

  // Initialize
  showStep(1);
  startAutoAdvance();
})();
