import asyncio
import logging
import random
from typing import List
from .components import Component

class FaultInjector:
    def __init__(self, components: List[Component], interval: float = 5.0, fault_prob: float = 0.3):
        self.components = components
        self.interval = interval
        self.fault_prob = fault_prob
        self.running = True

    async def run(self):
        logging.info(f"FaultInjector 启动 (interval={self.interval}s, prob={self.fault_prob})")
        while self.running:
            await asyncio.sleep(self.interval)
            if random.random() < self.fault_prob:
                comp = random.choice(self.components)
                if comp.healthy:
                    comp.mark_failure()
            await asyncio.sleep(0)
        logging.info("FaultInjector 停止")

    def stop(self):
        self.running = False
