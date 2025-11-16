import httpx, asyncio

from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from .settings import settings



@retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4))

async def chat_complete(messages: list[dict[str,str]]) -> tuple[str,int|None,int|None]:

    url = f"{settings.LLM_API_BASE}/chat/completions"

    headers = {

        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",

        "Content-Type": "application/json",

    }

    payload = {

        "model": settings.MODEL_NAME,

        "messages": messages,

        "temperature": 0.2,

    }

    timeout = httpx.Timeout(settings.TIMEOUT_S)

    async with httpx.AsyncClient(timeout=timeout) as client:

        r = await client.post(url, headers=headers, json=payload)

        r.raise_for_status()

        data = r.json()

        answer = data["choices"][0]["message"]["content"]

        usage = data.get("usage", {})

        return answer, usage.get("prompt_tokens"), usage.get("completion_tokens")



async def ping_openai() -> bool:

    """

    Light-touch check: hit /models to verify auth/connectivity.

    This avoids spending tokens compared to a chat completion.

    """

    url = f"{settings.LLM_API_BASE}/models"

    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    timeout = httpx.Timeout(10.0)

    try:

        async with httpx.AsyncClient(timeout=timeout) as client:

            r = await client.get(url, headers=headers)

            r.raise_for_status()

        return True

    except Exception:

        return False

