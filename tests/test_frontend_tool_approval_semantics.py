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


def test_tool_approval_ui_is_keyed_by_tool_id_not_singleton():
    text = Path("frontend/sdk-bridge-client.js").read_text()

    assert "function sendToolDecision(decision, toolId)" in text
    assert (
        "state.socket.send(JSON.stringify({ type: decision, tool_id: toolId }))"
        in text
    )

    assert (
        "const block = getOrCreateTool(evt.payload?.tool_id, "
        "evt.payload?.tool_name || 'tool');" in text
    )
    assert 'data-approve-tool="${evt.payload?.tool_id}"' in text
    assert 'data-reject-tool="${evt.payload?.tool_id}"' in text
    assert (
        'approvalSection.querySelector(`'
        '[data-approve-tool="${evt.payload?.tool_id}"]`)'
        in text
    )
    assert (
        'approvalSection.querySelector(`'
        '[data-reject-tool="${evt.payload?.tool_id}"]`)'
        in text
    )

    assert "const toolId = evt.payload?.tool_id;" in text
    assert "const block = getOrCreateTool(toolId, toolName);" in text

    assert "currentApproval" not in text
    assert "activeApproval" not in text
    assert "pendingApproval" not in text
