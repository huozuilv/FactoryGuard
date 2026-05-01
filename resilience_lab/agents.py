import asyncio
import logging
import random
import time
from typing import Dict, Any, List
from .components import Component
from .utils import EventLog, Metrics

# add global simple telemetry
_event_log = EventLog()
_metrics = Metrics()

class Agent:
    def __init__(self, name: str):
        self.name = name
        self.inbox: asyncio.Queue = asyncio.Queue()
        self.running = True

    async def send(self, msg: Dict[str, Any], q: asyncio.Queue):
        await q.put(msg)

    async def handle(self, msg: Dict[str, Any]):
        raise NotImplementedError

    async def run(self):
        logging.info(f"{self.name} 启动")
        while self.running:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=1.0)
                await self.handle(msg)
            except asyncio.TimeoutError:
                await asyncio.sleep(0)
        logging.info(f"{self.name} 停止")

    def stop(self):
        self.running = False


class MonitorAgent(Agent):
    def __init__(self, name: str, components: List[Component], diagnoser_queue: asyncio.Queue, interval: float = 2.0):
        super().__init__(name)
        self.components = components
        self.diagnoser_queue = diagnoser_queue
        self.interval = interval

    async def probe_component(self, comp: Component):
        await asyncio.sleep(0)
        comp.last_checked = time.time()
        if not comp.healthy:
            alert = {
                'type': 'alert',
                'component': comp.name,
                'timestamp': comp.last_checked,
                'failure_count': comp.failure_count,
                'metadata': comp.metadata,
            }
            logging.warning(f"{self.name} 发现告警: {comp.name}")
            await self.send(alert, self.diagnoser_queue)

    async def run(self):
        logging.info(f"{self.name} 启动 (interval={self.interval}s)")
        while self.running:
            for c in self.components:
                await self.probe_component(c)
            await asyncio.sleep(self.interval)
        logging.info(f"{self.name} 停止")


class DiagnoserAgent(Agent):
    def __init__(self, name: str, healer_queue: asyncio.Queue):
        super().__init__(name)
        self.healer_queue = healer_queue

    async def analyze(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        comp = alert['component']
        fc = alert.get('failure_count', 1)
        # 增强决策: 如果很频繁失败 -> escalate to 'replace'
        if fc > 3:
            decision = 'replace'
        else:
            decision = 'restart' if fc > 1 else 'soft-restart'

        diagnosis = {
            'type': 'heal_request',
            'component': comp,
            'decision': decision,
            'reason': f"failure_count={fc}",
            'timestamp': time.time(),
        }
        logging.info(f"{self.name} 对 {comp} 的诊断: {decision}")
        _event_log.push({'source': self.name, 'event': 'diagnosis', 'component': comp, 'decision': decision})
        _metrics.incr('diagnoses')
        return diagnosis

    async def handle(self, msg: Dict[str, Any]):
        if msg.get('type') == 'alert':
            diag = await self.analyze(msg)
            await self.send(diag, self.healer_queue)
        else:
            logging.debug(f"{self.name} 收到未知消息: {msg}")


class HealerAgent(Agent):
    def __init__(self, name: str, components: Dict[str, Component]):
        super().__init__(name)
        self.components = components

    async def attempt_heal(self, req: Dict[str, Any]):
        comp_name = req['component']
        decision = req['decision']
        comp = self.components.get(comp_name)
        if not comp:
            logging.error(f"{self.name} 未找到组件 {comp_name}")
            return

        # map action to strategy
        if decision == 'soft-restart':
            success = random.random() < 0.75
        elif decision == 'restart':
            success = random.random() < 0.9
        elif decision == 'replace':
            # replace 更昂贵但成功率高
            success = random.random() < 0.95
        else:
            success = False

        await asyncio.sleep(1)

        _metrics.incr('heal_attempts')
        _event_log.push({'source': self.name, 'event': 'heal_attempt', 'component': comp_name, 'action': decision})

        if success:
            comp.recover()
            result = {'type': 'heal_result', 'component': comp_name, 'success': True, 'action': decision}
            logging.info(f"{self.name} 修复成功: {comp_name} ({decision})")
            _event_log.push({'source': self.name, 'event': 'heal_success', 'component': comp_name, 'action': decision})
            _metrics.incr('heal_success')
        else:
            result = {'type': 'heal_result', 'component': comp_name, 'success': False, 'action': decision}
            logging.warning(f"{self.name} 修复失败: {comp_name} ({decision})")
            _event_log.push({'source': self.name, 'event': 'heal_failure', 'component': comp_name, 'action': decision})
            _metrics.incr('heal_failure')

        return result

    async def handle(self, msg: Dict[str, Any]):
        if msg.get('type') == 'heal_request':
            await self.attempt_heal(msg)
        else:
            logging.debug(f"{self.name} 收到未知消息: {msg}")
