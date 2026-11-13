import csv
import os
import random
import threading
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Proxy:
    ip: str
    port: int
    username: str
    password: str

    @property
    def key(self):
        return (self.ip, self.port, self.username, self.password)


class Store:
    def __init__(self, proxies_file, assignments_file):
        self.proxies_file = Path(proxies_file)
        self.assignments_file = Path(assignments_file)
        self._lock = threading.Lock()
        self.by_id = {}  # ID -> Proxy
        self.free = []   # unassigned Proxy objects
        self.load()

    def _read_proxies(self):
        out, seen = [], set()
        if not self.proxies_file.exists():
            return out
        with open(self.proxies_file, newline="", encoding="utf-8") as f:
            for row in csv.reader(f):
                row = [c.strip() for c in row]
                if len(row) < 2 or not row[0] or row[0].startswith("#"):
                    continue
                row += [""] * (4 - len(row))
                try:
                    p = Proxy(row[0], int(row[1]), row[2], row[3])
                except ValueError:
                    continue  # header / junk line
                if p.key not in seen:
                    seen.add(p.key)
                    out.append(p)
        return out

    def load(self):
        proxies = {p.key: p for p in self._read_proxies()}
        assigned = {}
        if self.assignments_file.exists():
            with open(self.assignments_file, newline="", encoding="utf-8") as f:
                for row in csv.reader(f):
                    if len(row) < 5 or not row[4]:
                        continue
                    try:
                        key = (row[0], int(row[1]), row[2], row[3])
                    except ValueError:
                        continue
                    if key in proxies:
                        assigned[row[4]] = proxies[key]
        self.by_id = assigned
        used = {p.key for p in assigned.values()}
        self.free = [p for k, p in proxies.items() if k not in used]
        self._save()

    def _save(self):
        self.assignments_file.parent.mkdir(parents=True, exist_ok=True)
        rows = [(p, i) for i, p in self.by_id.items()] + [(p, "") for p in self.free]
        tmp = self.assignments_file.with_suffix(".tmp")
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for p, i in rows:
                w.writerow([p.ip, p.port, p.username, p.password, i])
        os.replace(tmp, self.assignments_file)

    def assign(self, id_):
        """Returns 'success', 'id-already-assigned' or 'no-available-proxies'."""
        with self._lock:
            if id_ in self.by_id:
                return "id-already-assigned"
            if not self.free:
                return "no-available-proxies"
            p = self.free.pop(random.randrange(len(self.free)))
            self.by_id[id_] = p
            self._save()
            return "success"

    def get(self, id_):
        return self.by_id.get(id_)
