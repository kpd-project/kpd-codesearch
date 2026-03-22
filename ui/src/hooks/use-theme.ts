import { useEffect, useMemo, useState } from "react";

type ThemeMode = "auto" | "light" | "dark";

const STORAGE_KEY = "theme";

function getInitialMode(): ThemeMode {
  // SSR/не-бродузерных окружениях работаем в "auto".
  if (typeof window === "undefined") return "auto";

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "auto" || stored === "light" || stored === "dark") return stored;

  return "auto";
}

function getSystemPrefersDark() {
  return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false;
}

function applyResolvedTheme(resolvedMode: Exclude<ThemeMode, "auto">) {
  const root = document.documentElement;
  root.classList.toggle("dark", resolvedMode === "dark");
  // Подсказка браузеру для нативных элементов (адресная панель, формы и т.п.).
  root.style.colorScheme = resolvedMode;
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => getInitialMode());
  const [systemDark, setSystemDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return getSystemPrefersDark();
  });

  // Применяем текущую "разрешенную" (resolved) тему.
  const resolvedTheme = useMemo(() => {
    if (mode === "auto") return systemDark ? "dark" : "light";
    return mode;
  }, [mode, systemDark]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    applyResolvedTheme(resolvedTheme);
  }, [resolvedTheme]);

  // В режиме AUTO реагируем на изменения системной темы.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (mode !== "auto") return;

    const mql = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!mql) return;

    const handler = () => {
      setSystemDark(getSystemPrefersDark());
    };

    // Safari/старые браузеры: addListener/removeListener.
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", handler);
      return () => mql.removeEventListener("change", handler);
    }

    // eslint-disable-next-line deprecation/deprecation
    mql.addListener(handler);
    // eslint-disable-next-line deprecation/deprecation
    return () => mql.removeListener(handler);
  }, [mode]);

  // Пишем в localStorage только когда пользователь меняет режим.
  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);

  const api = useMemo(
    () => ({
      themeMode: mode,
      theme: resolvedTheme,
      isDark: resolvedTheme === "dark",
      toggleTheme: () => {
        if (mode === "auto") {
          // Делаем явный выбор в противоположность текущей resolved-теме.
          setMode(systemDark ? "light" : "dark");
          return;
        }
        setMode((m) => (m === "dark" ? "light" : "dark"));
      },
      setThemeMode: (next: ThemeMode) => setMode(next),
    }),
    [mode, resolvedTheme],
  );

  return api;
}

