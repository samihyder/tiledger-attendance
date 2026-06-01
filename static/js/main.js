// Global JS — auto-dismiss alerts, tooltips
document.addEventListener('DOMContentLoaded', () => {
  // ── Logout modal ──────────────────────────────────────────────────────────
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    const locked     = logoutBtn.dataset.locked === 'true';
    const logoutUrl  = logoutBtn.dataset.logoutUrl;
    const verifyUrl  = logoutBtn.dataset.verifyUrl;
    const modal      = new bootstrap.Modal(document.getElementById('logoutModal'));
    const lockedMsg  = document.getElementById('logoutLockedMsg');
    const freeMsg    = document.getElementById('logoutFreeMsg');
    const pwInput    = document.getElementById('logoutPassword');
    const pwError    = document.getElementById('logoutPasswordError');
    const confirmBtn = document.getElementById('logoutConfirmBtn');

    logoutBtn.addEventListener('click', () => {
      if (locked) {
        lockedMsg.classList.remove('d-none');
        freeMsg.classList.add('d-none');
        pwInput.value = '';
        pwError.classList.add('d-none');
      } else {
        lockedMsg.classList.add('d-none');
        freeMsg.classList.remove('d-none');
      }
      modal.show();
    });

    confirmBtn.addEventListener('click', async () => {
      if (!locked) { window.location.href = logoutUrl; return; }
      const password = pwInput.value;
      if (!password) { pwError.textContent = 'Password is required.'; pwError.classList.remove('d-none'); return; }
      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Checking…';
      try {
        const res = await fetch(verifyUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password }),
        });
        if (res.ok) {
          window.location.href = logoutUrl;
        } else {
          pwError.textContent = 'Incorrect password.';
          pwError.classList.remove('d-none');
          confirmBtn.disabled = false;
          confirmBtn.innerHTML = '<i class="bi bi-box-arrow-left me-1"></i>Logout';
        }
      } catch {
        pwError.textContent = 'Network error — try again.';
        pwError.classList.remove('d-none');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="bi bi-box-arrow-left me-1"></i>Logout';
      }
    });

    document.getElementById('logoutModal').addEventListener('shown.bs.modal', () => {
      if (locked) pwInput.focus();
    });
  }


  // Auto-dismiss success/info alerts after 4 seconds
  document.querySelectorAll('.alert-success, .alert-info').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      bsAlert?.close();
    }, 4000);
  });

  // Bootstrap tooltips
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
  });

  // Confirm dangerous form submissions
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
  });
});
