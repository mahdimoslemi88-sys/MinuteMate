from minutemate.events import EngineEvent, EventType, Stage, Status


def test_stage_event_payload_uses_camel_case_and_omits_none():
    event = EngineEvent(
        type=EventType.STAGE,
        stage=Stage.TRANSCRIPTION,
        status=Status.RUNNING,
        progress=0.42,
        eta_seconds=310.0,
    )

    payload = event.to_payload()

    assert payload["type"] == "stage"
    assert payload["stage"] == "transcription"
    assert payload["etaSeconds"] == 310.0
    assert "message" not in payload
    assert "kind" not in payload


def test_error_event_carries_code_and_hint():
    event = EngineEvent(type=EventType.ERROR, code="model_missing", message="x", hint="y")

    payload = event.to_payload()

    assert payload["code"] == "model_missing"
    assert payload["hint"] == "y"
