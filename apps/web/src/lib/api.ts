/** 开发环境默认走 Next mock API；接 Python 时在 .env.local 设 NEXT_PUBLIC_API_BASE=http://localhost:8000 */
export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ??
  (process.env.NODE_ENV === "development" ? "/api" : "http://localhost:8000");

export const IS_MOCK = API_BASE === "/api";
