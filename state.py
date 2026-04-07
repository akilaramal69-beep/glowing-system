import json
import os
import time

STATE_FILE = "positions.json"

class StateManager:
    def __init__(self):
        self.positions = self._load_state()
        self.signals = {}  # token_address -> [timestamp1, timestamp2, ...]

    def _load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_state(self):
        with open(STATE_FILE, "w") as f:
            json.dump(self.positions, f, indent=4)

    def add_position(self, token_address, entry_price, size_sol):
        self.positions[token_address] = {
            "entry_price": entry_price,
            "size_sol": size_sol,
            "timestamp": time.time()
        }
        self.save_state()

    def remove_position(self, token_address):
        if token_address in self.positions:
            del self.positions[token_address]
            self.save_state()

    def record_signal(self, token_address):
        if token_address not in self.signals:
            self.signals[token_address] = []
        self.signals[token_address].append(time.time())

    def get_signal_count(self, token_address, window_seconds):
        now = time.time()
        if token_address not in self.signals:
            return 0
        
        # Cleanup old signals
        self.signals[token_address] = [t for t in self.signals[token_address] if now - t <= window_seconds]
        return len(self.signals[token_address])

state_manager = StateManager()
