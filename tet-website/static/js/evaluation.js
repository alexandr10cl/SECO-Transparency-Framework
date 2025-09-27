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
