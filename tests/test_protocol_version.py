from app.schemas import PROTOCOL_VERSION, WSEnvelope


def test_protocol_version_constant():
    assert PROTOCOL_VERSION == "0.2.0"


def test_protocol_version_in_envelope():
    evt = WSEnvelope(
        type="assistant.delta",
        session_id="s1",
        seq=1,
        payload={"text": "x"},
    )
    assert evt.protocol_version == "0.2.0"
