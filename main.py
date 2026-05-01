"""
轻量级面向工业设备的自治修复 MVP（FactoryGuard）
场景: 轻量级工厂 / 车间设备（传感器、执行器、生产线单元）的故障检测、诊断与自动修复演示。
运行: python main.py 或 python -m resilience_lab
功能概述:
- MonitorAgent: 周期性检测设备并上报告警（支持传感器读数）
- DiagnoserAgent: 分析告警，选取修复策略（软重启/重启/替换）
- HealerAgent: 执行修复（设备重启、替换模块），并记录结果
- FaultInjector: 随机注入设备故障以验证系统行为
- 简单 CLI: 触发故障、查看最近事件与指标、查看设备状态

设计原则: 面向轻量级工业场景，使用纯 Python 标准库，易读、易扩展，适合做快速原型与车间演示
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# --- 的受管组件 ---
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


# --- Agent 基类 ---
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
                await asyncio.sleep(0)  # allow other tasks to run
        logging.info(f"{self.name} 停止")

    def stop(self):
        self.running = False


# --- 监控 Agent ---
class MonitorAgent(Agent):
    def __init__(self, name: str, components: List[Component], diagnoser_queue: asyncio.Queue, interval: float = 2.0):
        super().__init__(name)
        self.components = components
        self.diagnoser_queue = diagnoser_queue
        self.interval = interval

    async def probe_component(self, comp: Component):
        #检测延迟
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


# --- 诊断 Agent ---
class DiagnoserAgent(Agent):
    def __init__(self, name: str, healer_queue: asyncio.Queue):
        super().__init__(name)
        self.healer_queue = healer_queue

    async def analyze(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        # 简单诊断逻辑: 如果 failure_count>1 认为需要重启，否则先尝试轻修
        comp = alert['component']
        fc = alert.get('failure_count', 1)
        decision = 'restart' if fc > 1 else 'soft-restart'
        diagnosis = {
            'type': 'heal_request',
            'component': comp,
            'decision': decision,
            'reason': f"failure_count={fc}",
            'timestamp': time.time(),
        }
        logging.info(f"{self.name} 对 {comp} 的诊断: {decision}")
        return diagnosis

    async def handle(self, msg: Dict[str, Any]):
        if msg.get('type') == 'alert':
            diag = await self.analyze(msg)
            await self.send(diag, self.healer_queue)
        else:
            logging.debug(f"{self.name} 收到未知消息: {msg}")


# --- 自愈(修复) Agent ---
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

        #不同修复策略成功率
        if decision == 'soft-restart':
            success = random.random() < 0.7
        else:
            success = random.random() < 0.9

        await asyncio.sleep(1)  # 修复时间

        if success:
            comp.recover()
            result = {'type': 'heal_result', 'component': comp_name, 'success': True, 'action': decision}
            logging.info(f"{self.name} 修复成功: {comp_name} ({decision})")
        else:
            result = {'type': 'heal_result', 'component': comp_name, 'success': False, 'action': decision}
            logging.warning(f"{self.name} 修复失败: {comp_name} ({decision})")

        # 这里可以将结果上报回 diagnoser/monitor（简单打印即可）
        return result

    async def handle(self, msg: Dict[str, Any]):
        if msg.get('type') == 'heal_request':
            await self.attempt_heal(msg)
        else:
            logging.debug(f"{self.name} 收到未知消息: {msg}")


# --- 故障注入器 ---
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


# --- 小型演示/CLI ---
async def status_printer(components: List[Component]):
    while True:
        lines = [f"[{ 'UP' if c.healthy else 'DOWN' }] {c.name} (failures={c.failure_count})" for c in components]
        logging.info("组件状态: " + "; ".join(lines))
        await asyncio.sleep(6)


async def cli_loop(injector: FaultInjector, agents: List[Agent]):
    print("运行中的自治恢复演示 ResilienceLab (输入: i=注入故障, q=退出)")
    loop = asyncio.get_running_loop()

    def ask_input():
        return input().strip()

    while True:
        # 非阻塞读取用户输入
        user_in = await loop.run_in_executor(None, ask_input)
        if user_in == 'q':
            print('退出中...')
            injector.stop()
            for a in agents:
                a.stop()
            break
        elif user_in == 'i':
            comp = random.choice(injector.components)
            comp.mark_failure()
            print(f'手动注入故障: {comp.name}')
        else:
            print('未知命令. i=注入故障, q=退出')


async def main():
    random.seed(42)

    # 创建组件和共享队列
    comps = [Component(f"machine-{i}") for i in range(1, 5)]
    comps_map = {c.name: c for c in comps}

    diagnoser_q = asyncio.Queue()
    healer_q = asyncio.Queue()

    # 创建 agents
    monitor = MonitorAgent('MonitorAgent', comps, diagnoser_q, interval=2.0)
    diagnoser = DiagnoserAgent('DiagnoserAgent', healer_q)
    healer = HealerAgent('HealerAgent', comps_map)

    injector = FaultInjector(comps, interval=5.0, fault_prob=0.4)

    # 任务: agent run loops
    tasks = [
        asyncio.create_task(monitor.run()),
        asyncio.create_task(diagnoser.run()),
        asyncio.create_task(healer.run()),
        asyncio.create_task(injector.run()),
        asyncio.create_task(status_printer(comps)),
    ]

    # 用一个小协程把 diagnoser_q 的消息送到 diagnoser.inbox
    async def forward(src_q: asyncio.Queue, dst_agent: Agent):
        while dst_agent.running:
            msg = await src_q.get()
            await dst_agent.inbox.put(msg)

    tasks.append(asyncio.create_task(forward(diagnoser_q, diagnoser)))
    tasks.append(asyncio.create_task(forward(healer_q, healer)))

    # CLI
    tasks.append(asyncio.create_task(cli_loop(injector, [monitor, diagnoser, healer])))

    # 等待 CLI 结束 (用户输入 q)
    await tasks[-1]

    # 取消其它任务并等待收尾
    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.sleep(0.5)
    logging.info('主程序退出')


# 用于兼容旧入口的轻量脚本
from resilience_lab import __title__, __version__

if __name__ == '__main__':
    print(f"{__title__} version {__version__}")
    print("运行: python -m resilience_lab")