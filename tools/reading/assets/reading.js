(() => {
  const root = document.documentElement;
  const button = document.querySelector(".theme-toggle");
  const storageKey = "openharmony-reading-theme";
  const systemPreference = window.matchMedia("(prefers-color-scheme: dark)");

  root.classList.add("js-enabled");

  function storedTheme() {
    try {
      const value = window.localStorage.getItem(storageKey);
      return value === "light" || value === "dark" ? value : null;
    } catch {
      return null;
    }
  }

  function setTheme(theme, persist) {
    root.dataset.theme = theme;
    if (button) {
      button.setAttribute("aria-pressed", String(theme === "dark"));
      button.querySelector(".theme-label").textContent =
        theme === "dark" ? "切换浅色" : "切换深色";
    }
    if (persist) {
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch {
        // Theme switching remains available when browser storage is disabled.
      }
    }
  }

  const savedTheme = storedTheme();
  if (savedTheme) {
    setTheme(savedTheme, false);
  } else {
    root.dataset.theme = systemPreference.matches ? "dark" : "light";
    if (button) {
      button.setAttribute("aria-pressed", String(systemPreference.matches));
      button.querySelector(".theme-label").textContent =
        systemPreference.matches ? "切换浅色" : "切换深色";
    }
  }

  if (button) {
    button.addEventListener("click", () => {
      const currentTheme = root.dataset.theme || (systemPreference.matches ? "dark" : "light");
      setTheme(currentTheme === "dark" ? "light" : "dark", true);
    });
  }
})();
