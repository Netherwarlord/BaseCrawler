import json
import os

class ConnectionManager:
    def __init__(self, file_path="connections.json"):
        self.file_path = file_path
        self.connections = self._load_connections()

    def _load_connections(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _save_connections(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.connections, f, indent=4)

    def add_connection(self, connection_details):
        self.connections.append(connection_details)
        self._save_connections()

    def get_connections(self):
        return self.connections

    def remove_connection(self, connection_name):
        self.connections = [conn for conn in self.connections if conn.get("name") != connection_name]
        self._save_connections()

    def update_connection(self, old_name, new_details):
        for i, conn in enumerate(self.connections):
            if conn.get("name") == old_name:
                self.connections[i] = new_details
                self._save_connections()
                return True
        return False

    def reorder_connection(self, connection_name, direction): # direction: -1 for up, 1 for down
        idx = -1
        for i, conn in enumerate(self.connections):
            if conn.get("name") == connection_name:
                idx = i
                break
        
        if idx == -1:
            return False # Connection not found

        new_idx = idx + direction

        if 0 <= new_idx < len(self.connections):
            conn = self.connections.pop(idx)
            self.connections.insert(new_idx, conn)
            self._save_connections()
            return True
        return False # Cannot move further