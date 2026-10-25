/**
 * Theme Switcher & Chart.js Theme Sync
 */
(function() {
  const THEME_KEY = 'pp_traffic_theme';
  
  function getPreferredTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
    const themeIcon = document.getElementById('theme-icon');
    const themeBtn = document.getElementById('theme-toggle-btn');
    
    if (themeIcon) {
      if (theme === 'dark') {
        themeIcon.className = 'bi bi-moon-stars-fill text-warning';
        if (themeBtn) themeBtn.setAttribute('title', 'Switch to Light Mode');
      } else {
        themeIcon.className = 'bi bi-sun-fill text-warning';
        if (themeBtn) themeBtn.setAttribute('title', 'Switch to Dark Mode');
      }
    }

    // Trigger custom event so any active Chart.js instances can re-render colors
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: theme } }));
  }

  // Initial theme on load
  const initialTheme = getPreferredTheme();
  applyTheme(initialTheme);

  document.addEventListener('DOMContentLoaded', function() {
    applyTheme(getPreferredTheme());

    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function() {
        const current = document.documentElement.getAttribute('data-bs-theme') || 'light';
        const next = current === 'dark' ? 'light' : 'dark';
        localStorage.setItem(THEME_KEY, next);
        applyTheme(next);
      });
    }
  });
})();

