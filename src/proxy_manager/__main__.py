import asyncio
import tomllib
from pathlib import Path

from aiohttp import web

from .data import Store
from .forwarder import make_handler
from .server import make_app

ROOT = Path(__file__).resolve().parents[2]


async def main():
    with open(ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    host = cfg.get("host", "127.0.0.1")
    store = Store(ROOT / cfg["proxies_file"], ROOT / cfg["assignments_file"])

    runner = web.AppRunner(make_app(store))
    await runner.setup()
    await web.TCPSite(runner, host, cfg["assign_port"]).start()
    socks = await asyncio.start_server(make_handler(store), host, cfg["socks_port"])
    print(f"assign: http://{host}:{cfg['assign_port']}/assign | socks5: {host}:{cfg['socks_port']} "
          f"| {len(store.by_id)} assigned, {len(store.free)} free")
    async with socks:
        await socks.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
