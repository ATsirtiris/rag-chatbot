"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import ReactMarkdown from "react-markdown";

import remarkGfm from "remark-gfm";

import { postChat, getHealth, resetSession } from "@/lib/api";

import { useToast } from "@/components/Toast";



type Citation = {

  source?: string;

  page?: number | null;

  score?: number;

  snippet?: string;

};



type Msg = {

  role: "user" | "assistant";

  content: string;

  tokens_in?: number | null;

  tokens_out?: number | null;

  latencyMs?: number;

  sources?: Citation[];

};



export default function Chat() {

  const [sessionId, setSessionId] = useState<string | undefined>();

  const [msgs, setMsgs] = useState<Msg[]>([]);

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  const [typingDots, setTypingDots] = useState(".");

  const [useRag, setUseRag] = useState(false);

  const [k, setK] = useState(6);

  const [theme, setTheme] = useState<"light" | "dark">("dark");

  const [showSources, setShowSources] = useState(true);

  const [chatTitle, setChatTitle] = useState<string>("New Chat");



  const listRef = useRef<HTMLDivElement>(null);

  const { push, node } = useToast();



  // typing indicator animation

  useEffect(() => {

    if (!loading) return;

    const id = setInterval(() => {

      setTypingDots((d) => (d.length >= 3 ? "." : d + "."));

    }, 400);

    return () => clearInterval(id);

  }, [loading]);



  // auto-scroll

  useEffect(() => {

    listRef.current?.scrollTo({

      top: listRef.current.scrollHeight,

      behavior: "smooth",

    });

  }, [msgs, loading]);



  // restore session

  useEffect(() => {

    const saved = localStorage.getItem("session_id");

    if (saved) setSessionId(saved);

  }, []);



  // init theme from localStorage or system preference

  useEffect(() => {

    if (typeof window === "undefined") return;

    const saved = (localStorage.getItem("theme") as "light" | "dark" | null);

    const prefersDark = window.matchMedia &&

      window.matchMedia("(prefers-color-scheme: dark)").matches;

    const initial = saved || (prefersDark ? "dark" : "light");

    setTheme(initial);

    document.documentElement.classList.toggle("dark", initial === "dark");

  }, []);



  const stats = useMemo(() => {

    const totals = msgs.reduce(

      (acc, m) => {

        acc.tokens_in += m.tokens_in || 0;

        acc.tokens_out += m.tokens_out || 0;

        if (m.latencyMs) acc.latencies.push(m.latencyMs);

        return acc;

      },

      { tokens_in: 0, tokens_out: 0, latencies: [] as number[] }

    );

    const p50 = percentile(totals.latencies, 50);

    const p95 = percentile(totals.latencies, 95);

    return {

      tokens_in: totals.tokens_in,

      tokens_out: totals.tokens_out,

      p50,

      p95,

    };

  }, [msgs]);



  async function send() {

    const text = input.trim();

    if (!text || loading) return;

    setInput("");



    // push user message
    setMsgs((m) => {
      const newMsgs = [...m, { role: "user" as const, content: text }];
      // Set title from first user message if still "New Chat"
      if (chatTitle === "New Chat" && m.length === 0) {
        const title = text.slice(0, 30).trim();
        setChatTitle(title.length > 30 ? title + "..." : title);
      }
      return newMsgs;
    });

    setLoading(true);



    try {

      const res = await postChat(text, sessionId, { useRag, k });

      if (!res.ok) {

        push(res.data.error || "Request failed");

        setLoading(false);

        return;

      }



      const { answer, session_id, tokens_in, tokens_out, sources } = res.data;



      if (session_id && session_id !== sessionId) {

        setSessionId(session_id);

        localStorage.setItem("session_id", session_id);

      }



      setMsgs((m) => [

        ...m,

        {

          role: "assistant",

          content: answer || "",

          tokens_in,

          tokens_out,

          latencyMs: res.latencyMs,

          sources: sources || [],

        },

      ]);

    } catch (e: any) {

      push(e?.message || "Network error");

    } finally {

      setLoading(false);

    }

  }



  async function newChat() {

    const sid = sessionId;

    setMsgs([]);

    setSessionId(undefined);

    setChatTitle("New Chat");

    localStorage.removeItem("session_id");

    if (sid) {

      try {

        await resetSession(sid);

      } catch {

        // non-fatal

      }

    }

    push("Started a new chat");

  }



  async function checkHealth() {

    try {

      const h = await getHealth();

      if (!h) return push("Health: unavailable");

      const ok = h?.redis?.ok && h?.openai?.ok;

      push(ok ? "Health: OK" : "Health: degraded");

    } catch {

      push("Health: error");

    }

  }

  async function saveChat() {

    if (!sessionId) {

      push("No active chat to save");

      return;

    }

    try {

      const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

      const res = await fetch(`${BASE}/session/${sessionId}`);

      if (!res.ok) throw new Error("Failed to fetch session");

      const data = await res.json();

      // trigger browser download

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });

      const url = URL.createObjectURL(blob);

      const a = document.createElement("a");

      a.href = url;

      a.download = `session_${sessionId}.json`;

      a.click();

      URL.revokeObjectURL(url);

      push("Chat exported successfully!");

    } catch (err: any) {

      push("Error saving chat");

    }

  }

  async function loadChat() {

    try {

      const input = document.createElement("input");

      input.type = "file";

      input.accept = "application/json";

      input.onchange = async (e: any) => {

        const file = e.target.files?.[0];

        if (!file) return;

        const text = await file.text();

        const data = JSON.parse(text);

        if (!data.session_id || !Array.isArray(data.history)) {

          push("Invalid chat file");

          return;

        }

        // Restore chat data

        setSessionId(data.session_id);

        localStorage.setItem("session_id", data.session_id);

        setMsgs(data.history);

        // Set chat title: use file name or first user message

        if (data.history.length > 0) {

          const firstUserMsg = data.history.find((m: any) => m.role === "user");

          const nameFromMsg = firstUserMsg

            ? firstUserMsg.content.slice(0, 25) + (firstUserMsg.content.length > 25 ? "…" : "")

            : file.name.replace(".json", "");

          setChatTitle(nameFromMsg);

        } else {

          setChatTitle(file.name.replace(".json", ""));

        }

        // Visual feedback

        push(`✅ Loaded chat: ${file.name}`);

      };

      input.click();

    } catch (err: any) {

      console.error(err);

      push("Error loading chat");

    }

  }



  function toggleTheme() {

    const next = theme === "dark" ? "light" : "dark";

    setTheme(next);

    if (typeof document !== "undefined") {

      document.documentElement.classList.toggle("dark", next === "dark");

    }

    if (typeof window !== "undefined") {

      localStorage.setItem("theme", next);

    }

  }



  return (

    <div className="chat-card">

      {node}



      {/* HEADER */}

      <header className="chat-header">

        <div>

          <h1 className="chat-title">
            MSc RAG Chatbot
            <span className="ml-2 text-[10px] font-normal text-slate-400">
              — {chatTitle}
            </span>
          </h1>

          <p className="chat-subtitle">

            GPT-4 + OpenAI embeddings • Grounded answers with sources

          </p>

          <p className="chat-subtitle">

            in {stats.tokens_in} • out {stats.tokens_out} • p50 {stats.p50}ms • p95 {stats.p95}ms

          </p>

        </div>

        <div className="chat-controls">

          <span className="chat-subtitle hidden sm:inline">

            {useRag ? "RAG: ON" : "RAG: OFF"}

          </span>

          <label className="chat-toggle-label">

            <input

              type="checkbox"

              checked={useRag}

              onChange={(e) => setUseRag(e.target.checked)}

              className="w-3 h-3 accent-sky-500"

            />

            RAG

          </label>

          <label className="chat-toggle-label">

            <input

              type="checkbox"

              checked={showSources}

              onChange={(e) => setShowSources(e.target.checked)}

              className="w-3 h-3 accent-sky-500"

            />

            Show sources

          </label>

          <input

            type="number"

            min={1}

            max={10}

            value={k}

            onChange={(e) =>

              setK(

                Math.min(

                  10,

                  Math.max(1, parseInt(e.target.value || "4", 10))

                )

              )

            }

            className="chat-k-input"

            title="Top-k"

          />

          <button onClick={newChat} className="chat-btn" disabled={loading}>

            New

          </button>

          <button onClick={checkHealth} className="chat-btn" disabled={loading}>

            Health

          </button>

          <button onClick={saveChat} className="chat-btn" disabled={loading || !sessionId}>

            Save

          </button>

          <button

            onClick={loadChat}

            className="chat-btn"

            disabled={loading}

          >

            Load

          </button>

          <button

            type="button"

            onClick={toggleTheme}

            className="chat-btn"

            aria-label="Toggle theme"

          >

            <span className={`inline-block ${theme === "dark" ? "text-orange-500" : ""}`}>

              {theme === "dark" ? "☀︎" : "🌙"}

            </span>

          </button>

        </div>

      </header>



      {/* MESSAGES */}

      <div className="chat-body">

        <div ref={listRef} className="chat-messages">

          {msgs.map((m, i) => (

            <Message key={i} {...m} showSources={showSources} />

          ))}

          {loading && (

            <div className="flex items-end gap-1">

              <div className="avatar avatar-bot">AI</div>

              <div className="bubble bubble-bot">Thinking{typingDots}</div>

            </div>

          )}

        </div>

      </div>



      {/* INPUT */}

      <form

        onSubmit={(e) => {

          e.preventDefault();

          send();

        }}

        className="chat-input-wrap"

      >

        <input

          className="chat-input"

          placeholder={

            useRag

              ? "Ask something grounded in your uploaded documents..."

              : "Ask anything..."

          }

          value={input}

          onChange={(e) => setInput(e.target.value)}

        />

        <button

          className="chat-send-btn"

          disabled={loading || !input.trim()}

          type="submit"

        >

          <span>Send</span>

          <span>➜</span>

        </button>

      </form>

    </div>

  );

}



function Message({

  role,

  content,

  tokens_in,

  tokens_out,

  latencyMs,

  sources,

  showSources,

}: Msg & { showSources?: boolean }) {

  const isUser = role === "user";



  const bubble = (

    <div className={isUser ? "bubble bubble-user" : "bubble bubble-bot"}>

      {isUser ? (

        <div className="whitespace-pre-wrap">{content}</div>

      ) : (

        <>

          <div className="prose prose-invert max-w-none text-[11px]">

            <ReactMarkdown

              remarkPlugins={[remarkGfm]}

              components={{

                a({ href, children, ...props }) {

                  return (

                    <a

                      href={href || "#"}

                      target="_blank"

                      rel="noreferrer"

                      className="underline text-sky-400"

                      {...props}

                    >

                      {children}

                    </a>

                  );

                },

                code({ children, ...props }: any) {

                  const inline = (props as any).inline;

                  if (inline) {

                    return (

                      <code

                        className="bg-slate-800 rounded px-1"

                        {...props}

                      >

                        {children}

                      </code>

                    );

                  }

                  return (

                    <pre className="rounded-xl p-2.5 bg-slate-900 border border-slate-700 overflow-x-auto">

                      <code {...props}>{children}</code>

                    </pre>

                  );

                },

              }}

            >

              {content}

            </ReactMarkdown>

          </div>



          {showSources && sources && sources.length > 0 && (

            <div className="bubble-sources mt-2 border-t border-slate-700 pt-1.5">

              <div className="bubble-sources-title text-[9px] text-slate-400">

                Sources:

                {sources

                  .slice(0, 3)

                  .map((s) => `${s.source?.split("/").pop() || "?"}${s.page ? ` (p.${s.page})` : ""}`)

                  .join(", ")}

              </div>

            </div>

          )}

        </>

      )}



      {!isUser && (

        <div className="bubble-meta">

          {typeof tokens_in === "number" &&

            typeof tokens_out === "number" && (

              <span>

                tok in {tokens_in} • out {tokens_out}

              </span>

            )}

          {typeof latencyMs === "number" && (

            <span className="ml-2">{latencyMs} ms</span>

          )}

        </div>

      )}

    </div>

  );



  return (

    <div

      className={`flex items-end gap-1 ${

        isUser ? "justify-end" : "justify-start"

      }`}

    >

      {!isUser && <div className="avatar avatar-bot">AI</div>}

      {bubble}

      {isUser && <div className="avatar avatar-user">YOU</div>}

    </div>

  );

}



function percentile(arr: number[], p: number) {

  if (!arr.length) return 0;

  const s = [...arr].sort((a, b) => a - b);

  const idx = Math.floor((p / 100) * (s.length - 1));

  return s[idx];

}
