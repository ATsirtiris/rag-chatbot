import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional



import requests



API_BASE = "http://localhost:8010"  # adjust if needed
USE_RAG = True
K = 4



EVAL_FILE = Path("eval.jsonl")





def load_eval_cases() -> List[Dict[str, Any]]:

    if not EVAL_FILE.exists():

        raise SystemExit(f"Missing {EVAL_FILE}. Create it with one JSON object per line.")

    cases = []

    with EVAL_FILE.open("r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line:

                continue

            cases.append(json.loads(line))

    return cases





def call_chat(question: str, session_id: Optional[str] = None) -> Dict[str, Any]:

    payload = {

        "message": question,

        "session_id": session_id,

        "use_rag": USE_RAG,

        "k": K,

    }

    t0 = time.time()

    resp = requests.post(f"{API_BASE}/chat", json=payload, timeout=60)

    dt = (time.time() - t0) * 1000.0

    try:

        data = resp.json()

    except Exception:

        data = {"raw": resp.text}

    data["_latency_ms"] = dt

    data["_status"] = resp.status_code

    return data





def text_contains(text: str, needle: Optional[str]) -> bool:

    if not needle:

        return False

    # Normalize both strings for comparison (remove spaces, punctuation variations)
    text_norm = text.lower().replace(" ", "").replace(",", ".").replace("€", "").replace("$", "").replace("euro", "").replace("euros", "")
    needle_norm = needle.lower().replace(" ", "").replace(",", ".").replace("€", "").replace("$", "").replace("euro", "").replace("euros", "")
    
    # Check if normalized needle is in normalized text
    if needle_norm in text_norm:
        return True
    
    # Also check original (case-insensitive)
    return needle.lower() in text.lower()





def looks_like_idk(text: str) -> bool:

    t = text.lower()

    phrases = [

        "i don't know",

        "i do not know",

        "not in the documents",

        "not based on the documents",

        "i cannot find that",

        "no information available",

    ]

    return any(p in t for p in phrases)





def has_correct_source(sources: Optional[List[Dict[str, Any]]], must: Optional[str]) -> bool:

    if not must or not sources:

        return False

    must = must.lower()

    for s in sources:

        src = (s.get("source") or "").lower()

        if must in src:

            return True

    return False





def eval_case(case: Dict[str, Any], resp: Dict[str, Any]) -> Dict[str, Any]:

    q = case.get("question", "")

    expected = case.get("expected_substring")

    must_src = case.get("must_mention_source")

    should_idk = bool(case.get("should_say_idk"))



    ans = (resp.get("answer") or "").strip()

    sources = resp.get("sources") or []

    status = resp.get("_status", 0)

    latency = resp.get("_latency_ms", 0.0)



    # Basic flags

    contains_expected = text_contains(ans, expected) if expected else False

    cites_correct_src = has_correct_source(sources, must_src)

    says_idk = looks_like_idk(ans)



    # Classification

    if status != 200 or not ans:

        label = "error"

    elif should_idk:

        # Unanswerable: good if it refuses / says idk

        label = "correct_idk" if says_idk else "hallucination"

    else:

        # Answerable

        if expected and contains_expected:

            # Check grounding if specified

            if must_src:

                label = "correct_grounded" if cites_correct_src else "correct_unguarded"

            else:

                label = "correct"

        else:

            # wrong or vague

            label = "incorrect"



    return {

        "id": case.get("id"),

        "question": q,

        "label": label,

        "latency_ms": round(latency, 1),

        "has_sources": bool(sources),

        "cites_correct_src": cites_correct_src,

        "contains_expected": contains_expected,

        "says_idk": says_idk,

    }





def summarize(results: List[Dict[str, Any]]) -> None:

    from collections import Counter



    labels = Counter(r["label"] for r in results)

    latencies = [r["latency_ms"] for r in results if isinstance(r["latency_ms"], (int, float))]

    grounded = sum(1 for r in results if r["label"] == "correct_grounded")

    with_src = sum(1 for r in results if r["has_sources"])

    n = len(results)



    def pct(x: int) -> str:

        return f"{(x / n * 100):.1f}%" if n else "0.0%"



    print("\n=== Evaluation Summary ===")

    print(f"Total cases: {n}")

    for label, count in labels.items():

        print(f"{label:18s}: {count:3d} ({pct(count)})")



    if latencies:

        lat_sorted = sorted(latencies)

        p50 = lat_sorted[int(0.5 * (len(lat_sorted) - 1))]

        p95 = lat_sorted[int(0.95 * (len(lat_sorted) - 1))]

        print(f"\nLatency p50: {p50:.1f} ms")

        print(f"Latency p95: {p95:.1f} ms")



    print(f"\nAnswers with any sources: {with_src} ({pct(with_src)})")

    print(f"Correct & grounded (correct_grounded): {grounded} ({pct(grounded)})")



    print("\n=== Per-case breakdown ===")

    for r in results:

        print(

            f"[{r['id']}] {r['label']:18s} "

            f"lat={r['latency_ms']:6.1f}ms "

            f"exp={r['contains_expected']} "

            f"src_ok={r['cites_correct_src']} "

            f"idk={r['says_idk']}"

        )





def main():

    print("Loading eval cases...")

    cases = load_eval_cases()

    print(f"Loaded {len(cases)} cases.")

    results = []



    # Use a fresh session for each Q so context doesn't leak between evals

    for case in cases:

        resp = call_chat(case["question"], session_id=None)

        r = eval_case(case, resp)

        results.append(r)



    summarize(results)





if __name__ == "__main__":

    main()

