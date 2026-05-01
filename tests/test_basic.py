import asyncio
from resilience_lab.components import Component


def test_component_recover():
    c = Component('t1')
    c.mark_failure()
    assert not c.healthy
    c.recover()
    assert c.healthy
