/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_API_KEY: string;  // ← you added this
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
