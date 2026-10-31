"""Public-adapter boundaries. All documents are disposable synthetic fixtures."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

import app as public_app
from web_demo import service, worker


@pytest.fixture
def client():
    application = public_app.create_app()
    application.config["TESTING"] = True
    return application.test_client()


def sample_request(client, sample="pdf", **fields):
    return client.post("/api/process", data={"sample": sample, **fields}, content_type="multipart/form-data")


@pytest.mark.parametrize("sample", ["pdf", "docx"])
def test_samples_execute_real_original_extraction_in_subprocess(client, sample):
    response = sample_request(client, sample)
    assert response.status_code == 200
    result = response.get_json()
    assert result["document"]["type"] == sample
    assert "plateforme web" in result["document"]["text"]
    assert len(result["document"]["sha256"]) == 64
    assert result["classification"] == "dossier_de_fond"
    assert result["relevance"]["score"] == 15
    assert result["processing"]["ai"] is False
    assert result["relevance"]["ranking_only"] is True
    assert result["sources"][0]["quote"]
    assert "fictif" in result["warnings"][0]
    if sample == "pdf":
        assert result["document"]["pages"] == 1
        assert result["sources"][0]["page"] == 1
        assert "--- PAGE 1 ---" in result["document"]["text"]
    else:
        assert result["document"]["pages"] is None
        assert "Extraction native des tableaux" in result["document"]["text"]
    assert response.headers["Cache-Control"] == "no-store"


def test_isolated_worker_bootstraps_vendor_only_dependencies(monkeypatch):
    original_popen = service.subprocess.Popen
    calls = []

    def without_automatic_site_packages(command, **kwargs):
        # -S simulates a runtime whose dependencies exist only in an explicitly
        # vendored root, not the interpreter's ordinary site-packages.
        calls.append(command)
        return original_popen([*command[:1], "-S", *command[1:]], **kwargs)

    monkeypatch.setattr(service.subprocess, "Popen", without_automatic_site_packages)
    result = service.process_document(sample="pdf")
    assert "plateforme web" in result["document"]["text"]
    assert "--dependency-root" in calls[0]
    assert "-I" in calls[0]


def test_keywords_change_real_relevance_not_document(client):
    first = sample_request(client, keywords=json.dumps(["logiciel"])) .get_json()
    second = sample_request(client, keywords=json.dumps(["astronomie"])).get_json()
    assert first["document"] == second["document"]
    assert first["relevance"]["score"] == 3
    assert second["relevance"]["score"] == 0
    assert first["relevance"]["reasons"] == ["+ logiciel"]


def test_uploads_fail_closed_without_linux_resource_limits(client, monkeypatch):
    monkeypatch.setattr(service, "resource_limits_supported", lambda: False)
    response = client.post("/api/process", data={"file": (io.BytesIO(worker.synthetic_pdf()), "test.pdf")})
    assert response.status_code == 503
    assert response.get_json()["error"] == "uploads_unavailable"
    assert client.get("/api/capabilities").get_json()["uploads_enabled"] is False


def test_large_valid_multipart_file_reaches_dispatch_without_form_buffer_false_positive(client, monkeypatch):
    monkeypatch.setattr(service, "process_document", lambda **values: {"received": len(values["body"])})
    response = client.post("/api/process", data={"file": (io.BytesIO(b"%PDF-" + b"x" * 200_000), "test.pdf")})
    assert response.status_code == 200
    assert response.get_json()["received"] == 200_005


def test_upload_size_rejected_before_parser_runs(client, monkeypatch):
    monkeypatch.setattr(service, "resource_limits_supported", lambda: True)
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("parser must not start"))
    response = client.post("/api/process", data={"file": (io.BytesIO(b"x" * (service.MAX_FILE_BYTES + 1)), "test.pdf")})
    assert response.status_code == 413


@pytest.mark.parametrize("fields", [
    {}, {"sample": "../../sources/private.pdf"}, {"sample": "pdf", "url": "https://example.test/secret"},
    {"sample": "pdf", "keywords": "[\"<script>\"]"}, {"sample": "pdf", "keywords": "{}"},
    {"sample": "pdf", "keywords": json.dumps(["word"] * 13)},
    {"sample": "pdf", "keywords": json.dumps(["x" * 41])},
])
def test_invalid_inputs_never_start_a_parser(client, monkeypatch, fields):
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("parser must not start"))
    assert client.post("/api/process", data=fields, content_type="multipart/form-data").status_code == 400


@pytest.mark.parametrize("filename,mimetype", [
    ("../private.pdf", "application/pdf"), ("C:\\private.pdf", "application/pdf"),
    ("sample.doc", "application/msword"), ("sample.pdf", "image/png"),
    ("sample.pdf\x01", "application/pdf"), ("sample.exe", "application/octet-stream"),
])
def test_upload_name_and_mime_boundary(client, monkeypatch, filename, mimetype):
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("parser must not start"))
    response = client.post("/api/process", data={"file": (io.BytesIO(b"dummy"), filename, mimetype)})
    assert response.status_code in {400, 415}


def test_mutually_exclusive_and_duplicate_fields(client, monkeypatch):
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("parser must not start"))
    assert client.post("/api/process", data={"sample": "pdf", "file": (io.BytesIO(b"dummy"), "x.pdf")}).status_code == 400
    fields = MultiDict([("sample", "pdf"), ("sample", "docx")])
    assert client.post("/api/process", data=fields, content_type="multipart/form-data").status_code == 400


@pytest.mark.parametrize("headers", [
    {"Origin": "https://foreign.example"}, {"Origin": "null"},
    {"Sec-Fetch-Site": "cross-site"}, {"Origin": "http://["},
])
def test_foreign_origin_denied_before_processing(client, headers):
    response = client.post("/api/decision", json={"secret": "must not appear"}, headers=headers)
    assert response.status_code == 403
    assert "must not appear" not in response.get_data(as_text=True)


def test_vercel_https_origin_accepted_behind_http_transport(client, monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    response = client.post("/api/decision", json={"adequation": 10, "delai": 10, "administratif": 10, "risque": 10, "partial": True},
                           headers={"Origin": "https://localhost"})
    assert response.status_code == 200


def test_manual_rubric_reuses_original_thresholds_and_partial_guard(client, monkeypatch):
    from onetech_ao import analysis

    original = analysis.expected_decision
    calls = []

    def tracked(total):
        calls.append(total)
        return original(total)

    monkeypatch.setattr(analysis, "expected_decision", tracked)
    payload = {"adequation": 20, "delai": 20, "administratif": 20, "risque": 20, "partial": False}
    response = client.post("/api/decision", json=payload)
    assert response.get_json()["decision"] == "GO"
    assert response.get_json()["method"] == "manual-rubric"
    payload["partial"] = True
    assert client.post("/api/decision", json=payload).status_code == 409
    assert calls == [80, 80]


@pytest.mark.parametrize("patch", [{"adequation": True}, {"risque": 26}, {"delai": -1}, {"partial": "false"}, {"delai": 2.5}, {"extra": 1}])
def test_manual_rubric_rejects_ambiguous_scores(client, patch):
    payload = {"adequation": 10, "delai": 10, "administratif": 10, "risque": 10, "partial": True, **patch}
    assert client.post("/api/decision", json=payload).status_code == 400


def test_busy_limit_is_nonblocking_and_does_not_start_process(monkeypatch):
    slots = threading.BoundedSemaphore(2)
    slots.acquire()
    slots.acquire()
    monkeypatch.setattr(service, "WORKER_SLOTS", slots)
    monkeypatch.setattr(service.subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("parser must not start"))
    with pytest.raises(service.DemoError) as raised:
        service.process_document(sample="pdf")
    assert raised.value.status == 429


class FakeProcess:
    def __init__(self, output, stdout, *, timeout=False):
        self.returncode = None
        self.killed = False
        self.timeout = timeout
        self.reaped = False
        stdout.write(output)

    def communicate(self, _input=None, timeout=None):
        if self.timeout and not self.killed:
            raise subprocess.TimeoutExpired("private input path", timeout)
        self.returncode = 0
        self.reaped = True
        return None, None

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9


def test_timeout_kills_reaps_and_removes_temporary_upload(monkeypatch):
    calls = []
    monkeypatch.setattr(service, "resource_limits_supported", lambda: True)

    def fake_popen(command, **values):
        process = FakeProcess(b"", values["stdout"], timeout=True)
        calls.append((process, values, command))
        return process

    monkeypatch.setattr(service.subprocess, "Popen", fake_popen)
    with pytest.raises(service.DemoError) as raised:
        service.process_document(body=b"%PDF-test", name="private.pdf", document_type="pdf")
    assert raised.value.code == "processing_timeout"
    process, values, command = calls[0]
    assert process.killed and process.reaped
    assert not Path(values["cwd"]).exists()
    assert command[1:3] == ["-I", "-B"]
    assert values["stderr"] == subprocess.DEVNULL


def test_worker_does_not_receive_secret_environment(monkeypatch):
    monkeypatch.setenv("POSTGRES_PASSWORD", "disposable-test-secret")
    monkeypatch.setenv("OPENCLAW_GATEWAY_TOKEN", "disposable-test-secret")
    monkeypatch.setenv("VERCEL_BLOB_READ_WRITE_TOKEN", "disposable-test-secret")
    monkeypatch.setenv("PYTHONPATH", "untrusted-dependency-root")
    environment = service._worker_environment()
    assert not any("disposable-test-secret" in value or "untrusted-dependency-root" in value for value in environment.values())


def test_oversized_stdout_is_bounded_and_rejected(monkeypatch):
    def fake_popen(_command, **values):
        return FakeProcess(b"x" * 400_001, values["stdout"])

    monkeypatch.setattr(service.subprocess, "Popen", fake_popen)
    with pytest.raises(service.DemoError) as raised:
        service.process_document(sample="pdf")
    assert raised.value.code == "processing_failed"


def test_errors_do_not_echo_document_content_or_paths(client, monkeypatch):
    def fail(**_values):
        raise RuntimeError("PRIVATE TEXT /private/path/profile.md")

    monkeypatch.setattr(service, "process_document", fail)
    response = sample_request(client)
    assert response.status_code == 503
    assert "PRIVATE" not in response.get_data(as_text=True)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
