from __future__ import annotations

import importlib
import warnings


def test_testclient_creation_emits_no_httpx_app_deprecation_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from fastapi.testclient import TestClient

        app = importlib.import_module("main").app
        client = TestClient(app)
        response = client.get("/api/health")

    assert response.status_code == 200
    unexpected = [
        warning
        for warning in caught
        if "app" in str(warning.message).lower() and "deprecated" in str(warning.message).lower()
    ]
    assert unexpected == []
