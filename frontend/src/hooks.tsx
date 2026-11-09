// Shared hooks and context

import { createContext, useContext, useState, useCallback } from "react";
import type { ReactNode } from "react";

// ─── Toast ────────────────────────────────────────────────────────────────────

export type ToastType = "success" | "error" | "info";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastCtx {
  toasts: Toast[];
  toast: (type: ToastType, message: string) => void;
  dismiss: (id: number) => void;
}

export const ToastContext = createContext<ToastCtx>({
  toasts: [],
  toast: () => {},
  dismiss: () => {},
});

let _id = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((type: ToastType, message: string) => {
    const id = ++_id;
    setToasts((t) => [...t, { id, type, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, toast, dismiss }}>
      {children}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

