"""API v1 route definitions."""

from __future__ import annotations

from dataclasses import fields

from fastapi import APIRouter, status

from qalam.api.dependencies import ContainerDep, PipelineDep, PluginsDep
from qalam.api.v1.schemas import (
    AnalyzeRequestSchema,
    AnalyzeResponseSchema,
    CapabilityStatusSchema,
    CivilizationSchema,
    ErrorSchema,
    ReadinessSchema,
    to_response,
)
from qalam.core.errors import CapabilityUnavailableError
from qalam.domain.entities import AnalysisRequest, ImageReference

router = APIRouter(tags=["inscriptions"])

_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorSchema, "description": "Unknown civilization plugin"},
    422: {"model": ErrorSchema, "description": "Invalid request"},
    503: {"model": ErrorSchema, "description": "A required capability is unavailable"},
}


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """Report that the process is running.

    Deliberately dependency-free: a liveness probe must not fail because a
    downstream model or the knowledge graph is unreachable, or an orchestrator
    will restart a healthy process it cannot fix.
    """
    return {"status": "ok"}


@router.get("/readiness", response_model=ReadinessSchema, summary="Capability readiness")
def readiness(container: ContainerDep) -> ReadinessSchema:
    """Report which pipeline capabilities this deployment can actually serve.

    Separate from ``/health`` because "the server is up" and "the server can
    read an inscription" are different questions, and only this one tells an
    operator what is missing.
    """
    capabilities: list[CapabilityStatusSchema] = []
    for spec in fields(container.components):
        component = getattr(container.components, spec.name)
        if component is None:
            capabilities.append(
                CapabilityStatusSchema(
                    name=spec.name,
                    available=False,
                    implementation_id="none",
                    reason="No component configured for this stage.",
                )
            )
            continue
        capabilities.append(
            CapabilityStatusSchema(
                name=spec.name,
                available=component.is_available,
                implementation_id=component.id,
                reason=component.availability_reason,
            )
        )

    return ReadinessSchema(
        ready=all(capability.available for capability in capabilities),
        environment=container.settings.environment,
        version=container.settings.api_version,
        capabilities=capabilities,
    )


@router.get(
    "/civilizations",
    response_model=list[CivilizationSchema],
    summary="List supported civilizations",
)
def civilizations(plugins: PluginsDep) -> list[CivilizationSchema]:
    """Enumerate registered civilization plugins.

    Clients use this to populate selectors rather than hardcoding a list that
    goes stale the moment a new tradition ships.
    """
    return [
        CivilizationSchema(
            id=plugin.id,
            display_name=plugin.display_name,
            supported_scripts=sorted(plugin.supported_scripts),
            default_script=plugin.default_script,
            default_target_language=plugin.default_target_language,
        )
        for plugin in plugins.all()
    ]


@router.post(
    "/analyze",
    response_model=AnalyzeResponseSchema,
    status_code=status.HTTP_200_OK,
    responses=_ERROR_RESPONSES,
    summary="Analyze an inscription image",
)
async def analyze(payload: AnalyzeRequestSchema, pipeline: PipelineDep) -> AnalyzeResponseSchema:
    """Run the analysis pipeline over one image.

    Returns 200 with a partial result when some stages could not run but a
    reading was still produced. Returns 503 when no reading was produced at
    all: the endpoint's purpose is to read an inscription, and reporting
    success without one would misrepresent the outcome to every client and to
    every uptime dashboard. The response body names the missing capabilities.
    """
    request = AnalysisRequest(
        image=ImageReference(
            uri=payload.image_url,
            content_type=payload.content_type,
            sha256=payload.sha256,
        ),
        mode=payload.mode,
        civilization=payload.civilization,
        script_hint=payload.script_hint,
    )

    result = await pipeline.run(request)

    if result.ocr is None:
        missing = result.unavailable_capabilities
        raise CapabilityUnavailableError(
            "ocr",
            reason=(
                "No transcription could be produced. "
                f"Unavailable stages: {', '.join(missing) if missing else 'none reported'}."
            ),
        )

    return to_response(result, payload.mode)
