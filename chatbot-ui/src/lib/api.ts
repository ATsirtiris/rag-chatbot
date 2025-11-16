const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";



export type Citation = {

  source?: string;

  page?: number | null;

  score?: number;

  snippet?: string;

};

export type ChatResponse = {

  answer?: string;

  session_id?: string;

  tokens_in?: number | null;

  tokens_out?: number | null;

  error?: string;

  sources?: Citation[];

};



export async function postChat(

  message: string,

  sessionId?: string,

  opts?: { useRag?: boolean; k?: number }

) {

  const t0 = performance.now();

  const res = await fetch(`${BASE}/chat`, {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify({

      message,

      session_id: sessionId ?? null,

      use_rag: opts?.useRag ?? false,

      k: opts?.k ?? 8,  // increased to 8 for better retrieval coverage

    }),

  });

  const t1 = performance.now();

  const latencyMs = Math.round(t1 - t0);

  const data = (await res.json()) as ChatResponse;

  return { ok: res.ok as boolean, latencyMs, data };

}



export async function getHealth() {

  const res = await fetch(`${BASE}/health`, { cache: "no-store" });

  return res.ok ? res.json() : null;

}

export async function resetSession(sessionId: string) {

  const res = await fetch(`${BASE}/reset_session`, {

    method: "POST",

    headers: { "Content-Type": "application/json" },

    body: JSON.stringify({ session_id: sessionId }),

  });

  return res.ok;

}

