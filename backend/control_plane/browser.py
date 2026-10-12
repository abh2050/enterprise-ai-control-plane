"""In-process bridge for the interactive demo, where this backend runs in the browser.

The GitHub Pages console loads the unchanged FastAPI app in Pyodide and sends every API
request through `Bridge.request`, an ASGI call with no network in between. The store is
the in-memory store seeded with the SYNTHETIC registry and the committed evidence, so
each visitor works on a private copy that a reset or a reload restores.
"""

import asyncio
import json
from collections.abc import MutableMapping
from typing import Any

from fastapi import FastAPI


def run_threads_inline() -> None:
    """Run FastAPI's sync endpoints and dependencies inline: a browser has no threads.

    Starlette calls `anyio.to_thread.run_sync` through the module attribute, so replacing
    it covers every threadpool hop. Requests are served one at a time, as JavaScript
    awaits each before sending the next.
    """
    import anyio.to_thread

    async def run_sync(func: Any, *args: Any, **_: Any) -> Any:
        return func(*args)

    anyio.to_thread.run_sync = run_sync  # type: ignore[assignment]


class Bridge:
    def __init__(self, app: FastAPI, inline_threads: bool = True) -> None:
        self.app = app
        if inline_threads:
            run_threads_inline()
        self._lifespan_events: list[dict[str, Any]] = [{"type": "lifespan.startup"}]
        self._started = False

    async def start(self) -> None:
        """Run the app's lifespan startup (bind guard and seeding) once."""
        if self._started:
            return
        sent: list[MutableMapping[str, Any]] = []

        async def receive() -> dict[str, Any]:
            if self._lifespan_events:
                return self._lifespan_events.pop(0)
            # Startup is done; never deliver shutdown while the page is open.
            await asyncio.Event().wait()
            return {}

        async def send(message: MutableMapping[str, Any]) -> None:
            sent.append(message)
            if message["type"] == "lifespan.startup.failed":
                raise RuntimeError(message.get("message", "startup failed"))

        task = asyncio.ensure_future(
            self.app({"type": "lifespan", "asgi": {"version": "3.0"}, "state": {}}, receive, send)
        )
        while not any(m["type"].startswith("lifespan.startup") for m in sent):
            if task.done():
                task.result()
            await asyncio.sleep(0)
        if sent[-1]["type"] == "lifespan.startup.failed":
            raise RuntimeError(sent[-1].get("message", "startup failed"))
        self._started = True

    async def request(
        self, method: str, path: str, headers: dict[str, str] | None = None, body: str | None = None
    ) -> dict[str, Any]:
        """Serve one request; returns status, headers, and the decoded text body."""
        await self.start()
        raw_path, _, query = path.partition("?")
        payload = (body or "").encode()
        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        if payload:
            hdrs.setdefault("content-type", "application/json")
            hdrs["content-length"] = str(len(payload))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode(),
            "query_string": query.encode(),
            "root_path": "",
            "headers": [(k.encode(), v.encode()) for k, v in hdrs.items()],
            # The call never leaves this process, so the client is loopback by definition.
            "client": ("127.0.0.1", 0),
            "server": ("browser", 0),
        }
        chunks = [{"type": "http.request", "body": payload, "more_body": False}]
        status = 500
        out_headers: dict[str, str] = {}
        parts: list[bytes] = []

        async def receive() -> dict[str, Any]:
            return chunks.pop(0) if chunks else {"type": "http.disconnect"}

        async def send(message: MutableMapping[str, Any]) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                out_headers.update({k.decode(): v.decode() for k, v in message.get("headers", [])})
            elif message["type"] == "http.response.body":
                parts.append(message.get("body", b""))

        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # a server would log this and answer 500
            if status == 500 and not parts:
                parts.append(
                    json.dumps({"detail": f"Internal error: {type(exc).__name__}"}).encode()
                )
            status = 500
        return {"status": status, "headers": out_headers, "body": b"".join(parts).decode()}

    async def request_json(self, *args: Any, **kwargs: Any) -> str:
        """`request` serialized as JSON, so JavaScript receives a plain string."""
        return json.dumps(await self.request(*args, **kwargs))
