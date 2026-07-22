"""Stage execution helper: timing, availability, and failure containment."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from qalam.core.logging import get_logger
from qalam.domain.entities import StageReport, StageStatus
from qalam.domain.ports import Capability

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class StageOutcome[T]:
    """The value a stage produced, paired with its diagnostic report."""

    value: T | None
    report: StageReport

    @property
    def succeeded(self) -> bool:
        return self.report.status is StageStatus.COMPLETED


async def run_stage[T](
    name: str,
    capability: Capability | None,
    action: Callable[[], Awaitable[T]],
) -> StageOutcome[T]:
    """Execute one pipeline stage, recording timing and outcome.

    Three non-success paths are distinguished, because they mean different
    things operationally:

    ``SKIPPED``
        No component is wired for this stage at all — the deployment does not
        include it by design.
    ``UNAVAILABLE``
        A component is wired but reports it cannot serve, typically missing
        model weights or an unreachable dependency. Actionable by an operator.
    ``FAILED``
        The component raised. The pipeline continues so that stages which can
        still contribute do so, and the failure is reported rather than
        masked.

    In none of these paths is a fabricated value substituted.
    """
    started = time.perf_counter()

    def elapsed_ms() -> float:
        return (time.perf_counter() - started) * 1000.0

    if capability is None:
        return StageOutcome(
            value=None,
            report=StageReport(
                name=name,
                status=StageStatus.SKIPPED,
                duration_ms=elapsed_ms(),
                detail="No component configured for this stage.",
            ),
        )

    if not capability.is_available:
        logger.warning(
            "stage.unavailable",
            stage=name,
            implementation=capability.id,
            reason=capability.availability_reason,
        )
        return StageOutcome(
            value=None,
            report=StageReport(
                name=name,
                status=StageStatus.UNAVAILABLE,
                duration_ms=elapsed_ms(),
                detail=capability.availability_reason,
                implementation_id=capability.id,
            ),
        )

    try:
        value = await action()
    except Exception as exc:  # deliberate containment boundary; logged, not swallowed
        logger.exception("stage.failed", stage=name, implementation=capability.id)
        return StageOutcome(
            value=None,
            report=StageReport(
                name=name,
                status=StageStatus.FAILED,
                duration_ms=elapsed_ms(),
                detail=f"{type(exc).__name__}: {exc}",
                implementation_id=capability.id,
            ),
        )

    duration = elapsed_ms()
    logger.info(
        "stage.completed", stage=name, implementation=capability.id, duration_ms=round(duration, 2)
    )
    return StageOutcome(
        value=value,
        report=StageReport(
            name=name,
            status=StageStatus.COMPLETED,
            duration_ms=duration,
            implementation_id=capability.id,
        ),
    )
