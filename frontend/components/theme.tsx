"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { THEME_KEY as KEY } from "@/lib/theme-script";

export type Theme = "light" | "dark";
const EVENT = "bvb-theme-change";

function apply(theme: Theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
  window.dispatchEvent(new Event(EVENT));
}

/** Current theme, kept in sync across every component that uses it. */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>("dark");

  useEffect(() => {
    const read = () => setThemeState(document.documentElement.classList.contains("dark") ? "dark" : "light");
    read();
    window.addEventListener(EVENT, read);

    // With no saved choice, keep following the device if it switches (e.g. at sunset).
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const follow = () => {
      try {
        if (!localStorage.getItem(KEY)) apply(mq.matches ? "dark" : "light");
      } catch {}
    };
    mq.addEventListener("change", follow);
    return () => {
      window.removeEventListener(EVENT, read);
      mq.removeEventListener("change", follow);
    };
  }, []);

  const setTheme = (t: Theme) => {
    try {
      localStorage.setItem(KEY, t);
    } catch {}
    apply(t);
  };
  return { theme, setTheme };
}

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <Button variant="ghost" size="icon" onClick={() => setTheme(next)} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`}>
      {theme === "dark" ? <Sun /> : <Moon />}
    </Button>
  );
}
