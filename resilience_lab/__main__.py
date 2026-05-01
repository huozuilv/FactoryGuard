import asyncio
import random
import logging
from .components import Component
from .agents import MonitorAgent, DiagnoserAgent, HealerAgent
from .injector import FaultInjector
from .cli import status_printer, cli_loop
from .utils import EventLog, Metrics
from . import __title__, __version__

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

async def main():
    random.seed(42)

    print(f"启动 {__title__} v{__version__} — 工厂场景演示")
    
    # 模拟设备: machine-1..machine-4 （可代表传感器、PLC、伺服电机等）
    comps = [Component(f"machine-{i}") for i in range(1, 5)]
    comps_map = {c.name: c for c in comps}

    diagnoser_q = asyncio.Queue()
    healer_q = asyncio.Queue()

    monitor = MonitorAgent('MonitorAgent', comps, diagnoser_q, interval=2.0)
    diagnoser = DiagnoserAgent('DiagnoserAgent', healer_q)
    healer = HealerAgent('HealerAgent', comps_map)

    injector = FaultInjector(comps, interval=5.0, fault_prob=0.4)

    tasks = [
        asyncio.create_task(monitor.run()),
        asyncio.create_task(diagnoser.run()),
        asyncio.create_task(healer.run()),
        asyncio.create_task(injector.run()),
        asyncio.create_task(status_printer(comps)),
    ]

    async def forward(src_q: asyncio.Queue, dst_agent):
        while dst_agent.running:
            msg = await src_q.get()
            await dst_agent.inbox.put(msg)

    tasks.append(asyncio.create_task(forward(diagnoser_q, diagnoser)))
    tasks.append(asyncio.create_task(forward(healer_q, healer)))

    tasks.append(asyncio.create_task(cli_loop(injector, [monitor, diagnoser, healer])))

    await tasks[-1]

    for t in tasks:
        if not t.done():
            t.cancel()
    await asyncio.sleep(0.5)
    logging.info('主程序退出')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Interrupted')
