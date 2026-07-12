from unittest.mock import MagicMock, patch

from src.services.progress_health import (
    ProgressHealthMonitor,
    ProgressHealthReport,
    ProgressHealthSample,
    ProgressHealthService,
)


def sample(
    *,
    drop_id: str = "drop-1",
    confirmed: int = 10,
    estimated: int = 10,
    watch_succeeded: bool = True,
) -> ProgressHealthSample:
    return ProgressHealthSample(
        channel_id=123,
        channel_name="example_channel",
        drop_id=drop_id,
        drop_name="Example Drop",
        confirmed_minutes=confirmed,
        estimated_minutes=estimated,
        required_minutes=30,
        watch_succeeded=watch_succeeded,
        gql_status="unchanged",
    )


def test_reports_stall_repeats_to_file_interval_and_recovers():
    monitor = ProgressHealthMonitor()

    assert monitor.observe(sample(), now=0) is None
    assert monitor.observe(sample(estimated=14), now=299) is None

    warning = monitor.observe(sample(estimated=15), now=300)
    assert warning is not None
    assert warning.status == "warning"
    assert warning.kind == "progress_stalled"
    assert warning.alert_id == "PH-001"
    assert warning.repeated is False

    assert monitor.observe(sample(estimated=20), now=899) is None
    repeated = monitor.observe(sample(estimated=20), now=900)
    assert repeated is not None
    assert repeated.alert_id == "PH-001"
    assert repeated.repeated is True

    recovered = monitor.observe(sample(confirmed=11, estimated=11), now=901)
    assert recovered is not None
    assert recovered.status == "recovered"
    assert recovered.reason == "confirmed_progress"


def test_reports_consecutive_watch_failures_and_clears_on_success():
    monitor = ProgressHealthMonitor()

    assert monitor.observe(sample(watch_succeeded=False), now=0) is None
    assert monitor.observe(sample(watch_succeeded=False), now=59) is None
    warning = monitor.observe(sample(watch_succeeded=False), now=118)

    assert warning is not None
    assert warning.kind == "watch_delivery_failed"
    assert warning.consecutive_send_failures == 3

    recovered = monitor.observe(sample(watch_succeeded=True), now=177)
    assert recovered is not None
    assert recovered.status == "recovered"
    assert recovered.reason == "watch_delivery_resumed"


def test_target_change_clears_existing_warning_and_starts_a_new_baseline():
    monitor = ProgressHealthMonitor(stall_after_seconds=60)
    assert monitor.observe(sample(), now=0) is None
    assert monitor.observe(sample(), now=60) is not None

    cleared = monitor.observe(sample(drop_id="drop-2", confirmed=0), now=61)
    assert cleared is not None
    assert cleared.status == "cleared"
    assert cleared.reason == "target_changed"

    assert monitor.observe(sample(drop_id="drop-2", confirmed=0), now=120) is None


def test_web_console_gets_summary_while_logger_gets_diagnostics():
    twitch = MagicMock()
    service = ProgressHealthService(twitch)
    report = ProgressHealthReport(
        status="warning",
        alert_id="PH-001",
        kind="progress_stalled",
        sample=sample(estimated=15),
        stalled_seconds=300,
        consecutive_send_failures=0,
    )

    with patch("src.services.progress_health.logger.warning") as warning_log:
        service.report(report)

    twitch.print.assert_called_once_with(
        "[PH-001] Progress may be stalled: no confirmed increase for 5 min"
    )
    web_message = twitch.print.call_args.args[0]
    assert "example_channel" not in web_message
    assert "Example Drop" not in web_message
    warning_log.assert_called_once()
    assert "channel=%r" in warning_log.call_args.args[0]
    assert "drop=%r" in warning_log.call_args.args[0]
