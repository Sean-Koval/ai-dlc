"""Pure phase helpers extracted from the Docker conformance runner."""

from types import SimpleNamespace

import pytest

from ai_dlc.verification.sandbox import (
    _egress_probe,
    _firewall_rules,
    _live_env_args,
    _stage_fixtures,
    _summarize_run,
)


def test_firewall_rules_drop_everything_except_loopback_established_and_proxy():
    rules = _firewall_rules("10.9.0.2").splitlines()
    assert rules[0] == "set -eu"
    assert "iptables -P OUTPUT DROP" in rules
    assert "ip6tables -P OUTPUT DROP" in rules
    assert "iptables -A OUTPUT -p tcp -d 10.9.0.2 --dport 8080 -j ACCEPT" in rules
    assert rules[-2:] == ["touch /tmp/enforced", "exec sleep 3600"]


def test_live_env_args_route_through_proxy_and_pass_only_declared_credentials():
    manifest = {"sandbox_workspace": "team-sandbox", "credential_env": ["TOKEN_A", "TOKEN_B"]}
    args = _live_env_args(manifest, "10.9.0.2")
    assert args[:8] == [
        "--env",
        "HTTPS_PROXY=http://10.9.0.2:8080",
        "--env",
        "HTTP_PROXY=http://10.9.0.2:8080",
        "--env",
        "NO_PROXY=",
        "--env",
        "AI_DLC_SANDBOX_WORKSPACE=team-sandbox",
    ]
    # Credentials are passed by name only so the value never appears in argv.
    assert args[8:] == ["--env", "TOKEN_A", "--env", "TOKEN_B"]


def test_egress_probe_targets_proxy_and_refuses_undeclared_host():
    probe = _egress_probe("10.9.0.2")
    assert "connect_ex(('1.1.1.1',443))" in probe
    assert "create_connection(('10.9.0.2',8080),5)" in probe
    assert "CONNECT undeclared.invalid:443" in probe
    assert "\\r\\n\\r\\n" in probe


@pytest.mark.parametrize(
    ("returncode", "live", "passed", "isolation"),
    [
        (0, False, True, "network-none"),
        (3, False, False, "network-none"),
        (0, True, True, "namespace-firewall-and-allowlist-proxy"),
    ],
)
def test_summarize_run_reports_outcome_and_isolation(returncode, live, passed, isolation):
    result = SimpleNamespace(returncode=returncode, stdout="out", stderr="err")
    summary = _summarize_run("linear", result, live)
    assert list(summary) == [
        "provider",
        "passed",
        "exit_code",
        "stdout",
        "stderr",
        "live",
        "isolation",
    ]
    assert summary["provider"] == "linear"
    assert summary["passed"] is passed
    assert summary["exit_code"] == returncode
    assert summary["stdout"] == "out"
    assert summary["stderr"] == "err"
    assert summary["live"] is live
    assert summary["isolation"] == isolation


def test_stage_fixtures_copies_packaged_tree_and_ignores_missing_source(tmp_path):
    source = tmp_path / "fixtures"
    (source / "nested").mkdir(parents=True)
    (source / "nested" / "case.toml").write_text("x = 1\n")
    target = tmp_path / "target"
    target.mkdir()
    _stage_fixtures({"fixtures": str(source)}, str(target))
    assert (target / "nested" / "case.toml").read_text() == "x = 1\n"
    empty = tmp_path / "empty"
    empty.mkdir()
    _stage_fixtures({}, str(empty))
    assert list(empty.iterdir()) == []


def test_stage_fixtures_refuses_symlinks(tmp_path):
    source = tmp_path / "fixtures"
    source.mkdir()
    (source / "real.txt").write_text("ok")
    (source / "link.txt").symlink_to(source / "real.txt")
    target = tmp_path / "target"
    target.mkdir()
    with pytest.raises(ValueError, match="symlinks"):
        _stage_fixtures({"fixtures": str(source)}, str(target))
    assert list(target.iterdir()) == []
