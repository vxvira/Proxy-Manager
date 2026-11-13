import asyncio


async def _pipe(r, w):
    try:
        while data := await r.read(65536):
            w.write(data)
            await w.drain()
    except (ConnectionError, asyncio.CancelledError, OSError):
        pass
    finally:
        try:
            w.close()
        except Exception:
            pass


async def _read_addr(r):
    """Reads ATYP+ADDR+PORT from a SOCKS5 request, returns the raw bytes."""
    atyp = await r.readexactly(1)
    if atyp[0] == 1:
        body = await r.readexactly(4)
    elif atyp[0] == 3:
        n = await r.readexactly(1)
        body = n + await r.readexactly(n[0])
    elif atyp[0] == 4:
        body = await r.readexactly(16)
    else:
        raise ValueError("bad atyp")
    return atyp + body + await r.readexactly(2)


async def _skip_addr(r, atyp):
    if atyp == 1:
        await r.readexactly(6)
    elif atyp == 4:
        await r.readexactly(18)
    else:
        n = (await r.readexactly(1))[0]
        await r.readexactly(n + 2)


async def _connect_upstream(proxy, addr_bytes):
    r, w = await asyncio.wait_for(asyncio.open_connection(proxy.ip, proxy.port), 15)
    try:
        w.write(b"\x05\x02\x00\x02")  # offer no-auth + user/pass
        await w.drain()
        _, method = await asyncio.wait_for(r.readexactly(2), 15)
        if method == 2:
            u, p = proxy.username.encode(), proxy.password.encode()
            w.write(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
            await w.drain()
            if (await asyncio.wait_for(r.readexactly(2), 15))[1] != 0:
                raise ConnectionError("upstream auth failed")
        elif method != 0:
            raise ConnectionError("upstream rejected methods")
        w.write(b"\x05\x01\x00" + addr_bytes)
        await w.drain()
        head = await asyncio.wait_for(r.readexactly(4), 30)
        if head[1] != 0:
            raise ConnectionError(f"upstream connect failed ({head[1]})")
        await _skip_addr(r, head[3])
        return r, w
    except BaseException:
        w.close()
        raise


def make_handler(store):
    async def handle(cr, cw):
        try:
            ver, n = await cr.readexactly(2)
            methods = await cr.readexactly(n)
            if ver != 5 or 2 not in methods:
                cw.write(b"\x05\xff")
                return
            cw.write(b"\x05\x02")
            await cr.readexactly(1)
            ulen = (await cr.readexactly(1))[0]
            id_ = (await cr.readexactly(ulen)).decode(errors="replace")
            plen = (await cr.readexactly(1))[0]
            await cr.readexactly(plen)  # password ignored
            proxy = store.get(id_)
            if proxy is None:
                cw.write(b"\x01\x01")
                return
            cw.write(b"\x01\x00")
            hdr = await cr.readexactly(3)
            if hdr[1] != 1:  # CONNECT only
                cw.write(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            addr = await _read_addr(cr)
            try:
                ur, uw = await _connect_upstream(proxy, addr)
            except Exception:
                cw.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
                return
            cw.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            await cw.drain()
            await asyncio.gather(_pipe(cr, uw), _pipe(ur, cw))
        except (asyncio.IncompleteReadError, ConnectionError, OSError, ValueError):
            pass
        finally:
            try:
                cw.close()
            except Exception:
                pass

    return handle
