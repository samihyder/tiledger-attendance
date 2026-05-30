// Global JS — auto-dismiss alerts, tooltips
document.addEventListener('DOMContentLoaded', () => {
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
