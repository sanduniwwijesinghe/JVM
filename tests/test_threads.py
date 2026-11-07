from jvm_diagnostics.analyzers.thread_analyzer import ThreadAnalyzer
from jvm_diagnostics.models.evidence import IssueSeverity
from jvm_diagnostics.parsers.thread_dump_parser import ThreadDumpParser


def test_parser_reads_threads_and_states(contention_dump):
    parser = ThreadDumpParser()
    threads = parser.parse_file(str(contention_dump))
    assert len(threads) == 15
    dist = parser.get_thread_state_distribution()
    assert dist["BLOCKED"] == 6
    assert dist["RUNNABLE"] == 7


def test_parser_reads_locks(contention_dump):
    parser = ThreadDumpParser()
    parser.parse_file(str(contention_dump))
    t2 = parser.find_thread_by_name("Thread-2")
    assert t2.waiting_on_lock.lock_id == "0x00000000d5e7e9b0"
    assert "0x00000000d5e7e8a8" in [lock.lock_id for lock in t2.holding_locks]


def test_deadlock_detected_with_both_threads(deadlock_dump):
    evidence = ThreadAnalyzer().analyze_thread_dump(str(deadlock_dump))
    assert evidence.has_deadlock
    assert evidence.severity == IssueSeverity.CRITICAL
    (cycle,) = evidence.deadlocks
    assert {t.name for t in cycle.threads} == {"order-worker-1", "stock-sync-1"}


def test_no_false_deadlock_on_lock_chain(contention_dump):
    # Thread-1 -> Thread-2 -> Thread-3 is a chain, not a cycle
    evidence = ThreadAnalyzer().analyze_thread_dump(str(contention_dump))
    assert not evidence.has_deadlock


def test_contention_at_threshold_is_reported(contention_dump):
    evidence = ThreadAnalyzer({"contention_threshold": 5}).analyze_thread_dump(
        str(contention_dump)
    )
    (hotspot,) = evidence.contention_hotspots
    assert hotspot.contention_count == 5
    assert hotspot.holder_thread.name == "Thread-2"
    issues = [i for i in evidence.detected_issues if i.startswith("Lock contention")]
    assert issues and "held by 'Thread-2'" in issues[0]


def test_contention_below_threshold_ignored(contention_dump):
    evidence = ThreadAnalyzer({"contention_threshold": 6}).analyze_thread_dump(
        str(contention_dump)
    )
    assert evidence.contention_hotspots == []
