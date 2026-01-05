/**
 * Professional Dark Mode Toggle
 * Handles theme switching with localStorage persistence and system preference detection
 * WCAG AA compliant with proper focus management and accessibility
 */

class DarkModeToggle {
  constructor(options = {}) {
    this.options = {
      themeAttribute: 'data-theme',
      storageKey: 'theme',
      defaultTheme: 'light',
      toggleSelector: '.theme-toggle-menu',
      animateTransitions: true,
      respectSystemPreference: true,
      ...options
    };

    this.currentTheme = this.getInitialTheme();
    this.toggleElement = null;
    this.isInitialized = false;

    this.init();
  }

  /**
   * Initialize the dark mode toggle
   */
  init() {
    if (this.isInitialized) return;

    // Set initial theme
    this.setTheme(this.currentTheme, false);

    // Create or find toggle button
    this.createToggleButton();

    // Bind events
    this.bindEvents();

    // Listen for system theme changes
    this.watchSystemPreference();

    this.isInitialized = true;

    // Dispatch custom event
    this.dispatchThemeChange();
  }

  /**
   * Get the initial theme from localStorage or system preference
   */
  getInitialTheme() {
    try {
      // Check localStorage first
      const stored = localStorage.getItem(this.options.storageKey);
      if (stored && ['light', 'dark'].includes(stored)) {
        return stored;
      }

      // Fall back to system preference
      if (this.options.respectSystemPreference && window.matchMedia) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        return prefersDark ? 'dark' : 'light';
      }

      return this.options.defaultTheme;
    } catch (error) {
      console.warn('Error accessing localStorage or system preferences:', error);
      return this.options.defaultTheme;
    }
  }

  /**
   * Create the theme toggle menu item in the hamburger menu
   */
  createToggleButton() {
    // Try to find existing toggle button
    this.toggleElement = document.querySelector(this.options.toggleSelector);

    if (!this.toggleElement) {
      // Create theme toggle menu item
      this.toggleElement = document.createElement('a');
      this.toggleElement.className = 'nav-link theme-toggle-menu';
      this.toggleElement.setAttribute('href', '#');
      this.toggleElement.setAttribute('role', 'button');
      this.toggleElement.setAttribute('aria-label', 'Toggle dark mode');
      this.toggleElement.setAttribute('title', 'Toggle dark mode');

      // Insert into navigation links (hamburger menu)
      const navLinks = document.querySelector('.nav-links');
      if (navLinks) {
        navLinks.appendChild(this.toggleElement);
      } else {
        // Fallback to body if nav not found
        document.body.appendChild(this.toggleElement);
      }
    }

    this.updateToggleIcon();
  }

  /**
   * Update the toggle menu item icon based on current theme
   */
  updateToggleIcon() {
    if (!this.toggleElement) return;

    const isDark = this.currentTheme === 'dark';
    const icon = isDark ? '☀️' : '🌙';
    const label = isDark ? 'Light Mode' : 'Dark Mode';

    this.toggleElement.innerHTML = `${icon} ${label}`;
    this.toggleElement.setAttribute('aria-label', label);
    this.toggleElement.setAttribute('title', label);
  }

  /**
   * Set the theme on the document
   */
  setTheme(theme, animate = true) {
    if (!['light', 'dark'].includes(theme)) {
      console.warn('Invalid theme:', theme);
      return;
    }

    // Prevent flash of unstyled content during transition
    if (animate && this.options.animateTransitions) {
      document.documentElement.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    }

    // Set theme attribute on html element
    document.documentElement.setAttribute(this.options.themeAttribute, theme);
    
    // Also add class for backward compatibility
    document.documentElement.classList.toggle('dark', theme === 'dark');
    document.body.classList.toggle('dark', theme === 'dark');

    this.currentTheme = theme;

    // Clear transition after animation completes
    if (animate && this.options.animateTransitions) {
      setTimeout(() => {
        document.documentElement.style.transition = '';
      }, 300);
    }

    // Update toggle button
    this.updateToggleIcon();

    // Save to localStorage
    this.saveTheme(theme);

    // Dispatch custom event
    this.dispatchThemeChange();
  }

  /**
   * Toggle between light and dark themes
   */
  toggle() {
    const newTheme = this.currentTheme === 'light' ? 'dark' : 'light';
    this.setTheme(newTheme);
    
    // Provide haptic feedback on mobile
    if ('vibrate' in navigator) {
      navigator.vibrate(50);
    }

    // Announce theme change to screen readers
    this.announceThemeChange(newTheme);
  }

  /**
   * Save theme preference to localStorage
   */
  saveTheme(theme) {
    try {
      localStorage.setItem(this.options.storageKey, theme);
    } catch (error) {
      console.warn('Error saving theme preference:', error);
    }
  }

  /**
   * Watch for system theme preference changes
   */
  watchSystemPreference() {
    if (!window.matchMedia || !this.options.respectSystemPreference) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      // Only change theme if no user preference is stored
      const stored = localStorage.getItem(this.options.storageKey);
      if (!stored) {
        const newTheme = e.matches ? 'dark' : 'light';
        this.setTheme(newTheme);
      }
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      // Legacy browsers
      mediaQuery.addListener(handleChange);
    }
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    if (this.toggleElement) {
      this.toggleElement.addEventListener('click', (e) => {
        e.preventDefault(); // Prevent default link behavior
        this.toggle();
      });
      
      // Keyboard support
      this.toggleElement.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.toggle();
        }
      });
    }

    // Global keyboard shortcut (Ctrl/Cmd + Shift + D)
    document.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  /**
   * Announce theme change to screen readers
   */
  announceThemeChange(theme) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.style.cssText = `
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    `;
    
    announcement.textContent = `Switched to ${theme} mode`;
    document.body.appendChild(announcement);

    // Remove after announcement
    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }

  /**
   * Dispatch custom theme change event
   */
  dispatchThemeChange() {
    const event = new CustomEvent('themeChange', {
      detail: {
        theme: this.currentTheme,
        isDark: this.currentTheme === 'dark',
        isLight: this.currentTheme === 'light'
      }
    });
    
    document.dispatchEvent(event);
  }

  /**
   * Get current theme
   */
  getTheme() {
    return this.currentTheme;
  }

  /**
   * Check if currently in dark mode
   */
  isDark() {
    return this.currentTheme === 'dark';
  }

  /**
   * Check if currently in light mode
   */
  isLight() {
    return this.currentTheme === 'light';
  }

  /**
   * Destroy the toggle instance
   */
  destroy() {
    if (this.toggleElement) {
      this.toggleElement.removeEventListener('click', this.toggle);
      this.toggleElement.removeEventListener('keydown', this.handleKeydown);
    }
    
    document.removeEventListener('keydown', this.handleGlobalKeydown);
    
    this.isInitialized = false;
  }
}

// Auto-initialize when DOM is ready
function initDarkMode() {
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      window.darkMode = new DarkModeToggle();
    });
  } else {
    window.darkMode = new DarkModeToggle();
  }
}

// Initialize immediately
initDarkMode();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = DarkModeToggle;
}

// Global exposure for script tag usage
window.DarkModeToggle = DarkModeToggle;

/**
 * Utility functions for theme management
 */
window.themeUtils = {
  /**
   * Get the current theme
   */
  getCurrentTheme() {
    return window.darkMode ? window.darkMode.getTheme() : 'light';
  },

  /**
   * Check if dark mode is active
   */
  isDarkMode() {
    return window.darkMode ? window.darkMode.isDark() : false;
  },

  /**
   * Toggle theme programmatically
   */
  toggleTheme() {
    if (window.darkMode) {
      window.darkMode.toggle();
    }
  },

  /**
   * Set theme programmatically
   */
  setTheme(theme) {
    if (window.darkMode) {
      window.darkMode.setTheme(theme);
    }
  },

  /**
   * Listen for theme changes
   */
  onThemeChange(callback) {
    document.addEventListener('themeChange', callback);
  }
};
