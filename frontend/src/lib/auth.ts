import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "@/types";
import { authApi } from "./api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  setUser: (user: User | null) => void;
  fetchMe: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: false,

      setUser: (user) => set({ user }),

      fetchMe: async () => {
        set({ isLoading: true });
        try {
          const user = await authApi.me();
          set({ user });
        } catch {
          set({ user: null });
        } finally {
          set({ isLoading: false });
        }
      },

      logout: () => {
        authApi.logout();
        set({ user: null });
        window.location.href = "/auth/login";
      },
    }),
    {
      name: "auth-store",
      partialize: (s) => ({ user: s.user }),
    }
  )
);

export function useIsAdmin(): boolean {
  const user = useAuthStore((s) => s.user);
  return user?.role === "admin";
}
