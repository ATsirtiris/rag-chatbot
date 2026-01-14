const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export function getAuthHeaders(): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}



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

  try {

    const res = await fetch(`${BASE}/chat`, {

      method: "POST",

      headers: getAuthHeaders(),

      body: JSON.stringify({

        message,

        session_id: sessionId ?? null,

        use_rag: opts?.useRag ?? false,

        k: opts?.k ?? 6,  // default to 6

      }),

    });

    const t1 = performance.now();

    const latencyMs = Math.round(t1 - t0);

    

    let data: ChatResponse;

    try {

      const text = await res.text();
      try {
        data = JSON.parse(text) as ChatResponse;
      } catch (parseError) {
        console.error("Failed to parse JSON response:", text.slice(0, 500));
        data = { error: `Server error (${res.status}): Invalid JSON response` };
      }

    } catch (e) {

      // If reading response fails
      console.error("Failed to read response:", e);
      data = { error: `Server error (${res.status}): Could not read response` };

    }

    

    return { ok: res.ok as boolean, latencyMs, data };

  } catch (e: any) {

    // Network error or fetch failed

    console.error("Network error in postChat:", e);
    const t1 = performance.now();

    const latencyMs = Math.round(t1 - t0);

    return {

      ok: false,

      latencyMs,

      data: { error: e?.message || "Network error: Could not connect to backend" },

    };

  }

}



export async function getHealth() {

  try {

    const res = await fetch(`${BASE}/health`, { cache: "no-store" });

    if (!res.ok) return null;

    return await res.json();

  } catch (e) {

    return null;

  }

}

export async function resetSession(sessionId: string) {

  const res = await fetch(`${BASE}/reset_session`, {

    method: "POST",

    headers: getAuthHeaders(),

    body: JSON.stringify({ session_id: sessionId }),

  });

  return res.ok;

}

