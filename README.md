# FactoryGuard（面向轻量级工厂的自治修复器）

FactoryGuard 是一个轻量级的自治修复仿真器，面向小型工厂/车间场景，用于演示设备（传感器、PLC、执行器、产线单元）在出现故障时的监控、诊断与自动修复流程。

快速开始：

- 要运行演示，请使用 Python 3.8+：

  python -m resilience_lab

功能亮点：
- 设备与故障注入
- 多 Agent 协作：监控 -> 诊断 -> 修复
- 简易事件日志与指标
- CLI 支持查看最近事件、指标与设备状态

文件结构：
- resilience_lab/ (包)
  - __main__.py: 程序入口（工厂场景）
  - components.py: 受管设备模型
  - agents.py: Monitor/Diagnoser/Healer 实现
  - injector.py: 故障注入器
  - cli.py: 命令行交互

许可证: MIT
"# FactoryGuard" 
"# FactoryGuard" 
"# FactoryGuard" 
"# FactoryGuard" 
