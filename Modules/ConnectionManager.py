import json
import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
_CONNECTIONS_DIR = os.path.join(_PROJECT_ROOT, "Connections")


class ConnectionManager:
    def __init__(self):
        os.makedirs(_CONNECTIONS_DIR, exist_ok=True)
        self._connections = self._load_all()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _conn_dir(self, name: str) -> str:
        return os.path.join(_CONNECTIONS_DIR, name)

    def _conn_file(self, name: str) -> str:
        return os.path.join(self._conn_dir(name), f"{name}.json")

    def _state_file(self, name: str) -> str:
        return os.path.join(self._conn_dir(name), "ConnectionState.json")

    def _load_all(self) -> list:
        connections = []
        for entry in os.scandir(_CONNECTIONS_DIR):
            if not entry.is_dir():
                continue
            cfg = os.path.join(entry.path, f"{entry.name}.json")
            if not os.path.exists(cfg):
                continue
            try:
                with open(cfg, "r") as f:
                    data = json.load(f)
                connections.append(data)
            except (json.JSONDecodeError, OSError):
                continue
        connections.sort(key=lambda c: c.get("order", 9999))
        return connections

    def _save_connection(self, details: dict):
        name = details["name"]
        os.makedirs(self._conn_dir(name), exist_ok=True)
        with open(self._conn_file(name), "w") as f:
            json.dump(details, f, indent=4)

    def _reindex(self):
        for i, conn in enumerate(self._connections):
            conn["order"] = i
            self._save_connection(conn)

    # ── Public API ────────────────────────────────────────────────────────────

    def get_connections(self) -> list:
        return list(self._connections)

    def add_connection(self, details: dict):
        details = dict(details)
        details["order"] = len(self._connections)
        self._connections.append(details)
        self._save_connection(details)

    def remove_connection(self, name: str):
        conn_dir = self._conn_dir(name)
        if os.path.isdir(conn_dir):
            shutil.rmtree(conn_dir)
        self._connections = [c for c in self._connections if c.get("name") != name]
        self._reindex()

    def update_connection(self, old_name: str, new_details: dict) -> bool:
        new_details = dict(new_details)
        for i, conn in enumerate(self._connections):
            if conn.get("name") != old_name:
                continue
            new_details["order"] = conn.get("order", i)
            new_name = new_details["name"]

            if new_name != old_name:
                old_dir = self._conn_dir(old_name)
                new_dir = self._conn_dir(new_name)
                if os.path.isdir(old_dir):
                    os.rename(old_dir, new_dir)

            self._connections[i] = new_details
            self._save_connection(new_details)
            return True
        return False

    def reorder_connection(self, name: str, direction: int) -> bool:
        idx = next((i for i, c in enumerate(self._connections) if c.get("name") == name), -1)
        if idx == -1:
            return False
        new_idx = idx + direction
        if not (0 <= new_idx < len(self._connections)):
            return False
        self._connections.insert(new_idx, self._connections.pop(idx))
        self._reindex()
        return True

    # ── Workspace state persistence ───────────────────────────────────────────

    def save_state(self, name: str, state: dict):
        conn_dir = self._conn_dir(name)
        if not os.path.isdir(conn_dir):
            return
        try:
            with open(self._state_file(name), "w") as f:
                json.dump(state, f, indent=4)
        except OSError:
            pass

    def load_state(self, name: str) -> dict:
        path = self._state_file(name)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
