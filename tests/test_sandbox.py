import pytest


def test_missing_docker_fails_closed_without_host_execution(monkeypatch):
    from ai_dlc.sandbox import test_provider

    monkeypatch.setattr("ai_dlc.sandbox.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError, match="unavailable"):
        test_provider("linear", {"image": "example@sha256:" + "a" * 64})


def test_unpinned_image_and_missing_live_credentials_rejected():
    from ai_dlc.sandbox import validate_test_manifest

    with pytest.raises(ValueError, match="digest"):
        validate_test_manifest({"image": "python:latest"})
    with pytest.raises(ValueError, match="sandbox"):
        validate_test_manifest({"image": "example@sha256:" + "a" * 64}, live=True)


def test_proxy_rejects_ip_private_dns_and_undeclared_hosts():
    from ai_dlc.test_proxy import allowed_destination

    assert not allowed_destination("evil.test", 443, {"api.linear.app"}, lambda h: ["1.1.1.1"])
    assert not allowed_destination(
        "api.linear.app", 443, {"api.linear.app"}, lambda h: ["127.0.0.1"]
    )
    assert not allowed_destination("api.linear.app", 80, {"api.linear.app"}, lambda h: ["1.1.1.1"])
    assert allowed_destination("api.linear.app", 443, {"api.linear.app"}, lambda h: ["1.1.1.1"])
