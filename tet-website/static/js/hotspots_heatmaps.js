document.addEventListener('DOMContentLoaded', () => {
  const idElem = document.getElementById('id-avaliacao');
  if (!idElem) {
    console.warn('Element #evaluation-id not found. No heatmap will be loaded.');
    return;
  }

  const id = idElem.textContent.trim();
  const root = document.getElementById('heatmaps-root');
  const filtersContainer = document.getElementById('task-filters');
  
  if (!root || !filtersContainer) return;

  let availableTasks = [];
  let heatmapContainers = [];

  root.innerHTML = '<p class="loading">Loading heatmaps...</p>';

  // Usar nova API que mapeia heatmaps com tarefas
  fetch(`/api/heatmap-tasks/${id}`)
    .then(response => {
      if (!response.ok) throw new Error(`Network error: ${response.status} ${response.statusText}`);
      return response.json();
    })
    .then(data => {
      root.innerHTML = '';
      
      const heatmaps = data.heatmaps || [];
      availableTasks = data.available_tasks || [];

      // Criar filtros baseados nas tarefas disponíveis
      setupTaskFilters(availableTasks);

      if (heatmaps.length === 0) {
        root.innerHTML = '<p>No heatmaps found for this evaluation.</p>';
        return;
      }

      heatmaps.forEach((heatmapData, index) => {
        // Analisar tarefas presentes neste heatmap
        const tasksInHeatmap = getTasksFromPoints(heatmapData.points || []);
        
        // Criar wrapper para o heatmap
        const container = createHeatmapContainer(heatmapData, index, tasksInHeatmap);
        root.appendChild(container);
        heatmapContainers.push(container);

        // Inicializar heatmap
        initializeHeatmap(container, heatmapData, index);
      });
    })
    .catch(error => {
      console.error('Error loading or processing heatmap data:', error);
      root.innerHTML = `<p>Error loading heatmaps: ${error.message}</p>`;
    });

  // Função para configurar filtros
  function setupTaskFilters(tasks) {
    // Limpar filtros existentes (manter apenas "Show All")
    const existingFilters = filtersContainer.querySelectorAll('.filter-item:not(:first-child)');
    existingFilters.forEach(item => item.remove());

    // Adicionar filtro para cada tarefa
    tasks.forEach(task => {
      const filterItem = document.createElement('div');
      filterItem.className = 'filter-item';
      
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.id = `filter-task-${task.task_id}`;
      checkbox.checked = true;
      
      const label = document.createElement('label');
      label.htmlFor = checkbox.id;
      label.textContent = task.title;
      
      filterItem.appendChild(checkbox);
      filterItem.appendChild(label);
      filtersContainer.appendChild(filterItem);

      // Adicionar event listener para o filtro
      checkbox.addEventListener('change', handleFilterChange);
    });

    // Configurar filtro "Show All"
    const showAllCheckbox = document.getElementById('filter-all');
    if (showAllCheckbox) {
      showAllCheckbox.addEventListener('change', handleShowAllChange);
    }
  }

  // Função para extrair tarefas únicas dos pontos do heatmap
  function getTasksFromPoints(points) {
    const tasks = new Set();
    points.forEach(point => {
      if (point.active_task && point.active_task.task_id) {
        tasks.add(point.active_task.task_id);
      }
    });
    return Array.from(tasks);
  }

  // Função para criar container do heatmap com interface moderna
  function createHeatmapContainer(heatmapData, index, tasksInHeatmap) {
    const container = document.createElement('div');
    container.classList.add('heatmap-wrapper');
    
    // Estilos modernos base
    Object.assign(container.style, {
      position: 'relative',
      maxWidth: '100%',
      marginBottom: '32px',
      borderRadius: '16px',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
      border: '1px solid rgba(255, 255, 255, 0.18)',
      background: 'linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      width: heatmapData.width ? `${heatmapData.width}px` : '640px',
      height: heatmapData.height ? `${heatmapData.height}px` : '360px'
    });
    
    // Hover effect
    container.addEventListener('mouseenter', () => {
      container.style.transform = 'translateY(-4px)';
      container.style.boxShadow = '0 12px 48px rgba(0, 0, 0, 0.18)';
    });
    
    container.addEventListener('mouseleave', () => {
      container.style.transform = 'translateY(0)';
      container.style.boxShadow = '0 8px 32px rgba(0, 0, 0, 0.12)';
    });
    
    // Adicionar atributos para filtragem (normalizados)
    container.dataset.heatmapIndex = index;
    if (tasksInHeatmap.length > 0) {
      container.dataset.taskIds = tasksInHeatmap.map(normalizeTaskId).join(',');
    }

    // Criar overlay moderno de tarefas ao invés de badge
    if (tasksInHeatmap.length > 0) {
      const taskOverlay = createTaskOverlay(tasksInHeatmap);
      container.appendChild(taskOverlay);
    }

    // Adicionar indicador de cobertura se disponível
    if (heatmapData.metadata && heatmapData.metadata.coverage_percentage) {
      const coverageIndicator = createCoverageIndicator(heatmapData.metadata);
      container.appendChild(coverageIndicator);
    }

    return container;
  }

  // Função para criar overlay moderno de tarefas
  function createTaskOverlay(tasksInHeatmap) {
    const overlay = document.createElement('div');
    overlay.className = 'task-overlay';
    
    Object.assign(overlay.style, {
      position: 'absolute',
      top: '16px',
      left: '16px',
      right: '16px',
      zIndex: '10',
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px',
      pointerEvents: 'none'
    });

    tasksInHeatmap.forEach(taskId => {
      const task = availableTasks.find(t => normalizeTaskId(t.task_id) === normalizeTaskId(taskId));
      if (task) {
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        
        Object.assign(taskCard.style, {
          background: 'rgba(59, 130, 246, 0.9)',
          color: 'white',
          padding: '8px 16px',
          borderRadius: '12px',
          fontSize: '14px',
          fontWeight: '600',
          backdropFilter: 'blur(12px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          maxWidth: '200px',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          animation: 'slideInDown 0.3s ease-out'
        });
        
        taskCard.textContent = task.title;
        taskCard.title = `${task.title}${task.description ? ': ' + task.description : ''}`;
        overlay.appendChild(taskCard);
      }
    });

    return overlay;
  }

  // Função para criar indicador de cobertura
  function createCoverageIndicator(metadata) {
    const indicator = document.createElement('div');
    indicator.className = 'coverage-indicator';
    
    Object.assign(indicator.style, {
      position: 'absolute',
      bottom: '16px',
      right: '16px',
      background: 'rgba(34, 197, 94, 0.9)',
      color: 'white',
      padding: '6px 12px',
      borderRadius: '8px',
      fontSize: '12px',
      fontWeight: '600',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      zIndex: '10'
    });
    
    indicator.textContent = `${metadata.coverage_percentage}% mapped`;
    indicator.title = `${metadata.points_with_tasks}/${metadata.total_points} points mapped to tasks`;
    
    return indicator;
  }

  // Função para inicializar heatmap
  function initializeHeatmap(container, heatmapData, index) {
    const img = new Image();
    const mime = heatmapData.mime || 'image/jpeg';
    img.src = `data:${mime};base64,${heatmapData.image}`;
    img.alt = heatmapData.title || `Heatmap ${index + 1}`;
    img.style.position = 'absolute';
    img.style.top = '0';
    img.style.left = '0';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';
    img.style.display = 'block';

    const initHeatmap = () => {
      const naturalW = img.naturalWidth || heatmapData.width || container.clientWidth;
      const naturalH = img.naturalHeight || heatmapData.height || container.clientHeight;
      const sourceW = heatmapData.width || naturalW;
      const sourceH = heatmapData.height || naturalH;

      container.style.width = `${naturalW}px`;
      container.style.height = `${naturalH}px`;
      container.appendChild(img);

      const heatmapInstance = h337.create({
        container: container,
        radius: 40,
        maxOpacity: 0.6,
        blur: 0.9,
      });

      const scaleX = container.clientWidth / sourceW;
      const scaleY = container.clientHeight / sourceH;

      const pts = (heatmapData.points || []).map(point => ({
        x: Math.round((point.x || 0) * scaleX),
        y: Math.round((point.y || 0) * scaleY),
        value: Math.max(1, Math.round((point.intensity || 0) * 700)),
      }));

      const maxVal = pts.length ? Math.max(...pts.map(p => p.value)) : 100;
      try {
        heatmapInstance.setData({ max: Math.max(maxVal, 100), data: pts });
      } catch (err) {
        console.error('Error setting data on heatmapInstance:', err);
        const errMsg = document.createElement('p');
        errMsg.textContent = `Error rendering heatmap ${index + 1}: ${err.message}`;
        container.appendChild(errMsg);
      }
    };

    if (img.decode) {
      img.decode().then(initHeatmap).catch(err => {
        console.warn('img.decode failed, using onload as fallback', err);
        img.onload = initHeatmap;
        img.onerror = handleImageError;
      });
    } else {
      img.onload = initHeatmap;
      img.onerror = handleImageError;
    }

    function handleImageError() {
      console.error('Error loading heatmap image');
      container.remove();
      const em = document.createElement('p');
      em.textContent = `Error loading heatmap image ${index + 1}.`;
      root.appendChild(em);
    }
  }

  // Função para normalizar task IDs (garantir consistência string/number)
  function normalizeTaskId(id) {
    if (id === null || id === undefined) return null;
    const normalized = String(id).trim();
    return normalized === '' ? null : normalized;
  }

  // Função para lidar com mudanças nos filtros
  function handleFilterChange() {
    const showAll = document.getElementById('filter-all');
    const taskFilters = Array.from(filtersContainer.querySelectorAll('input[type="checkbox"]:not(#filter-all)'));
    
    // Desmarcar "Show All" se algum filtro específico foi desmarcado
    const allTasksChecked = taskFilters.every(checkbox => checkbox.checked);
    if (showAll) {
      showAll.checked = allTasksChecked;
    }

    applyFilters();
  }

  // Função para lidar com "Show All"
  function handleShowAllChange() {
    const showAll = document.getElementById('filter-all');
    const taskFilters = filtersContainer.querySelectorAll('input[type="checkbox"]:not(#filter-all)');
    
    taskFilters.forEach(checkbox => {
      checkbox.checked = showAll.checked;
    });

    applyFilters();
  }

  // Função otimizada para aplicar filtros
  function applyFilters() {
    const showAllCheckbox = document.getElementById('filter-all');
    const taskFilters = Array.from(filtersContainer.querySelectorAll('input[type="checkbox"]:checked:not(#filter-all)'));
    
    // Se "Show All" está marcado ou nenhum filtro específico, mostrar tudo
    if (showAllCheckbox && showAllCheckbox.checked) {
      heatmapContainers.forEach(container => {
        container.classList.remove('filtered-out');
      });
      return;
    }

    // Coletar IDs das tarefas selecionadas (normalizados como strings)
    const checkedTaskIds = new Set();
    taskFilters.forEach(checkbox => {
      const id = normalizeTaskId(checkbox.id.replace('filter-task-', ''));
      if (id !== null) {
        checkedTaskIds.add(id);
      }
    });

    console.log('🔍 Filtros aplicados:', Array.from(checkedTaskIds));

    // Aplicar filtros aos containers
    heatmapContainers.forEach(container => {
      const taskIdsStr = container.dataset.taskIds || '';
      const containerTaskIds = taskIdsStr.split(',')
        .map(normalizeTaskId)
        .filter(id => id !== null);

      console.log(`📦 Container ${container.dataset.heatmapIndex}: tarefas [${containerTaskIds.join(', ')}]`);

      // Mostrar se:
      // 1. Nenhum filtro específico selecionado (mostrar tudo)
      // 2. Container tem pelo menos uma tarefa que coincide com filtros
      // 3. Container não tem tarefas e isso é explicitamente permitido
      const shouldShow = checkedTaskIds.size === 0 || 
                        containerTaskIds.some(id => checkedTaskIds.has(id));

      if (shouldShow) {
        container.classList.remove('filtered-out');
      } else {
        container.classList.add('filtered-out');
      }
    });

    // Atualizar contador de heatmaps visíveis
    const visibleCount = heatmapContainers.filter(c => !c.classList.contains('filtered-out')).length;
    console.log(`📊 ${visibleCount}/${heatmapContainers.length} heatmaps visíveis`);
  }
});
