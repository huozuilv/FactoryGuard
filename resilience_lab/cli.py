import asyncio
import random
from typing import List
from .injector import FaultInjector
from .agents import Agent
from .utils import EventLog, Metrics
from .agents import _event_log, _metrics

async def status_printer(components: List):
    while True:
        lines = [f"[{ 'UP' if c.healthy else 'DOWN' }] {c.name} (failures={c.failure_count})" for c in components]
        print("组件状态: " + "; ".join(lines))
        await asyncio.sleep(6)


async def cli_loop(injector: FaultInjector, agents: List[Agent]):
    print("运行中的工厂自治修复演示 FactoryGuard (输入: i=注入故障, e=事件, m=指标, s=设备状态, q=退出)")
    loop = asyncio.get_running_loop()

    def ask_input():
        return input().strip()

    while True:
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
        elif user_in == 'e':
            evs = _event_log.tail(10)
            print('最近事件:')
            for e in evs:
                print(e)
        elif user_in == 'm':
            print('指标: ', _metrics.get())
        elif user_in == 's':
            lines = [f"[{ 'OK' if c.healthy else 'FAULT' }] {c.name} (failures={c.failure_count})" for c in injector.components]
            print('设备状态: ' + '; '.join(lines))
        else:
            print('未知命令. i=注入故障, q=退出')
