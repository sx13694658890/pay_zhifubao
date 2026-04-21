/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 根地址，例如 https://api.example.com；留空则走当前站点（配合 Vite 代理 /api） */
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
