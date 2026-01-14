from fastapi import FastAPI, Body, Depends

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse, JSONResponse

from uuid import uuid4

from pathlib import Path

from typing import Any, Dict



from .settings import settings

from .llm import chat_complete, ping_openai

from .memory import memory

from .logger import log_event

from .retriever import rag

from .users import router as user_router

from .auth import get_current_user



RAG_MIN_SCORE = 0.30  # tune if needed



app = FastAPI(title="General Chatbot MVP (Redis)")

app.add_middleware(

CORSMiddleware,

allow_origins=["http://localhost:3000", "http://localhost:3010"],

allow_credentials=True,

allow_methods=["*"],

allow_headers=["*"],

)



app.include_router(user_router)



@app.get("/", response_class=HTMLResponse)

def home():

    return Path("web/index.html").read_text()



@app.get("/health")

async def health() -> JSONResponse:

    # Redis check

    try:

        pong = await memory.r.ping()

        redis_ok = bool(pong)

        dbsize = await memory.r.dbsize() if redis_ok else None

    except Exception as e:

        redis_ok = False

        dbsize = None



    # OpenAI check

    openai_ok = await ping_openai()



    status = {

        "redis": {"ok": redis_ok, "dbsize": dbsize, "url": settings.REDIS_URL},

        "openai": {"ok": openai_ok, "model": settings.MODEL_NAME},

        "app": {"system_prompt_len": len(settings.SYSTEM_PROMPT)},

    }

    http_status = 200 if (redis_ok and openai_ok) else 503

    return JSONResponse(status, status_code=http_status)



@app.post("/chat")

async def chat(req: Dict[str, Any], user_id: str = Depends(get_current_user)):

    try:

        session_id = req.get("session_id") or str(uuid4())

        user_msg = (req.get("message") or "").strip()

        use_rag = bool(req.get("use_rag", False))

        k = int(req.get("k", 6))  # default to 6 for balanced retrieval coverage



        if not user_msg:

            log_event("error.empty_message", {"session_id": session_id})

            return JSONResponse({"error": "Empty message", "session_id": session_id}, status_code=400)



        history = await memory.get(session_id, user_id)



        citations = []

        context_block = ""

        system_prompt = settings.SYSTEM_PROMPT  # default: normal assistant



        if use_rag:

            docs = await rag.retrieve(user_msg, k=k)



            # keep only docs above a similarity threshold

            good_docs = [d for d in docs if (d.get("score") or 0) >= RAG_MIN_SCORE]



            if good_docs:

                # use up to k best docs for context

                top = good_docs[:k]

                snippets = [d["text"] for d in top]



                citations = [

                {

                    "source": d["metadata"].get("source"),

                    "page": d["metadata"].get("page"),

                    "score": d.get("score"),

                    "snippet": d["text"][:300],

                }

                for d in top

                ]



                # soft, friendly grounding: use context when useful, but answer normally

                context_block = (

                "\n\nYou have access to the following relevant document excerpts. "

                "Use them to improve accuracy, especially for concrete facts (amounts, dates, IDs, terms). "

                "Answer in a natural, conversational way. "

                "If the excerpts do not contain the answer, you may rely on your general knowledge, "

                "but do not invent specific personal details.\n"

                "DOCUMENT CONTEXT:\n"

                + "\n---\n".join(snippets)

                + "\n"

                )



                system_prompt = (

                "You are a helpful, conversational assistant. "

                "You have access to relevant excerpts from uploaded documents. "

                "Treat those excerpts as information you already know — use them naturally when they help answer the user's question. "

                "Speak like a normal assistant, not like you are reading files. "

                "If the excerpts do not contain the answer, you can use general knowledge. "

                "Only say you are unsure if you truly have no reliable information."

                )

            # if no good_docs: fall back to normal chat behavior (no context_block)



        messages = (

        [{"role": "system", "content": system_prompt + context_block}]

        + history

        + [{"role": "user", "content": user_msg}]

        )



        log_event(

        "chat.request",

        {

            "session_id": session_id,

            "message": user_msg,

            "history_len": len(history),

            "use_rag": use_rag,

            "k": k,

            "rag_docs_used": len(citations),

        },

        )



        answer, tokens_in, tokens_out = await chat_complete(messages)



        await memory.append(session_id, "user", user_msg, user_id)

        await memory.append(session_id, "assistant", answer, user_id)



        log_event(

        "chat.response",

        {

            "session_id": session_id,

            "answer_preview": answer[:200],

            "tokens_in": tokens_in,

            "tokens_out": tokens_out,

            "use_rag": use_rag,

            "rag_docs_used": len(citations),

        },

        )



        return {

            "answer": answer,

            "session_id": session_id,

            "tokens_in": tokens_in,

            "tokens_out": tokens_out,

            "sources": citations,  # list of {source, page, score, snippet}

        }
    except Exception as e:
        log_event("error.chat_exception", {"session_id": session_id if 'session_id' in locals() else "unknown", "error": str(e)})
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}", "session_id": session_id if 'session_id' in locals() else None},
            status_code=500
        )



@app.post("/reset_session")

async def reset_session(payload: dict = Body(...), user_id: str = Depends(get_current_user)):

    session_id = (payload or {}).get("session_id")

    if not session_id:

        return {"ok": False, "error": "missing session_id"}

    try:

        key = f"user:{user_id}:session:{session_id}"

        await memory.r.delete(key)

        return {"ok": True}

    except Exception as e:

        return {"ok": False, "error": str(e)}


@app.get("/session/{session_id}")

async def get_session(session_id: str, user_id: str = Depends(get_current_user)):

    """Return the full chat history for a given session_id."""

    history = await memory.get(session_id, user_id)

    if not history:

        return JSONResponse({"error": "Session not found or empty"}, status_code=404)

    return JSONResponse({

        "username": user_id,

        "session_id": session_id,

        "history": history

    })

