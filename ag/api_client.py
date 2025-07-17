import requests
import json
from typing import List, Dict, Any
from .config import API_KEY, BASE_URL, DEFAULT_MODEL

class APIError(Exception):
    """throw this when request failed"""

def send_message(
        message: List[Dict[str, str]],
        stream: bool = False,
        timeout: int = 30
) -> str:
    """
    message: [{"role":"system"|"user"|"assistant","content": "..."}...]
    stream:  ~
    timeout: ~
    """
    if not API_KEY:
        raise APIError("Missing API_KEY: set $API_KEY in .env")

    url = f"{BASE_URL}/v1/chat/completions"
    header = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "messages": message,
    }
    if stream:
        payload["stream"] = True

    resp = requests.post(url, headers=header, json=payload, timeout=timeout, stream=stream)
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise APIError(f"HTTP {resp.status_code} : {resp.text}") from e

    if not stream:
        body = resp.json()
        return body["choices"][0]["message"]["content"]

    full = ""
    for line in resp.iter_lines():
        if not line or line.startswith(b"data: [DONE]"):
            continue
        chunk = line.decode().removeprefix("data: ")
        data = json.loads(chunk)
        delta = data["choices"][0]["delta"].get("content")
        if delta:
            print(delta, end="", flush=True)
            full += delta
    print()

    return full
