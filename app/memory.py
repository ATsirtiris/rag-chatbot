import json

from typing import List, Dict, Literal

from redis.asyncio import Redis

from .settings import settings



Role = Literal["system","user","assistant"]



class RedisMemory:

    def __init__(self, url: str, max_turns: int):

        # max messages kept = user+assistant per turn

        self.max_msgs = max_turns * 2

        self.r = Redis.from_url(url, decode_responses=True)



    def _key(self, user_id: str, session_id: str) -> str:

        return f"user:{user_id}:session:{session_id}"



    async def get(self, session_id: str, user_id: str = "anonymous") -> List[Dict[str,str]]:

        key = f"user:{user_id}:session:{session_id}"

        vals = await self.r.lrange(key, 0, -1)

        return [json.loads(v) for v in vals]



    async def append(self, session_id: str, role: Role, content: str, user_id: str = "anonymous") -> None:

        item = json.dumps({"role": role, "content": content})

        key = f"user:{user_id}:session:{session_id}"

        pipe = self.r.pipeline()

        pipe.rpush(key, item)

        pipe.ltrim(key, -self.max_msgs, -1)   # keep last N

        await pipe.execute()



memory = RedisMemory(settings.REDIS_URL, settings.MAX_TURNS)

# Export Redis connection for use in other modules (e.g., auth)
redis = memory.r

