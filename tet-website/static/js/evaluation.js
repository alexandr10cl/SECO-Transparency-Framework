document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.evaluation-form')
  const button = document.getElementById('create-btn')
  if (!form || !button) return

  let submitted = false

  form.addEventListener('submit', e => {
    // ✅ Require at least one SECO process checkbox selected
    const anyChecked = !!form.querySelector('input[name="seco_process_ids"]:checked')
    if (!anyChecked) {
      e.preventDefault()
      // Show inline error message instead of just alert
      let errorEl = document.getElementById('process-error')
      if (errorEl) {
        errorEl.textContent = 'Please select at least one process'
        errorEl.classList.remove('d-none')
        form.querySelector('.checkbox-group')?.classList.add('has-error')
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
    button.disabled = true
    const spinner = button.querySelector('.spinner')
    if (spinner) spinner.classList.remove('d-none')
  })
})
