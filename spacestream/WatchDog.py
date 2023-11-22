import threading
import time
from enum import Enum

from duit.model.DataField import DataField


class HealthStatus(Enum):
    Online = 0
    Warning = 1
    Offline = 2


class WatchDog:
    def __init__(self, warning_timeout: float = 0.1, offline_timeout: float = 1.0, update_interval: float = 0.1):
        self.health = DataField(HealthStatus.Offline)

        self.last_timestamp: float = time.time()
        self.update_interval = update_interval

        self.warning_timeout = warning_timeout
        self.offline_timeout = offline_timeout

        self._running = True
        # self.thread = threading.Thread(target=self._loop)

    def start(self):
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()

    def reset(self):
        self.last_timestamp = time.time()

    def _loop(self):
        while self._running:
            self.update()
            time.sleep(self.update_interval)

    def update(self):
        ts = time.time()

        if ts - self.last_timestamp > self.offline_timeout:
            self.health.value = HealthStatus.Offline
            return

        if ts - self.last_timestamp > self.warning_timeout:
            self.health.value = HealthStatus.Warning
            return

        self.health.value = HealthStatus.Online
