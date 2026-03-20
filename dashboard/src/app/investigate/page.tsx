"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Trash2, Loader2, Brain, User, Sparkles } from "lucide-react";
import { useStore } from "@/lib/store";
import { investigate } from "@/lib/api";

export default function InvestigatePage() {
  const messages = useStore((s) => s.messages);
  const addMessage = useStore((s) => s.addMessage);
  const appendToLastMessage = useStore((s) => s.appendToLastMessage);
  const clearMessages = useStore((s) => s.clearMessages);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || streaming) return;
    setInput("");
    addMessage({ role: "user", content: q });
    addMessage({ role: "assistant", content: "" });
    setStreaming(true);

    controllerRef.current = investigate(
      q,
      (token) => appendToLastMessage(token),
      () => setStreaming(false)
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    "What are the most critical threats to coral reef ecosystems?",
    "Analyze illegal fishing patterns in the Western Indian Ocean",
    "What is the relationship between sea temperature and species migration?",
    "Summarize the latest maritime security assessments",
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          /* Welcome state */
          <div className="flex flex-col items-center justify-center h-full px-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent-violet to-accent-blue flex items-center justify-center mb-6">
              <Brain size={32} className="text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Ocean Intelligence Investigation</h2>
            <p className="text-sm text-text-muted mb-8 max-w-md text-center">
              Ask questions about ocean data, entities, threats, and trends. Powered by Claude AI with access to the full Okeanus knowledge base.
            </p>
            <div className="grid grid-cols-2 gap-3 max-w-2xl w-full">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => {
                    setInput(s);
                    inputRef.current?.focus();
                  }}
                  className="text-left bg-bg-surface border border-white/5 rounded-xl p-4 hover:bg-bg-hover hover:border-accent-violet/30 transition-all group"
                >
                  <div className="flex items-start gap-2">
                    <Sparkles size={14} className="text-accent-violet mt-0.5 shrink-0 group-hover:text-accent-violet" />
                    <span className="text-sm text-text-secondary group-hover:text-text-primary transition-colors">
                      {s}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message thread */
          <div className="max-w-3xl mx-auto py-6 px-4 space-y-6">
            {messages.map((msg, i) => (
              <div key={i} className="flex gap-3">
                <div className="shrink-0 mt-1">
                  {msg.role === "user" ? (
                    <div className="w-7 h-7 rounded-lg bg-bg-hover flex items-center justify-center">
                      <User size={14} className="text-text-secondary" />
                    </div>
                  ) : (
                    <div className="w-7 h-7 rounded-lg bg-accent-violet/20 flex items-center justify-center">
                      <Brain size={14} className="text-accent-violet" />
                    </div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[10px] uppercase tracking-wider text-text-muted mb-1 font-semibold">
                    {msg.role === "user" ? "You" : "Okeanus AI"}
                  </div>
                  <div className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                    {msg.content}
                    {streaming && i === messages.length - 1 && msg.role === "assistant" && (
                      <span className="inline-block w-2 h-4 bg-accent-violet/60 animate-pulse ml-0.5" />
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-white/5 bg-bg-surface p-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3 bg-bg-deep border border-white/10 rounded-xl px-4 py-3 focus-within:border-accent-violet/40 transition-colors">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about ocean intelligence..."
              rows={1}
              className="flex-1 bg-transparent text-sm text-text-primary outline-none resize-none max-h-32 placeholder:text-text-muted"
              style={{ minHeight: "24px" }}
            />
            <div className="flex items-center gap-2 shrink-0">
              {messages.length > 0 && (
                <button
                  onClick={clearMessages}
                  className="text-text-muted hover:text-text-secondary p-1 transition-colors"
                  title="Clear conversation"
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button
                onClick={handleSend}
                disabled={!input.trim() || streaming}
                className="bg-accent-violet hover:bg-accent-violet/80 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg p-2 transition-colors"
              >
                {streaming ? (
                  <Loader2 size={16} className="animate-spin" />
                ) : (
                  <Send size={16} />
                )}
              </button>
            </div>
          </div>
          <div className="text-[10px] text-text-muted text-center mt-2">
            Okeanus AI has access to {">"}41K entities, 55 alerts, and full ocean intelligence data.
            Press Enter to send, Shift+Enter for new line.
          </div>
        </div>
      </div>
    </div>
  );
}
