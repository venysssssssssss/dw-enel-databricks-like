import { create } from "zustand";

type Theme = "light" | "dark";

type UiState = {
  sidebarOpen: boolean;
  theme: Theme;
  toggleSidebar: () => void;
  setSidebar: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
};

const initialTheme = (): Theme => {
  const params = new URLSearchParams(window.location.search);
  const theme = params.get("theme");
  if (theme === "dark" || theme === "light") {
    return theme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
};

const initialSidebarOpen = (): boolean => {
  if (typeof window === "undefined") return true;
  // Closed by default on mobile (≤960px); open on desktop.
  return window.matchMedia("(min-width: 961px)").matches;
};

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: initialSidebarOpen(),
  theme: initialTheme(),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebar: (open) => set({ sidebarOpen: open }),
  setTheme: (theme) => set({ theme })
}));
