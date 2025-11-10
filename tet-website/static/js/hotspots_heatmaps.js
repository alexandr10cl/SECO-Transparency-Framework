document.addEventListener('DOMContentLoaded', () => {
  const evaluationIdElement = document.getElementById('id-avaliacao');
  if (!evaluationIdElement) {
    console.warn('Evaluation id element not found. Heatmaps will not be loaded.');
    return;
  }

  const evaluationId = evaluationIdElement.textContent.trim();
  const root = document.getElementById('heatmaps-root');
  const filtersContainer = document.getElementById('task-filters');

  if (!root || !filtersContainer) {
    console.warn('Heatmap root or filters container not found.');
    return;
  }

  let availableScenarios = [];
  let heatmapCards = [];
  let scenarioMappingAvailable = true;

  root.innerHTML = '<p class="loading">Loading heatmaps...</p>';

  fetch(`/api/heatmap-scenarios/${evaluationId}`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Network error: ${response.status} ${response.statusText}`);
      }
      return response.json();
    })
    .then(data => {
      root.innerHTML = '';

      const heatmapsByUrl = data.heatmaps_by_url || [];
      availableScenarios = data.available_scenarios || [];
      const metadata = data.metadata || {};

      scenarioMappingAvailable = metadata.scenario_mapping_available !== false;

      if (metadata) {
        displayDataQualityInfo(metadata);
      }

      setupScenarioFilters(availableScenarios, metadata);

      if (!heatmapsByUrl.length) {
        const emptyState = document.createElement('p');
        emptyState.textContent = 'No heatmaps were generated for this evaluation yet.';
        root.appendChild(emptyState);
        return;
      }

      heatmapsByUrl.forEach((urlData, index) => {
        const section = createHeatmapCard(urlData, index);
        root.appendChild(section.card);
        heatmapCards.push(section.card);

        const heatmapPayload = {
          image: urlData.image,
          mime: urlData.mime || 'image/jpeg',
          width: urlData.width,
          height: urlData.height,
          points: urlData.aggregated_points || urlData.points || [],
          title: urlData.title || urlData.url || `Heatmap ${index + 1}`
        };

        initializeHeatmap(section.heatmapContainer, heatmapPayload, index);
      });

      applyFilters();
    })
    .catch(error => {
      console.error('Error loading scenario heatmaps:', error);
      
      // Create a more user-friendly error display
      const errorContainer = document.createElement('div');
      errorContainer.className = 'heatmap-error-container';
      errorContainer.innerHTML = `
        <div class="heatmap-error-card">
          <div class="error-icon">⚠️</div>
          <h3>Unable to Load Heatmaps</h3>
          <p class="error-message">${escapeHtml(error.message)}</p>
          <p class="error-hint">This may happen if:</p>
          <ul class="error-reasons">
            <li>The UX Tracking API is temporarily unavailable</li>
            <li>The heatmap data is very large and took too long to load</li>
            <li>Your network connection was interrupted</li>
          </ul>
          <button class="retry-button" onclick="location.reload()">
            🔄 Retry
          </button>
        </div>
      `;
      root.innerHTML = '';
      root.appendChild(errorContainer);
    });

  function setupScenarioFilters(scenarios, metadata = {}) {
    filtersContainer.innerHTML = '';

    const header = document.createElement('h3');
    header.textContent = 'Filter by Scenario';
    const list = document.createElement('div');
    list.className = 'task-filters-list';

    filtersContainer.appendChild(header);
    filtersContainer.appendChild(list);

    const mappingAvailable = scenarioMappingAvailable && Array.isArray(scenarios) && scenarios.length > 0;

    if (!mappingAvailable) {
      const disabledMessage = document.createElement('div');
      disabledMessage.className = 'filter-disabled-message';
      const reason = metadata.scenario_mapping_reason
        || 'Scenario filters are unavailable because navigation data could not be linked to specific scenarios.';
      disabledMessage.innerHTML = `<strong>Scenario filters unavailable.</strong><br>${escapeHtml(reason)}`;
      list.appendChild(disabledMessage);
      scenarioMappingAvailable = false;
      return;
    }

    const showAllItem = createFilterItem({
      id: 'filter-all-scenarios',
      label: 'Show All Scenarios',
      checked: true
    });
    list.appendChild(showAllItem.container);
    showAllItem.checkbox.addEventListener('change', handleShowAllChange);

    scenarios.forEach(scenario => {
      const normalizedId = normalizeScenarioId(scenario.task_id);
      if (normalizedId === null) {
        return;
      }

      const item = createFilterItem({
        id: `filter-scenario-${normalizedId}`,
        label: scenario.title || `Scenario ${normalizedId}`,
        checked: true,
        description: scenario.description || ''
      });

      item.checkbox.dataset.scenarioId = normalizedId;
      item.checkbox.addEventListener('change', handleFilterChange);
      list.appendChild(item.container);
    });
  }

  function createFilterItem({ id, label, checked = false, description = '' }) {
    const container = document.createElement('div');
    container.className = 'filter-item';

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.id = id;
    checkbox.checked = checked;

    const labelElement = document.createElement('label');
    labelElement.htmlFor = id;
    labelElement.textContent = label;

    if (description) {
      labelElement.title = description;
    }

    container.appendChild(checkbox);
    container.appendChild(labelElement);

    return { container, checkbox };
  }

  function createHeatmapCard(urlData, index) {
    const card = document.createElement('section');
    card.className = 'heatmap-card';

    const scenarioIds = (urlData.scenarios_involved || [])
      .map(scenario => normalizeScenarioId(scenario.task_id))
      .filter(id => id !== null);

    if (scenarioIds.length > 0) {
      card.dataset.scenarioIds = scenarioIds.join(',');
    }

    const header = document.createElement('div');
    header.className = 'url-section-header';

    const headerContent = document.createElement('div');
    headerContent.className = 'url-header-content';

    const titleElement = document.createElement('h3');
    titleElement.className = 'url-title';

    const iconSpan = document.createElement('span');
    iconSpan.className = 'url-icon';
    iconSpan.textContent = '🌐';

    const titleText = document.createElement('span');
    titleText.textContent = urlData.title || urlData.url || `Page ${index + 1}`;

    titleElement.appendChild(iconSpan);
    titleElement.appendChild(titleText);

    const addressElement = document.createElement('p');
    addressElement.className = 'url-address';
    addressElement.textContent = urlData.url || 'Unknown URL';

    headerContent.appendChild(titleElement);
    headerContent.appendChild(addressElement);

    const stats = document.createElement('div');
    stats.className = 'url-stats';

    stats.innerHTML = `
      <div class="stat-item">
        <span class="stat-value">${formatNumber(urlData.scenarios_count || 0)}</span>
        <span class="stat-label">Scenarios</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">${formatNumber(urlData.total_points || 0)}</span>
        <span class="stat-label">Interactions</span>
      </div>
      <div class="stat-item">
        <span class="stat-value">${formatNumber(urlData.total_navigation_hits || 0)}</span>
        <span class="stat-label">Navigation Hits</span>
      </div>
    `;

    header.appendChild(headerContent);
    header.appendChild(stats);
    card.appendChild(header);

    const tagContainer = createScenarioTags(urlData.scenarios_involved || []);
    if (tagContainer) {
      card.appendChild(tagContainer);
    } else if (!scenarioMappingAvailable) {
      const info = document.createElement('p');
      info.className = 'scenario-tags-info';
      info.textContent = 'Scenario attribution unavailable for this URL.';
      card.appendChild(info);
    }

    if (Array.isArray(urlData.sources) && urlData.sources.length > 1) {
      const sourceInfo = document.createElement('p');
      sourceInfo.className = 'heatmap-source-info';
      const totalSources = urlData.sources.length;
      const totalPoints = urlData.total_points || 0;
      sourceInfo.textContent = `${totalSources} heatmaps combined · ${formatNumber(totalPoints)} interaction points`;
      card.appendChild(sourceInfo);
    }

    const heatmapContainer = createHeatmapContainer(urlData);
    card.appendChild(heatmapContainer);

    return { card, heatmapContainer };
  }

  function createScenarioTags(scenarios) {
    if (!Array.isArray(scenarios) || scenarios.length === 0) {
      return null;
    }

    const container = document.createElement('div');
    container.className = 'scenario-tags';

    const label = document.createElement('span');
    label.className = 'tag-label';
    label.textContent = 'Scenarios:';
    container.appendChild(label);

    scenarios.forEach(scenario => {
      const normalizedId = normalizeScenarioId(scenario.task_id);
      const tag = document.createElement('span');
      tag.className = 'scenario-tag';
      tag.textContent = scenario.scenario_title || `Scenario ${normalizedId || ''}`;
      tag.title = `${formatNumber(scenario.navigation_hits || 0)} navigation hits`;
      if (normalizedId !== null) {
        tag.dataset.scenarioId = normalizedId;
      }
      container.appendChild(tag);
    });

    return container;
  }

  function createHeatmapContainer(heatmapData) {
    const container = document.createElement('div');
    container.className = 'heatmap-wrapper';

    Object.assign(container.style, {
      position: 'relative',
      maxWidth: '100%',
      marginTop: '16px',
      borderRadius: '16px',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(15, 23, 42, 0.15)',
      border: '1px solid rgba(148, 163, 184, 0.25)',
      background: 'linear-gradient(145deg, #ffffff 0%, #f8fafc 100%)',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      width: heatmapData.width ? `${heatmapData.width}px` : '720px',
      height: heatmapData.height ? `${heatmapData.height}px` : '405px'
    });

    container.addEventListener('mouseenter', () => {
      container.style.transform = 'translateY(-4px)';
      container.style.boxShadow = '0 16px 40px rgba(15, 23, 42, 0.18)';
    });

    container.addEventListener('mouseleave', () => {
      container.style.transform = 'translateY(0)';
      container.style.boxShadow = '0 8px 32px rgba(15, 23, 42, 0.15)';
    });

    return container;
  }

  function initializeHeatmap(container, heatmapData, index) {
    if (!heatmapData.image) {
      const fallback = document.createElement('p');
      fallback.textContent = `Heatmap image ${index + 1} is unavailable.`;
      fallback.className = 'heatmap-image-missing';
      container.appendChild(fallback);
      return;
    }

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
        container,
        radius: 40,
        maxOpacity: 0.6,
        blur: 0.9
      });

      const scaleX = container.clientWidth / sourceW;
      const scaleY = container.clientHeight / sourceH;

      const pts = (heatmapData.points || []).map(point => ({
        x: Math.round((point.x || 0) * scaleX),
        y: Math.round((point.y || 0) * scaleY),
        value: Math.max(1, Math.round((point.intensity || 0) * 700))
      }));

      const maxVal = pts.length ? Math.max(...pts.map(p => p.value)) : 100;

      try {
        heatmapInstance.setData({ max: Math.max(maxVal, 100), data: pts });
      } catch (err) {
        console.error('Error rendering heatmap', err);
        const errMsg = document.createElement('p');
        errMsg.textContent = `Error rendering heatmap ${index + 1}: ${err.message}`;
        errMsg.className = 'heatmap-error';
        container.appendChild(errMsg);
      }
    };

    if (img.decode) {
      img.decode().then(initHeatmap).catch(err => {
        console.warn('img.decode failed, falling back to onload', err);
        img.onload = initHeatmap;
        img.onerror = () => showImageError(container, index);
      });
    } else {
      img.onload = initHeatmap;
      img.onerror = () => showImageError(container, index);
    }
  }

  function showImageError(container, index) {
    console.error('Error loading heatmap image');
    container.innerHTML = '';
    const message = document.createElement('p');
    message.textContent = `Error loading heatmap image ${index + 1}.`;
    message.className = 'heatmap-error';
    container.appendChild(message);
  }

  function normalizeScenarioId(id) {
    if (id === null || id === undefined) return null;
    const normalized = String(id).trim();
    return normalized === '' ? null : normalized;
  }

  function handleFilterChange() {
    const showAllCheckbox = document.getElementById('filter-all-scenarios');
    if (showAllCheckbox) {
      const scenarioCheckboxes = Array.from(filtersContainer.querySelectorAll('input[type="checkbox"]:not(#filter-all-scenarios)'));
      showAllCheckbox.checked = scenarioCheckboxes.every(checkbox => checkbox.checked);
    }

    applyFilters();
  }

  function handleShowAllChange() {
    const showAllCheckbox = document.getElementById('filter-all-scenarios');
    const scenarioCheckboxes = filtersContainer.querySelectorAll('input[type="checkbox"]:not(#filter-all-scenarios)');

    scenarioCheckboxes.forEach(checkbox => {
      checkbox.checked = showAllCheckbox.checked;
    });

    applyFilters();
  }

  function applyFilters() {
    if (!scenarioMappingAvailable) {
      heatmapCards.forEach(card => card.classList.remove('filtered-out'));
      return;
    }

    const showAllCheckbox = document.getElementById('filter-all-scenarios');
    const activeScenarioCheckboxes = Array.from(filtersContainer.querySelectorAll('input[type="checkbox"]:checked:not(#filter-all-scenarios)'));

    if (!activeScenarioCheckboxes.length || (showAllCheckbox && showAllCheckbox.checked)) {
      heatmapCards.forEach(card => card.classList.remove('filtered-out'));
      return;
    }

    const selectedScenarioIds = new Set(
      activeScenarioCheckboxes
        .map(checkbox => checkbox.dataset.scenarioId || checkbox.id.replace('filter-scenario-', ''))
        .map(normalizeScenarioId)
        .filter(id => id !== null)
    );

    heatmapCards.forEach(card => {
      const datasetValue = card.dataset.scenarioIds || '';
      const cardScenarioIds = datasetValue
        .split(',')
        .map(normalizeScenarioId)
        .filter(id => id !== null);

      const hasScenario = cardScenarioIds.length > 0;
      const shouldShow = !selectedScenarioIds.size
        || (hasScenario && cardScenarioIds.some(id => selectedScenarioIds.has(id)));

      if (shouldShow) {
        card.classList.remove('filtered-out');
      } else {
        card.classList.add('filtered-out');
      }
    });
  }

  function displayDataQualityInfo(metadata) {
    const qualityContainer = document.createElement('div');
    qualityContainer.className = 'data-quality-info';

    const qualityScore = metadata.data_quality_score || 0;
    const warnings = metadata.data_quality_warnings || [];
    const fallbackUsed = metadata.fallback_used || false;
    const segmentationMethod = metadata.segmentation_method || 'unknown';
    const navigationCount = metadata.navigation_data_count || 0;

    let qualityClass = 'good';
    if (qualityScore < 50) qualityClass = 'poor';
    else if (qualityScore < 80) qualityClass = 'fair';

    let qualityText = '';
    if (fallbackUsed) {
      qualityText = '⚠️ Using fallback mode – navigation tracking was not available.';
    } else if (qualityScore >= 80) {
      qualityText = '✅ Good data quality – navigation tracking working properly.';
    } else if (qualityScore >= 50) {
      qualityText = '⚠️ Fair data quality – some navigation data is missing.';
    } else {
      qualityText = '❌ Poor data quality – navigation tracking issues detected.';
    }

    qualityContainer.innerHTML = `
      <div class="quality-header">
        <h4>📊 Data Quality Assessment</h4>
        <div class="quality-score ${qualityClass}">Score: ${qualityScore}/100</div>
      </div>
      <div class="quality-details">
        <p><strong>Status:</strong> ${qualityText}</p>
        <p><strong>Method:</strong> ${escapeHtml(segmentationMethod)}</p>
        <p><strong>Navigation Events:</strong> ${formatNumber(navigationCount)}</p>
        ${warnings.length ? `
          <div class="quality-warnings">
            <strong>⚠️ Warnings:</strong>
            <ul>${warnings.map(warning => `<li>${escapeHtml(warning)}</li>`).join('')}</ul>
          </div>
        ` : ''}
      </div>
    `;

    root.insertBefore(qualityContainer, root.firstChild);
  }

  function escapeHtml(value) {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function formatNumber(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return '0';
    }
    return Number(value).toLocaleString();
  }
});
