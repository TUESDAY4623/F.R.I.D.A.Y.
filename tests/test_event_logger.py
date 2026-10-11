"""Tests for Event Logger per Section 13."""

from jarvis.logger import EventLogger, EventType, LogEvent, LogLevel


def test_event_logger_records_structured_events():
    logger = EventLogger(console_output=False)
    event = logger.log_event(
        event_type=EventType.TASK_CREATED,
        source="intent_manager",
        message="Task initialized",
        task_id="task_123",
        payload={"query": "test query"},
    )

    assert event.task_id == "task_123"
    assert event.source == "intent_manager"
    assert event.event_type == EventType.TASK_CREATED
    assert event.payload == {"query": "test query"}

    events = logger.get_events(task_id="task_123")
    assert len(events) == 1
    assert events[0].event_id == event.event_id


def test_event_logger_redaction_guarantee():
    """Section 13 constraint: Never log passwords, API keys, tokens, or raw credentials."""
    logger = EventLogger(console_output=False)
    event = logger.log_event(
        event_type=EventType.CREDENTIAL_ACCESSED,
        source="vault",
        message="Accessing secret",
        task_id="task_sec",
        payload={
            "user": "test_user",
            "password": "super_secret_password_123",
            "api_key": "sk-proj-999999999",
            "auth_token": "bearer xyz12345",
            "nested": {
                "secret_key": "hidden",
                "normal_val": 42,
            },
        },
    )

    payload = event.payload
    assert payload["user"] == "test_user"
    assert payload["password"] == "[REDACTED]"
    assert payload["api_key"] == "[REDACTED]"
    assert payload["auth_token"] == "[REDACTED]"
    assert payload["nested"]["secret_key"] == "[REDACTED]"
    assert payload["nested"]["normal_val"] == 42
    assert event.redacted is True


def test_event_logger_live_subscriber_streaming():
    """Test live event streaming for Tanmay's UI log pane."""
    logger = EventLogger(console_output=False)
    captured = []

    def subscriber(ev: LogEvent):
        captured.append(ev)

    logger.add_subscriber(subscriber)

    logger.log_step(step_name="Step 1", task_id="t1")
    logger.log_step(step_name="Step 2", task_id="t1")

    assert len(captured) == 2
    assert captured[0].step_name == "Step 1"
    assert captured[1].step_name == "Step 2"

    logger.remove_subscriber(subscriber)
    logger.log_step(step_name="Step 3", task_id="t1")
    assert len(captured) == 2
