document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.edit-form') || document.querySelector('.create-form')
  if (!form) return
  const button = form.querySelector('button[type="submit"], input[type="submit"]')

  let submitted = false

  // Apple-level Process Card Interactions
  const processCards = document.querySelectorAll('.process-card')
  processCards.forEach(card => {
    const checkbox = card.querySelector('.process-checkbox')
    
    // Skip disabled cards
    if (card.classList.contains('disabled') || checkbox.disabled) {
      return
    }
    
    // Handle card click
    card.addEventListener('click', (e) => {
      // Don't trigger if clicking the checkbox directly
      if (e.target === checkbox) return
      
      checkbox.checked = !checkbox.checked
      updateCardState(card, checkbox.checked)
    })
    
    // Handle checkbox change
    checkbox.addEventListener('change', (e) => {
      updateCardState(card, e.target.checked)
    })
    
    // Initialize card state
    updateCardState(card, checkbox.checked)
  })

  function updateCardState(card, isChecked) {
    if (isChecked) {
      card.classList.add('selected')
    } else {
      card.classList.remove('selected')
    }
  }

  // Apple-level URL Validation
  const urlInput = document.getElementById('seco_portal_url')
  if (urlInput) {
    // Only validate on blur, not on input to avoid premature errors
    urlInput.addEventListener('blur', validateURL)
    
    // Don't initialize validation on page load
  }

  function validateURL() {
    const url = urlInput.value.trim()
    const isValid = isValidURL(url)
    
    // Only show error if user has actually entered something and it's invalid
    if (url.length > 0 && !isValid) {
      urlInput.setAttribute('data-invalid', 'true')
    } else {
      urlInput.removeAttribute('data-invalid')
    }
  }

  function isValidURL(string) {
    if (!string) return true // Empty is valid (required will handle it)
    
    // More flexible URL pattern - accepts various formats
    const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/
    return urlPattern.test(string)
  }

  form.addEventListener('submit', e => {
    // ✅ Validate URL format
    const urlInput = document.getElementById('seco_portal_url')
    if (urlInput && urlInput.value.trim()) {
      const isValid = isValidURL(urlInput.value.trim())
      if (!isValid) {
        e.preventDefault()
        urlInput.setAttribute('data-invalid', 'true')
        urlInput.focus()
        return
      }
    }

    // ✅ Require at least one SECO process checkbox selected
    const anyChecked = !!form.querySelector('input[name="seco_process_ids"]:checked')
    if (!anyChecked) {
      e.preventDefault()
      // Show inline error message instead of just alert
      let errorEl = document.getElementById('process-error')
      if (errorEl) {
        errorEl.textContent = 'Please select at least one process'
        errorEl.classList.remove('d-none')
        form.querySelector('.processes-grid')?.classList.add('has-error')
      } else {
        alert('Please select at least one process')
      }
      return
    }

    // ✅ Prevent double submission
    if (submitted) {
      e.preventDefault()
      return
    }
    submitted = true
    if (button) {
      button.disabled = true
      const spinner = button.querySelector('.spinner')
      if (spinner) {
        spinner.classList.remove('d-none')
      }
      button.innerHTML = '<span class="btn-icon">⏳</span><span>Creating...</span>'
    }
  })
})

// ===============================
// 🎯 Dynamic KSC Distribution via JSON
// ===============================

document.addEventListener('DOMContentLoaded', () => {
  const kscContainer = document.getElementById('ksc-container')
  if (!kscContainer) return;

  const processCheckboxes = document.querySelectorAll('.process-checkbox')

  // Atualiza a seção toda vez que mudar seleção de processos
  processCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      updateKSCSection();
    });
  });

  async function updateKSCSection() {
    kscContainer.innerHTML = '<p class=form-help>Loading KSC data...</p>';

    // Coleta IDs selecionados
    const selected = Array.from(processCheckboxes)
    .filter(cb => cb.checked)
    .map(cb => cb.value);

    if (selected.length === 0) {
      kscContainer.innerHTML = '<p class="form-help">Select procedures above to assign KSC importance points (total of 10 per procedure).</p>';
      return;
    }

    try {
      // Faz a requisição para o Flask
      const response = await fetch(`/api/get_pksc?ids=${selected.join(',')}`);
      const kscData = await response.json();

      kscContainer.innerHTML = ''; // limpa ants de recriar

      Object.entries(kscData).forEach(([pid, info]) => {
        const {process_description, ksc_list} = info;

        // Cria container principal do processo
        const group = document.createElement('div');
        group.className = 'ksc-group';
        group.dataset.pid = pid;

        // Cabeçalho
        const header = document.createElement('div');
        header.className = 'ksc-header';
        header.innerHTML = `
          <strong>Procedure: P${pid}</strong> - ${process_description}<br>
          <span class="form-help">Distribute a total of <strong>10 points</strong> among the KSCs below based on their importance.</span>
        `;
        group.appendChild(header);

        // Container dos KSCs
        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'ksc-items';

        ksc_list.forEach((ksc, i) => {
          const item = document.createElement('div');
          item.className = 'ksc-item';
          item.innerHTML = `
            <div class="ksc-info">
              <span class="ksc-title"><strong>${ksc.title}</strong></span>
              <p class="ksc-description">${ksc.description}</p>
            </div>
            <input type="number" min="0" max="10" value="0"
                    class="ksc-input"
                    name="ksc_points_${pid}_${ksc.id}">
          `;
          itemsContainer.appendChild(item);
        });

        group.appendChild(itemsContainer);

        // Aviso de validação
        const warning = document.createElement('div');
        warning.className = 'ksc-warning';
        warning.textContent = '';
        group.appendChild(warning);

        // Validação de soma total por processo
        group.addEventListener('input', () => {
          const inputs = group.querySelectorAll('.ksc-input');
          const sum = Array.from(inputs).reduce((a, b) => a + Number(b.value || 0), 0);
          if (sum > 10) {
            warning.textContent = `⚠️ You distributed ${sum} points. Maximum is 10.`;
            warning.style.color = 'var(--danger)'
          } else if (sum < 10) {
            warning.textContent = `⚠️ You distributed only ${sum} points. Please allocate a total of 10 points.`;
            warning.style.color = 'var(--warning)'
          } else {
            warning.textContent = '✅ Perfect distribution of 10 points!';
            warning.style.color = 'var(--success)'
          }
        });

        kscContainer.appendChild(group);
      });

    } catch (err) {
      console.error('Error fetching KSC data:', err);
      kscContainer.innerHTML = '<p class="form-help" style="color: var(--danger);">Error loading KSC data. Please try again later.</p>';
    }
  }
});