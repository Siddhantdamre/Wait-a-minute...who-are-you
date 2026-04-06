from deic_core import ToolInterface
import pytest

class DummyAdapter(ToolInterface):
    def observe(self, source, item):
        return {"status": "success", "value": 15}
    def commit(self, proposed_state, escalated=False):
        return {"correct": True}
    def remaining_budget(self):
        return 5

def test_tool_interface():
    adapter = DummyAdapter()
    assert adapter.observe("s1", "i1") == {"status": "success", "value": 15}
    assert adapter.commit({"i1": 15}) == {"correct": True}
    assert adapter.remaining_budget() == 5

def test_interface_not_implemented():
    class IncompleteAdapter(ToolInterface):
        pass
    
    adapter = IncompleteAdapter()
    with pytest.raises(NotImplementedError):
        adapter.observe("s", "i")
    with pytest.raises(NotImplementedError):
        adapter.commit({})
    with pytest.raises(NotImplementedError):
        adapter.remaining_budget()
