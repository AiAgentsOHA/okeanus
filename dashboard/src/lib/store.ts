import { create } from "zustand";

interface AppState {
  // Sidebar
  sidebarOpen: boolean;
  toggleSidebar: () => void;

  // Map layers
  layers: {
    entities: boolean;
    hotspots: boolean;
    density: boolean;
    alerts: boolean;
    vessels: boolean;
  };
  toggleLayer: (key: keyof AppState["layers"]) => void;

  // Selected entity
  selectedEntity: Record<string, unknown> | null;
  setSelectedEntity: (entity: Record<string, unknown> | null) => void;

  // Search
  searchOpen: boolean;
  setSearchOpen: (open: boolean) => void;

  // Investigation
  messages: { role: "user" | "assistant"; content: string }[];
  addMessage: (msg: { role: "user" | "assistant"; content: string }) => void;
  appendToLastMessage: (text: string) => void;
  clearMessages: () => void;
}

export const useStore = create<AppState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),

  layers: {
    entities: true,
    hotspots: false,
    density: false,
    alerts: true,
    vessels: false,
  },
  toggleLayer: (key) =>
    set((s) => ({ layers: { ...s.layers, [key]: !s.layers[key] } })),

  selectedEntity: null,
  setSelectedEntity: (entity) => set({ selectedEntity: entity }),

  searchOpen: false,
  setSearchOpen: (open) => set({ searchOpen: open }),

  messages: [],
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  appendToLastMessage: (text) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === "assistant") {
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          content: msgs[msgs.length - 1].content + text,
        };
      }
      return { messages: msgs };
    }),
  clearMessages: () => set({ messages: [] }),
}));
