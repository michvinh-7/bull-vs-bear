// Plain module (not "use client") so the server layout can inline the script text.
export const THEME_KEY = "bvb-theme";

/**
 * Runs before React loads (see app/layout.tsx) so the page never flashes the wrong theme.
 * A saved choice wins; otherwise follow the device setting.
 */
export const themeInitScript = `(function(){try{var t=localStorage.getItem("${THEME_KEY}");var d=t?t==="dark":matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d);document.documentElement.style.colorScheme=d?"dark":"light"}catch(e){document.documentElement.classList.add("dark")}})()`;
