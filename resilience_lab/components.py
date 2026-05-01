import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Component:
    name: str
    healthy: bool = True
    last_checked: float = field(default_factory=time.time)
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def mark_failure(self):
        self.healthy = False
        self.failure_count += 1
        logging.info(f"组件 {self.name} 发生故障 (count={self.failure_count})")

    def recover(self):
        self.healthy = True
        logging.info(f"组件 {self.name} 已恢复")
