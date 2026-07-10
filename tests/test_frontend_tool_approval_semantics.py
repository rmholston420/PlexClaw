from pathlib import Path


def test_tool_approval_events_are_wired_in_frontend():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "case 'tool.permission_required':" in text
    assert "case 'tool.permission_decided':" in text
    assert "sendToolDecision('approve'" in text
    assert "sendToolDecision('reject'" in text


def test_tool_permission_decided_updates_decision_ui_contract():
    text = Path("frontend/sdk-bridge-client.js").read_text()
    assert "const decision = evt.payload?.decision || 'unknown';" in text
    assert "tool-decision-section" in text
    assert "Decision</div><pre></pre>" in text
    assert "tagSearchableNode(block, `${toolName} ${decision}`);" in text
    assert "badge.textContent = 'approved';" in text
    assert "badge.textContent = 'rejected';" in text
