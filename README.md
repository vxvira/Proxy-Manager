Proxy manager for python
--
Point incoming connections at `127.0.0.1:{ASSIGN_PORT}/assign` (set port in config.toml) with an `{"ID":"XYZ"}` parameter and have it send requests to its assigned proxy. Add proxies to `proxies.csv` in this format: `{IP},{PORT},{USERNAME},{PASSWORD}`. 
To actually forward the data, on the first run, the script will generate `assignments.csv` that maps each unique entry in `proxies.csv` to an ID, each proxy is assigned randomly to whatever passed ID and remains attached to it forever. 

Note: the I/O is handled through SOCK5 but assignment is handled through HTTP. 
If an ID already exists an error will be returned. (status: `id-already-asssigned`)
If no more proxies exist an error will be returned. (status: `no-available-proxies`)

## Usage
1. Fill `data/proxies.csv`, adjust `config.toml`.
2. `set PYTHONPATH=src` then `python -m proxy_manager` (needs `pip install aiohttp`).
3. `POST http://127.0.0.1:{assign_port}/assign` with `{"ID":"bot1"}` -> `200 {"status":"success"}`.
4. Point the client (e.g. Minecraft bot) at SOCKS5 `127.0.0.1:{socks_port}` with **username = ID** (password ignored). Traffic is chained through that ID's proxy; remote DNS is done by the upstream proxy.

Errors: `409 id-already-asssigned`, `503 no-available-proxies`, `400 invalid-request`. `assignments.csv` is `ip,port,user,pass,id` (blank id = free).
