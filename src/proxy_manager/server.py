from aiohttp import web

CODES = {"success": 200, "id-already-assigned": 409, "no-available-proxies": 503}


def make_app(store):
    async def assign(request):
        id_ = None
        try:
            body = await request.json()
            if isinstance(body, dict):
                id_ = body.get("ID")
        except Exception:
            pass
        if id_ is None:
            id_ = request.query.get("ID")
        if not id_ or not isinstance(id_, str):
            return web.json_response({"status": "invalid-request"}, status=400)
        status = store.assign(id_)
        return web.json_response({"status": status}, status=CODES[status])

    app = web.Application()
    app.router.add_post("/assign", assign)
    return app
