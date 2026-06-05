import axios, { AxiosInstance, AxiosError } from "axios";
import Cookies from "js-cookie";
import type {
  AuthTokens, User, CodingResponse, CodingSession, DashboardStats, FeedbackRequest,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Only set Secure flag when running on HTTPS (production).
// On HTTP localhost the Secure flag prevents cookies from being sent.
const IS_SECURE = typeof window !== "undefined" && window.location.protocol === "https:";

function createApiClient(): AxiosInstance {
  const client = axios.create({ baseURL: API_URL, timeout: 60000 });

  client.interceptors.request.use((config) => {
    const token = Cookies.get("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      const original = error.config as any;
      if (error.response?.status === 401 && !original._retry) {
        original._retry = true;
        const refreshToken = Cookies.get("refresh_token");
        if (refreshToken) {
          try {
            const { data } = await axios.post<AuthTokens>(
              `${API_URL}/auth/refresh`,
              { refresh_token: refreshToken }
            );
            Cookies.set("access_token", data.access_token, { secure: true, sameSite: "strict" });
            original.headers.Authorization = `Bearer ${data.access_token}`;
            return client(original);
          } catch {
            Cookies.remove("access_token");
            Cookies.remove("refresh_token");
            window.location.href = "/auth/login";
          }
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

const api = createApiClient();

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: { email: string; password: string; full_name: string; organization?: string }) =>
    api.post<User>("/auth/register", data).then((r) => r.data),

  login: (email: string, password: string) =>
    api.post<AuthTokens>("/auth/login", { email, password }).then((r) => {
      const { access_token, refresh_token, expires_in } = r.data;
      const expires = expires_in / 86400; // days
      Cookies.set("access_token", access_token, { secure: IS_SECURE, sameSite: "strict", expires });
      Cookies.set("refresh_token", refresh_token, { secure: IS_SECURE, sameSite: "strict", expires: 7 });
      return r.data;
    }),

  logout: () => {
    Cookies.remove("access_token");
    Cookies.remove("refresh_token");
  },

  me: () => api.get<User>("/auth/me").then((r) => r.data),

  updateProfile: (full_name: string, organization?: string) =>
    api.put<User>("/auth/me", { full_name, organization }).then((r) => r.data),

  changePassword: (current_password: string, new_password: string) =>
    api.put("/auth/change-password", { current_password, new_password }),

  forgotPassword: (email: string) =>
    api.post("/auth/forgot-password", { email }).then((r) => r.data),

  resetPassword: (token: string, new_password: string) =>
    api.post("/auth/reset-password", { token, new_password }).then((r) => r.data),

  requestEmailVerification: () =>
    api.post("/auth/verify-email/request").then((r) => r.data),

  verifyEmail: (token: string) =>
    api.post("/auth/verify-email", { token }).then((r) => r.data),
};

// ── Medical Coding ────────────────────────────────────────────────────────────
export const codingApi = {
  analyze: (clinical_text: string, top_k_codes = 5, include_explanation = true) =>
    api
      .post<CodingResponse>("/coding/analyze", { clinical_text, top_k_codes, include_explanation })
      .then((r) => r.data),

  getSessions: (page = 1, per_page = 20) =>
    api.get<{ sessions: CodingSession[]; total: number; page: number }>("/coding/sessions", {
      params: { page, per_page },
    }).then((r) => r.data),

  getSession: (id: string) =>
    api.get(`/coding/sessions/${id}`).then((r) => r.data),

  submitFeedback: (data: FeedbackRequest) =>
    api.post("/coding/feedback", data).then((r) => r.data),
};

// ── Admin ─────────────────────────────────────────────────────────────────────
export const adminApi = {
  getDashboard: () =>
    api.get<DashboardStats>("/admin/dashboard").then((r) => r.data),

  getUsers: (page = 1) =>
    api.get("/admin/users", { params: { page } }).then((r) => r.data),

  updateUser: (userId: string, data: Partial<{ role: string; is_active: boolean; is_verified: boolean }>) =>
    api.patch(`/admin/users/${userId}`, data).then((r) => r.data),

  getPendingSessions: (page = 1) =>
    api.get("/admin/sessions/pending", { params: { page } }).then((r) => r.data),

  reviewSession: (sessionId: string, review_status: string, reviewer_notes?: string) =>
    api.patch(`/admin/sessions/${sessionId}/review`, { review_status, reviewer_notes }).then((r) => r.data),

  getAuditLogs: (page = 1, action?: string) =>
    api.get("/admin/audit-logs", { params: { page, action } }).then((r) => r.data),
};

export default api;
