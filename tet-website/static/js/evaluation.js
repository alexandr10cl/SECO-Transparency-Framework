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
  // processCheckboxes.forEach(checkbox => {
  //   checkbox.addEventListener('change', () => {
  //     updateKSCSection();
  //   });
  // });

  // Multi-step behaviour: maintain groups and show one at a time
  const nextBtn = document.getElementById('next-btn')
  const prevBtn = document.getElementById('prev-btn')
  const submitBtn = document.getElementById('submit-btn')
  const kscStep = document.getElementById('ksc-step')
  const stepDetails = document.getElementById('step-details')
  const progressSteps = document.querySelectorAll('.form-progress-step')
  const progressCounter = document.getElementById('progress-counter')
  const nextBtnLabel = nextBtn?.querySelector('.btn-label')
  const prevBtnLabel = prevBtn?.querySelector('.btn-label')
  const submitBtnLabel = submitBtn?.querySelector('.btn-label')

  // NOTE: do not call updateKSCSection here; the main Next handler below
  // will call updateKSCSection() when advancing from the details step.

  const processMeta = buildProcessMeta()

  let currentStepIndex = -1 // -1 = details step, 0..n-1 = ksc groups
  let groupElements = []
  let kscTabsBar = null
  let kscGroupsWrapper = null

  function updateProgress(state = 'details', groupIndex = 0) {
    if (!progressSteps.length) return

    progressSteps.forEach(step => {
      step.classList.remove('active', 'completed')
    })

    if (state === 'details') {
      progressSteps[0].classList.add('active')
      if (progressSteps[1]) progressSteps[1].classList.remove('completed')
      if (progressCounter) progressCounter.textContent = 'Awaiting setup'
      if (nextBtnLabel) nextBtnLabel.textContent = 'Next'
      if (prevBtnLabel) prevBtnLabel.textContent = 'Back'
      return
    }

    if (state === 'ksc-empty') {
      progressSteps[0].classList.add('completed')
      if (progressSteps[1]) {
        progressSteps[1].classList.add('active', 'completed')
      }
      if (progressCounter) progressCounter.textContent = 'Ready to submit'
      if (nextBtnLabel) nextBtnLabel.textContent = 'Review'
      if (prevBtnLabel) prevBtnLabel.textContent = 'Back to Details'
      return
    }

    if (state === 'ksc') {
      progressSteps[0].classList.add('completed')
      if (progressSteps[1]) {
        progressSteps[1].classList.add('active')
        if (groupElements.length > 0 && groupIndex >= groupElements.length - 1) {
          progressSteps[1].classList.add('completed')
        }
      }

      if (progressCounter) {
        if (groupElements.length > 0) {
          if (groupIndex >= groupElements.length - 1) {
            progressCounter.textContent = 'Final review'
          } else {
            progressCounter.textContent = `Group ${groupIndex + 1} of ${groupElements.length}`
          }
        } else {
          progressCounter.textContent = 'Ready to submit'
        }
      }

      if (nextBtnLabel) {
        if (!groupElements.length || groupIndex >= groupElements.length - 1) {
          nextBtnLabel.textContent = 'Review'
        } else {
          nextBtnLabel.textContent = 'Next Group'
        }
      }

      if (prevBtnLabel) {
        prevBtnLabel.textContent = groupIndex <= 0 ? 'Back to Details' : 'Previous Group'
      }

      if (submitBtnLabel && groupElements.length > 0) {
        submitBtnLabel.textContent = 'Create Evaluation'
      }
    }
  }

  updateProgress('details')

  function buildProcessMeta() {
    const meta = new Map()
    processCheckboxes.forEach(cb => {
      const pid = cb.value
      const card = cb.closest('.process-card')
      if (!card) return
      const code = card.querySelector('.process-id')?.textContent?.trim() ?? `P${pid}`
      const description = card.querySelector('.process-description')?.textContent?.trim() ?? ''
      meta.set(String(pid), { code, description })
    })
    return meta
  }

  function getProcessLabel(pid, fallbackDescription) {
    const meta = processMeta.get(String(pid))
    if (meta) {
      if (meta.code && meta.description) return `${meta.code} — ${meta.description}`
      return meta.code || meta.description || fallbackDescription || `Procedure P${pid}`
    }
    if (fallbackDescription) return fallbackDescription
    if (pid) return `Procedure P${pid}`
    return 'Selected Procedure'
  }

  function normalizeKscResponse(raw) {
    if (!raw) return []

    const groups = []
    if (Array.isArray(raw)) {
      const byPid = new Map()

      raw.forEach((item, index) => {
        if (!item) return
        const pid = item.process_id != null
          ? String(item.process_id)
          : item.task_id != null
            ? String(item.task_id)
            : `group-${index}`

        const processLabel = getProcessLabel(pid, item.process_description || item.task_title)
        const group = byPid.get(pid) || {
          pid,
          processDescription: processLabel,
          kscList: [],
          taskId: item.task_id ?? null,
          taskTitle: item.task_title ?? null,
          taskSummary: item.task_summary ?? null
        }

        group.kscList.push({
          id: item.ksc_id ?? item.id ?? `ksc-${index}`,
          title: item.ksc_title ?? item.title ?? 'Key Success Criterion',
          description: item.ksc_description ?? item.description ?? ''
        })

        if (!group.taskTitle && item.task_title) group.taskTitle = item.task_title
        if (!group.taskSummary && item.task_summary) group.taskSummary = item.task_summary
        if (!group.taskId && item.task_id) group.taskId = item.task_id

        byPid.set(pid, group)
      })

      return Array.from(byPid.values())
    }

    if (typeof raw === 'object') {
      return Object.entries(raw).map(([pid, info], index) => {
        const kscList = Array.isArray(info?.ksc_list) ? info.ksc_list : []
        return {
          pid,
          processDescription: getProcessLabel(pid, info?.process_description),
          kscList: kscList.map(ksc => ({
            id: ksc.id ?? ksc.ksc_id ?? `ksc-${index}`,
            title: ksc.title ?? ksc.ksc_title ?? 'Key Success Criterion',
            description: ksc.description ?? ksc.ksc_description ?? ''
          })),
          taskId: info?.task_id ?? null,
          taskTitle: info?.task_title ?? null,
          taskSummary: info?.task_summary ?? null
        }
      })
    }

    return []
  }

  function clearKscStructure() {
    if (kscTabsBar) {
      kscTabsBar.remove()
      kscTabsBar = null
    }
    if (kscGroupsWrapper) {
      kscGroupsWrapper.remove()
      kscGroupsWrapper = null
    }
    kscContainer.innerHTML = ''
    groupElements = []
  }

  function renderKscTabs(groups) {
    if (!groups.length) {
      clearKscStructure()
      kscContainer.innerHTML = '<p class="form-help">No key success criteria were found for the selected procedures.</p>'
      return
    }

    kscTabsBar = document.createElement('div')
    kscTabsBar.className = 'ksc-tabs'

    groups.forEach((group, index) => {
      const tab = document.createElement('button')
      tab.type = 'button'
      tab.className = 'ksc-tab'
      tab.dataset.index = index
      tab.innerHTML = `
        <span class="tab-indicator">${index + 1}</span>
        <span class="tab-content">
          <span class="tab-title">${group.processDescription}</span>
          ${group.taskTitle ? `<span class="tab-subtitle">${group.taskTitle}</span>` : ''}
        </span>
      `
      tab.addEventListener('click', () => {
        if (index === currentStepIndex) return
        if (currentStepIndex >= 0 && !validateCurrentGroup(currentStepIndex)) return
        currentStepIndex = index
        showGroup(index, true)
      })
      kscTabsBar.appendChild(tab)
    })

    kscContainer.appendChild(kscTabsBar)

    kscGroupsWrapper = document.createElement('div')
    kscGroupsWrapper.className = 'ksc-groups-wrapper'
    kscContainer.appendChild(kscGroupsWrapper)
  }

  function setActiveTab(index) {
    if (!kscTabsBar) return
    const tabs = kscTabsBar.querySelectorAll('.ksc-tab')
    tabs.forEach((tab, i) => {
      tab.classList.toggle('active', i === index)
    })
  }

  function isValidURL(string) {
    if (!string) return true
    const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/
    return urlPattern.test(string)
  }

  async function updateKSCSection() {
    kscContainer.innerHTML = '<p class=form-help>Loading KSC data...</p>';

    // Coleta IDs selecionados
    const selected = Array.from(processCheckboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value);

    if (selected.length === 0) {
      kscContainer.innerHTML = '<p class="form-help">Select procedures above to assign KSC importance points (total of 10 per procedure).</p>';
      groupElements = []
      updateProgress('details')
      return;
    }

    document.querySelector('.processes-grid')?.classList.remove('has-error')
    document.getElementById('process-error')?.classList.add('d-none')

    try {
      const response = await fetch(`/api/get_pksc?ids=${selected.join(',')}`);
      const kscData = await response.json();
      const normalizedGroups = normalizeKscResponse(kscData);

      clearKscStructure()

      if (!normalizedGroups.length) {
        kscContainer.innerHTML = '<p class="form-help">No key success criteria were found for the selected procedures.</p>'
        updateProgress('ksc-empty')
        currentStepIndex = -1
        return
      }

      renderKscTabs(normalizedGroups)
      currentStepIndex = -1

      normalizedGroups.forEach((groupData, idx) => {
        const { pid, processDescription, kscList, taskTitle, taskSummary } = groupData

        const group = document.createElement('div');
        group.className = 'ksc-group';
        group.dataset.pid = pid;
        group.dataset.index = idx;
        if (groupData.taskId) group.dataset.taskId = groupData.taskId;
        group.style.display = 'none'

        const header = document.createElement('div');
        header.className = 'ksc-header';
        const taskDetails = taskTitle
          ? `<br><small class="ksc-task">Scenario: <strong>${taskTitle}</strong>${taskSummary ? ` — ${taskSummary}` : ''}</small>`
          : '';
        header.innerHTML = `
          <strong>${processDescription}</strong>
          <span class="form-help">Distribute a total of <strong>10 points</strong> among the KSCs below based on their importance.</span>
          ${taskDetails}
        `;
        group.appendChild(header);

        const itemsContainer = document.createElement('div');
        itemsContainer.className = 'ksc-items';

        kscList.forEach((ksc, i) => {
          const item = document.createElement('div');
          item.className = 'ksc-item';
          item.innerHTML = `
            <div class="ksc-info">
              <span class="ksc-title"><strong>${ksc.title}</strong></span>
              <p class="ksc-description">${ksc.description}</p>
            </div>
            <input type="number" min="0" max="10" value="" placeholder="0-10" step="1"
                    class="ksc-input"
                    name="ksc_points_${pid}_${ksc.id}">
          `;
          
          itemsContainer.appendChild(item);
          
          const kscInput = item.querySelector('.ksc-input');
          
          // Real-time validation: prevent values < 0 or > 10
          kscInput.addEventListener('input', (e) => {
            let value = parseInt(e.target.value);
            
            // Clamp value between 0 and 10
            if (e.target.value !== '' && !isNaN(value)) {
              if (value < 0) {
                e.target.value = 0;
              } else if (value > 10) {
                e.target.value = 10;
              }
            }
            
            // Visual feedback for invalid input
            const currentValue = parseInt(e.target.value) || 0;
            if (currentValue < 0 || currentValue > 10) {
              e.target.classList.add('input-error');
            } else {
              e.target.classList.remove('input-error');
            }
          });
          
          // Prevent typing negative sign or decimals
          kscInput.addEventListener('keydown', (e) => {
            if (e.key === '-' || e.key === '.' || e.key === ',') {
              e.preventDefault();
            }
          });
        });

        group.appendChild(itemsContainer);

        const warning = document.createElement('div');
        warning.className = 'ksc-warning';
        warning.textContent = '';
        group.appendChild(warning);

        // live validation for UX
        group.addEventListener('input', () => {
          const inputs = group.querySelectorAll('.ksc-input');
          const sum = Array.from(inputs).reduce((a, b) => a + Number(b.value || 0), 0);
          // normalize classes
          warning.classList.remove('ok', 'warn', 'err')
          if (sum > 10) {
            warning.textContent = `⚠️ You distributed ${sum} points. Maximum is 10.`;
            warning.classList.add('err')
          } else if (sum < 10) {
            warning.textContent = `⚠️ You distributed only ${sum} points. Please allocate a total of 10 points.`;
            warning.classList.add('warn')
          } else {
            warning.textContent = '✅ Perfect distribution of 10 points!';
            warning.classList.add('ok')
          }
        });

        kscGroupsWrapper.appendChild(group);
        groupElements.push(group);
      });

      if (groupElements.length === 0) {
        updateProgress('ksc-empty')
      }

    } catch (err) {
      console.error('Error fetching KSC data:', err);
      kscContainer.innerHTML = '<p class="form-help" style="color: var(--danger);">Error loading KSC data. Please try again later.</p>';
      groupElements = []
      updateProgress('details')
    }
  }

  function showGroup(index, fromTab = false) {
    // Hide non-active groups with a smooth transition
    groupElements.forEach((g, i) => {
      if (i === index) {
        // ensure visible then add class to trigger transition
        g.style.display = ''
        requestAnimationFrame(() => {
          g.classList.add('ksc-visible')
        })
      } else {
        // remove visible class to animate out, then hide after transition
        if (g.classList.contains('ksc-visible')) g.classList.remove('ksc-visible')
        // schedule hide after transition (260ms) if still hidden
        setTimeout(() => {
          if (!g.classList.contains('ksc-visible')) g.style.display = 'none'
        }, 300)
      }
    })

    // show ksc step container
    kscStep.style.display = ''
    // prev visible if not first
    prevBtn.classList.toggle('d-none', index <= 0)
    // if last group, hide next and show submit
    if (index >= groupElements.length - 1) {
      nextBtn.classList.add('d-none')
      submitBtn.classList.remove('d-none')
    } else {
      nextBtn.classList.remove('d-none')
      submitBtn.classList.add('d-none')
    }

    updateProgress('ksc', index)
    setActiveTab(index)

    if (!fromTab) {
      const activeTab = kscTabsBar?.querySelector('.ksc-tab.active')
      activeTab?.scrollIntoView({ block: 'nearest', behavior: 'smooth', inline: 'center' })
    }
  }

  function validateCurrentGroup(index) {
    const group = groupElements[index]
    if (!group) return true
    const inputs = group.querySelectorAll('.ksc-input')
    const warning = group.querySelector('.ksc-warning')
    
    // Check for empty inputs
    const hasEmptyInputs = Array.from(inputs).some(input => input.value === '')
    if (hasEmptyInputs) {
      warning.textContent = '⚠️ Please fill in all KSC weight fields (use 0 if not applicable)'
      warning.classList.remove('ok','warn')
      warning.classList.add('err')
      
      // Highlight empty inputs
      inputs.forEach(input => {
        if (input.value === '') {
          input.classList.add('input-error')
        } else {
          input.classList.remove('input-error')
        }
      })
      return false
    }
    
    // Remove error highlighting if all filled
    inputs.forEach(input => input.classList.remove('input-error'))
    
    const sum = Array.from(inputs).reduce((a, b) => a + Number(b.value || 0), 0)
    if (sum !== 10) {
      warning.textContent = `⚠️ You distributed ${sum} points. Please allocate exactly 10 points.`
      warning.classList.remove('ok','warn')
      warning.classList.add('err')
      return false
    }
    warning.textContent = '✅ Perfect distribution of 10 points!'
    warning.classList.remove('err','warn')
    warning.classList.add('ok')
    return true
  }

  // We intentionally do NOT auto-fetch KSC data on checkbox change.
  // The data is fetched only when the user clicks Next from the details step.

  // Next/back control flow
  nextBtn?.addEventListener('click', async () => {
    // If we are on details step, validate and build groups
    if (currentStepIndex === -1) {
      // Validate SECO Type is selected
      const secoTypeSelect = document.getElementById('seco_type')
      if (secoTypeSelect && !secoTypeSelect.value) {
        secoTypeSelect.classList.add('input-error')
        secoTypeSelect.focus()
        
        // Show error message
        let errorEl = secoTypeSelect.parentElement.querySelector('.field-error')
        if (!errorEl) {
          errorEl = document.createElement('div')
          errorEl.className = 'field-error'
          errorEl.style.color = '#e74c3c'
          errorEl.style.fontSize = '0.875rem'
          errorEl.style.marginTop = '0.5rem'
          secoTypeSelect.parentElement.appendChild(errorEl)
        }
        errorEl.textContent = 'Please select a SECO Type before continuing'
        return
      }
      secoTypeSelect.classList.remove('input-error')
      
      // Remove error message if exists
      const existingError = secoTypeSelect.parentElement.querySelector('.field-error')
      if (existingError) existingError.remove()
      
      // Validate URL
      const urlInput = document.getElementById('seco_portal_url')
      if (urlInput && urlInput.value.trim()) {
        if (!isValidURL(urlInput.value.trim())) {
          urlInput.setAttribute('data-invalid', 'true')
          urlInput.focus()
          return
        }
      }

      // require at least one process
      const anyChecked = !!document.querySelector('input[name="seco_process_ids"]:checked')
      if (!anyChecked) {
        const errorEl = document.getElementById('process-error')
        if (errorEl) {
          errorEl.textContent = 'Please select at least one process'
          errorEl.classList.remove('d-none')
          document.querySelector('.processes-grid')?.classList.add('has-error')
        }
        return
      }

      // Build groups and start at first
      await updateKSCSection()
      if (groupElements.length === 0) {
        // no groups; nothing to step through: reveal submit
        stepDetails.style.display = 'none'
        kscStep.style.display = ''
        nextBtn.classList.add('d-none')
        prevBtn.classList.remove('d-none')
        submitBtn.classList.remove('d-none')
        currentStepIndex = -1
        updateProgress('ksc-empty')
        return
      }
      // move to first group
      stepDetails.style.display = 'none'
      currentStepIndex = 0
      showGroup(0)
      return
    }

    // otherwise we are inside groups: validate current and advance
    if (!validateCurrentGroup(currentStepIndex)) return
    if (currentStepIndex < groupElements.length - 1) {
      currentStepIndex += 1
      showGroup(currentStepIndex)
    }
  })

  prevBtn?.addEventListener('click', () => {
    if (currentStepIndex <= 0) {
      // go back to details
      stepDetails.style.display = ''
      kscStep.style.display = 'none'
      prevBtn.classList.add('d-none')
      submitBtn.classList.add('d-none')
      nextBtn.classList.remove('d-none')
      currentStepIndex = -1
      updateProgress('details')
      setActiveTab(-1)
      return
    }
    currentStepIndex -= 1
    showGroup(currentStepIndex)
  })

  // Before final submit ensure last group valid
  submitBtn?.addEventListener('click', (e) => {
    if (groupElements.length > 0) {
      const idx = groupElements.length - 1
      if (!validateCurrentGroup(idx)) {
        e.preventDefault()
        return
      }
      updateProgress('ksc', idx)
    }
    // allow normal submit (existing form submit handler will also run)
  })
});