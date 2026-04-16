import { create } from "zustand";

type Theme = "light" | "dark";

type UiState = {
  sidebarOpen: boolean;
  theme: Theme;
  toggleSidebar: () => void;
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

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  theme: initialTheme(),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setTheme: (theme) => set({ theme })
}));
