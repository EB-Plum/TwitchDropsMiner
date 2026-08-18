"""State machine for detecting unconfirmed drop progress."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING, Literal


if TYPE_CHECKING:
    from src.core.client import Twitch
    from src.models.channel import Channel


logger = logging.getLogger("TwitchDrops")


AlertKind = Literal["progress_stalled", "watch_delivery_failed"]
ReportStatus = Literal["warning", "recovered", "cleared"]


@dataclass(frozen=True)
class ProgressHealthSample:
    channel_id: int
    channel_name: str
    drop_id: str
    drop_name: str
    confirmed_minutes: int
    estimated_minutes: int
    required_minutes: int
    watch_succeeded: bool
    gql_status: str

    @property
    def target(self) -> tuple[int, str]:
        return (self.channel_id, self.drop_id)


@dataclass(frozen=True)
class ProgressHealthReport:
    status: ReportStatus
    alert_id: str
    kind: AlertKind
    sample: ProgressHealthSample | None
    stalled_seconds: int
    consecutive_send_failures: int
    repeated: bool = False
    reason: str = ""


class ProgressHealthMonitor:
    """Detect stalled confirmed progress without treating estimates as proof."""

    def __init__(
        self,
        *,
        stall_after_seconds: int = 5 * 60,
        send_failure_threshold: int = 3,
        repeat_after_seconds: int = 10 * 60,
    ) -> None:
        self._stall_after_seconds = stall_after_seconds
        self._send_failure_threshold = send_failure_threshold
        self._repeat_after_seconds = repeat_after_seconds
        self._sequence = 0
        self._target: tuple[int, str] | None = None
        self._confirmed_minutes = 0
        self._last_confirmed_at = 0.0
        self._consecutive_send_failures = 0
        self._last_sample: ProgressHealthSample | None = None
        self._active_alert_id: str | None = None
        self._active_kind: AlertKind | None = None
        self._last_reported_at = 0.0

    def _next_alert_id(self) -> str:
        self._sequence += 1
        return f"PH-{self._sequence:03d}"

    def _stalled_seconds(self, now: float) -> int:
        return max(0, int(now - self._last_confirmed_at))

    def _finish_active_alert(
        self,
        *,
        status: Literal["recovered", "cleared"],
        now: float,
        sample: ProgressHealthSample | None,
        reason: str,
    ) -> ProgressHealthReport | None:
        if self._active_alert_id is None or self._active_kind is None:
            return None
        report = ProgressHealthReport(
            status=status,
            alert_id=self._active_alert_id,
            kind=self._active_kind,
            sample=sample,
            stalled_seconds=self._stalled_seconds(now),
            consecutive_send_failures=self._consecutive_send_failures,
            reason=reason,
        )
        self._active_alert_id = None
        self._active_kind = None
        self._last_reported_at = 0.0
        return report

    def reset(self, *, now: float, reason: str) -> ProgressHealthReport | None:
        report = self._finish_active_alert(
            status="cleared",
            now=now,
            sample=self._last_sample,
            reason=reason,
        )
        self._target = None
        self._confirmed_minutes = 0
        self._last_confirmed_at = 0.0
        self._consecutive_send_failures = 0
        self._last_sample = None
        return report

    def _initialize_target(self, sample: ProgressHealthSample, now: float) -> None:
        self._target = sample.target
        self._confirmed_minutes = sample.confirmed_minutes
        self._last_confirmed_at = now
        self._consecutive_send_failures = 0 if sample.watch_succeeded else 1
        self._last_sample = sample

    def observe(self, sample: ProgressHealthSample, *, now: float) -> ProgressHealthReport | None:
        if sample.target != self._target:
            report = self.reset(now=now, reason="target_changed")
            self._initialize_target(sample, now)
            return report

        self._last_sample = sample
        if sample.watch_succeeded:
            self._consecutive_send_failures = 0
        else:
            self._consecutive_send_failures += 1

        if sample.confirmed_minutes != self._confirmed_minutes:
            advanced = sample.confirmed_minutes > self._confirmed_minutes
            self._confirmed_minutes = sample.confirmed_minutes
            self._last_confirmed_at = now
            self._consecutive_send_failures = 0
            return self._finish_active_alert(
                status="recovered" if advanced else "cleared",
                now=now,
                sample=sample,
                reason="confirmed_progress" if advanced else "confirmed_progress_reset",
            )

        stalled_seconds = self._stalled_seconds(now)
        kind: AlertKind | None = None
        if self._consecutive_send_failures >= self._send_failure_threshold:
            kind = "watch_delivery_failed"
        elif stalled_seconds >= self._stall_after_seconds:
            kind = "progress_stalled"

        if kind is None:
            return self._finish_active_alert(
                status="recovered",
                now=now,
                sample=sample,
                reason="watch_delivery_resumed",
            )

        if self._active_alert_id is None:
            self._active_alert_id = self._next_alert_id()
            self._active_kind = kind
            self._last_reported_at = now
            return ProgressHealthReport(
                status="warning",
                alert_id=self._active_alert_id,
                kind=kind,
                sample=sample,
                stalled_seconds=stalled_seconds,
                consecutive_send_failures=self._consecutive_send_failures,
            )

        kind_changed = kind != self._active_kind
        repeat_due = now - self._last_reported_at >= self._repeat_after_seconds
        if not kind_changed and not repeat_due:
            return None

        self._active_kind = kind
        self._last_reported_at = now
        return ProgressHealthReport(
            status="warning",
            alert_id=self._active_alert_id,
            kind=kind,
            sample=sample,
            stalled_seconds=stalled_seconds,
            consecutive_send_failures=self._consecutive_send_failures,
            repeated=not kind_changed,
        )


class ProgressHealthService:
    """Connect progress health detection to logs and the web GUI."""

    def __init__(
        self, twitch: Twitch, monitor: ProgressHealthMonitor | None = None
    ) -> None:
        self._twitch = twitch
        self._monitor = monitor or ProgressHealthMonitor()

    @staticmethod
    def _message(report: ProgressHealthReport) -> str:
        if report.kind == "watch_delivery_failed":
            return (
                "Watch delivery may be failing: "
                f"{report.consecutive_send_failures} consecutive requests failed"
            )
        stalled_minutes = max(1, report.stalled_seconds // 60)
        return (
            "Progress may be stalled: "
            f"no confirmed increase for {stalled_minutes} min"
        )

    def report(self, report: ProgressHealthReport | None) -> None:
        if report is None:
            return

        if report.status == "warning":
            message = self._message(report)
            sample = report.sample
            if sample is not None:
                logger.warning(
                    "progress_health status=warning event_id=%s kind=%s channel=%r "
                    "drop=%r confirmed=%s/%s estimated=%s/%s stalled_seconds=%s "
                    "watch_succeeded=%s consecutive_send_failures=%s gql_status=%s repeated=%s",
                    report.alert_id,
                    report.kind,
                    sample.channel_name,
                    sample.drop_name,
                    sample.confirmed_minutes,
                    sample.required_minutes,
                    sample.estimated_minutes,
                    sample.required_minutes,
                    report.stalled_seconds,
                    sample.watch_succeeded,
                    report.consecutive_send_failures,
                    sample.gql_status,
                    report.repeated,
                )
            self._twitch.gui.progress.set_health_warning(
                {
                    "id": report.alert_id,
                    "kind": report.kind,
                    "message": message,
                }
            )
            if not report.repeated:
                self._twitch.print(f"[{report.alert_id}] {message}")
            return

        self._twitch.gui.progress.clear_health_warning()
        logger.info(
            "progress_health status=%s event_id=%s kind=%s reason=%s",
            report.status,
            report.alert_id,
            report.kind,
            report.reason,
        )
        if report.status == "recovered":
            self._twitch.print(f"[{report.alert_id}] Progress health recovered")

    def reset(self, reason: str) -> None:
        self.report(self._monitor.reset(now=monotonic(), reason=reason))

    def observe(
        self, channel: Channel, *, watch_succeeded: bool, gql_status: str
    ) -> None:
        active_campaign = self._twitch._inventory_service.get_active_campaign(channel)
        active_drop = active_campaign.first_drop if active_campaign is not None else None
        if active_drop is None:
            self.reset("no_active_drop")
            return

        sample = ProgressHealthSample(
            channel_id=channel.id,
            channel_name=channel.name,
            drop_id=active_drop.id,
            drop_name=active_drop.name,
            confirmed_minutes=active_drop.real_current_minutes,
            estimated_minutes=active_drop.current_minutes,
            required_minutes=active_drop.required_minutes,
            watch_succeeded=watch_succeeded,
            gql_status=gql_status,
        )
        self.report(self._monitor.observe(sample, now=monotonic()))
