/**
 * ITRACK Theme Manager
 * Handles light/dark mode toggle with localStorage persistence
 */

(function () {
    const THEME_KEY = 'itrack-theme';

    // Get saved theme or default to 'light'
    function getSavedTheme() {
        return localStorage.getItem(THEME_KEY) || 'light';
    }

    // Save theme to localStorage
    function saveTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    // Apply theme to document
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateToggleIcon(theme);
    }

    // Update toggle button icon
    function updateToggleIcon(theme) {
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            const icon = toggleBtn.querySelector('i');
            if (icon) {
                icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
            }
            toggleBtn.title = theme === 'dark' ? 'เปลี่ยนเป็นโหมดสว่าง' : 'เปลี่ยนเป็นโหมดมืด';
        }
    }

    // Toggle theme
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
        saveTheme(newTheme);
    }

    // Initialize theme on page load
    function initTheme() {
        const savedTheme = getSavedTheme();
        applyTheme(savedTheme);

        // Attach click handler to toggle button
        const toggleBtn = document.getElementById('theme-toggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
    }

    // Apply theme immediately (before DOM ready) to prevent flash
    const savedTheme = getSavedTheme();
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }

    // Expose toggle function globally
    window.toggleTheme = toggleTheme;
})();
