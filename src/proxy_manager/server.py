from aiohttp import web

from .forwarder import check_proxy

CODES = {
    "success": 200,
    "id-already-assigned": 409,
    "no-available-proxies": 503,
    "unknown-id": 404,
}


async def _get_id(request):
    id_ = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            id_ = body.get("ID")
    except Exception:
        pass
    if id_ is None:
        id_ = request.query.get("ID")
    return id_ if isinstance(id_, str) and id_ else None


def make_app(store, health_target=("1.1.1.1", 443)):
    def reply(status):
        return web.json_response({"status": status}, status=CODES[status])

    async def assign(request):
        id_ = await _get_id(request)
        if not id_:
            return web.json_response({"status": "invalid-request"}, status=400)
        return reply(store.assign(id_))

    async def release(request):
        id_ = await _get_id(request)
        if not id_:
            return web.json_response({"status": "invalid-request"}, status=400)
        return reply(store.release(id_))

    async def status(request):
        assigned = [{"ID": i, "ip": p.ip, "port": p.port} for i, p in store.by_id.items()]
        return web.json_response({
            "total": len(store.by_id) + len(store.free),
            "assigned": len(store.by_id),
            "free": len(store.free),
            "assignments": assigned,
        })

    async def health(request):
        id_ = await _get_id(request)
        if not id_:
            return web.json_response({"status": "invalid-request"}, status=400)
        proxy = store.get(id_)
        if proxy is None:
            return reply("unknown-id")
        ok, ms, err = await check_proxy(proxy, *health_target)
        return web.json_response(
            {"status": "healthy" if ok else "unhealthy", "ID": id_, "latency_ms": ms, "error": err},
            status=200 if ok else 502,
        )

    app = web.Application()
    app.router.add_post("/assign", assign)
    app.router.add_post("/release", release)
    app.router.add_get("/status", status)
    app.router.add_route("*", "/health", health)
    return app
