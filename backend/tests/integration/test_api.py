"""HTTP contract tests for API v1."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from qalam.api.app import create_app
from qalam.api.dependencies import get_pipeline
from qalam.application.pipeline import AnalysisPipeline, PipelineComponents
from qalam.core.config import Settings
from qalam.plugins.base import PluginRegistry
from qalam.plugins.islamic_epigraphy import IslamicEpigraphyPlugin
from tests.conftest import (
    FakeDetector,
    FakeKnowledgeGraph,
    FakeOcrEngine,
    FakePreprocessor,
    FakeScriptClassifier,
    FakeTranslator,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    """A client over the real application, with all stages unavailable.

    This is the production wiring for the current milestone: no models have
    shipped, so every capability resolves to an explicitly-unavailable adapter.
    """
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def wired_client(settings: Settings) -> Iterator[TestClient]:
    """A client whose pipeline is overridden with working doubles."""
    app = create_app(settings)
    working = AnalysisPipeline(
        components=PipelineComponents(
            preprocessor=FakePreprocessor(),
            detector=FakeDetector(),
            script_classifier=FakeScriptClassifier(),
            ocr=FakeOcrEngine(),
            translator=FakeTranslator(),
            knowledge_graph=FakeKnowledgeGraph(),
        ),
        plugins=PluginRegistry((IslamicEpigraphyPlugin(),)),
        settings=settings,
    )
    app.dependency_overrides[get_pipeline] = lambda: working
    with TestClient(app) as test_client:
        yield test_client


class TestHealth:
    def test_liveness_does_not_depend_on_models(self, client: TestClient) -> None:
        """Must stay 200 even with every capability unavailable."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestReadiness:
    def test_reports_not_ready_when_capabilities_are_missing(self, client: TestClient) -> None:
        response = client.get("/api/v1/readiness")
        assert response.status_code == 200
        body = response.json()
        assert body["ready"] is False
        assert body["environment"] == "test"

    def test_names_every_missing_capability_with_a_reason(self, client: TestClient) -> None:
        """An operator must be able to see exactly what to fix."""
        body = client.get("/api/v1/readiness").json()
        names = {capability["name"] for capability in body["capabilities"]}
        assert {"ocr", "detector", "translator", "knowledge_graph"} <= names
        for capability in body["capabilities"]:
            assert capability["available"] is False
            assert capability["reason"]
            assert "scheduled" in capability["reason"]


class TestCivilizations:
    def test_lists_registered_plugins(self, client: TestClient) -> None:
        body = client.get("/api/v1/civilizations").json()
        assert len(body) == 1
        assert body[0]["id"] == "islamic_epigraphy"
        assert "arabic" in body[0]["supported_scripts"]


class TestAnalyzeWithoutModels:
    def test_returns_503_rather_than_a_fabricated_reading(self, client: TestClient) -> None:
        """The regression that matters most: no invented inscription text."""
        response = client.post("/api/v1/analyze", json={"image_url": "file://sample.jpg"})
        assert response.status_code == 503
        body = response.json()
        assert body["code"] == "capability_unavailable"
        assert "inscription_text" not in body
        assert "ocr" in body["details"]["capability"]

    def test_error_body_explains_which_stages_are_missing(self, client: TestClient) -> None:
        body = client.post("/api/v1/analyze", json={"image_url": "file://x.jpg"}).json()
        assert "ocr" in body["details"]["reason"]


class TestAnalyzeWithModels:
    def test_returns_a_reading_and_evidence_backed_claims(self, wired_client: TestClient) -> None:
        response = wired_client.post("/api/v1/analyze", json={"image_url": "file://sample.jpg"})
        assert response.status_code == 200
        body = response.json()
        assert body["ocr"]["text"]
        assert body["translation"]["target_language"] == "en"
        assert body["claims"]
        for claim in body["claims"]:
            assert claim["evidence"], "a claim without evidence must never reach the wire"

    def test_tourist_mode_omits_stage_diagnostics(self, wired_client: TestClient) -> None:
        body = wired_client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "mode": "tourist"}
        ).json()
        assert body["stages"] is None

    def test_developer_mode_includes_stage_diagnostics(self, wired_client: TestClient) -> None:
        body = wired_client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "mode": "developer"}
        ).json()
        assert body["stages"]
        assert {stage["name"] for stage in body["stages"]} >= {"ocr", "detect"}

    def test_unknown_civilization_returns_404_with_available_options(
        self, wired_client: TestClient
    ) -> None:
        response = wired_client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "civilization": "atlantean"}
        )
        assert response.status_code == 404
        assert response.json()["details"]["available"] == ["islamic_epigraphy"]


class TestRequestValidation:
    def test_rejects_a_missing_image_url(self, client: TestClient) -> None:
        assert client.post("/api/v1/analyze", json={}).status_code == 422

    def test_rejects_unknown_fields(self, client: TestClient) -> None:
        """``extra=forbid`` catches client typos instead of silently ignoring them."""
        response = client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "mdoe": "tourist"}
        )
        assert response.status_code == 422

    def test_rejects_a_malformed_sha256(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "sha256": "not-a-hash"}
        )
        assert response.status_code == 422

    def test_rejects_an_unknown_mode(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/analyze", json={"image_url": "file://x.jpg", "mode": "archaeologist"}
        )
        assert response.status_code == 422


class TestOpenApi:
    def test_schema_is_generated(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        paths = response.json()["paths"]
        assert {"/api/v1/analyze", "/api/v1/health", "/api/v1/readiness"} <= set(paths)
