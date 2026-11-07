import sys

import pytest

from jvm_diagnostics import cli


def run_cli(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["jvm-diag", *argv])
    cli.main()


def test_full_analysis_writes_report_and_prompt(
    monkeypatch, tmp_path, contention_dump, mat_histogram, capsys
):
    out = tmp_path / "incident_report.txt"
    run_cli(
        monkeypatch,
        "analyze",
        "--thread-dump",
        str(contention_dump),
        "--heap-summary",
        str(mat_histogram),
        "--output",
        str(out),
    )
    report = out.read_text()
    prompt = (tmp_path / "incident_copilot_prompt.txt").read_text()

    assert "JVM DIAGNOSTICS REPORT" in report
    assert "LOCK CONTENTION ANALYSIS" in report
    assert "Thread-2" in prompt


def test_deadlock_exit_summary(monkeypatch, tmp_path, deadlock_dump, capsys):
    run_cli(
        monkeypatch,
        "analyze",
        "--thread-dump",
        str(deadlock_dump),
        "--mode",
        "summary",
        "--output",
        str(tmp_path / "r.txt"),
    )
    out = capsys.readouterr().out
    assert "Severity: CRITICAL" in out
    assert "Deadlock detected involving 2 threads" in out


def test_custom_config(monkeypatch, tmp_path, contention_dump, capsys):
    cfg = tmp_path / "strict.yaml"
    cfg.write_text("thread_analysis:\n  contention_threshold: 2\n  blocked_threshold: 3\n")
    run_cli(
        monkeypatch,
        "analyze",
        "--thread-dump",
        str(contention_dump),
        "--config",
        str(cfg),
        "--mode",
        "summary",
        "--output",
        str(tmp_path / "r.txt"),
    )
    assert "High number of BLOCKED threads: 6" in capsys.readouterr().out


def test_missing_input_exits_nonzero(monkeypatch):
    with pytest.raises(SystemExit) as exc:
        run_cli(monkeypatch, "analyze")
    assert exc.value.code == 1
