import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authAPI } from '../api/missions' // Assuming missions.js export authAPI

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      isLoading: false,

      setToken: (token) => set({ token }),
      setUser: (user) => set({ user }),

      login: async (email, password) => {
        set({ isLoading: true })
        try {
          const { data } = await authAPI.login(email, password)
          set({ token: data.access_token, user: data.user, isLoading: false })
          return data
        } catch (error) {
          set({ isLoading: false })
          throw error
        }
      },

      logout: () => set({ token: null, user: null }),

      loadUser: async () => {
        if (!get().token) return
        try {
          const { data } = await authAPI.me()
          set({ user: data })
        } catch (error) {
          set({ token: null, user: null })
        }
      },
    }),
    { 
      name: 'levi-auth', 
      partialize: (s) => ({ token: s.token, user: s.user }) 
    }
  )
)
