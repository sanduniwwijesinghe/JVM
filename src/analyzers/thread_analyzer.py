"""
Thread analyzer for JVM diagnostic analysis.

Orchestrates thread dump parsing, deadlock detection, and contention analysis.
"""

from typing import List, Dict, Optional
from ..models.evidence import (
    DiagnosticEvidence, ThreadInfo, ThreadState, IssueSeverity
)
from ..parsers.thread_dump_parser import ThreadDumpParser
from ..detectors.deadlock_detector import DeadlockDetector
from ..detectors.contention_detector import ContentionDetector


class ThreadAnalyzer:
    """
    High-level analyzer for thread dump analysis.

    Coordinates parsing, deadlock detection, contention analysis,
    and evidence extraction.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize thread analyzer.

        Args:
            config: Configuration dict with thresholds:
                - blocked_threshold: Alert if >N BLOCKED threads
                - runnable_threshold: Alert if >N RUNNABLE threads
                - contention_threshold: Alert if >N threads on same lock
        """
        self.config = config or {}
        self.blocked_threshold = self.config.get('blocked_threshold', 10)
        self.runnable_threshold = self.config.get('runnable_threshold', 50)
        self.contention_threshold = self.config.get('contention_threshold', 5)

        self.parser = ThreadDumpParser()
        self.threads: List[ThreadInfo] = []
        self.evidence = DiagnosticEvidence()

    def analyze_thread_dump(self, file_path: str) -> DiagnosticEvidence:
        """
        Analyze a thread dump file and return diagnostic evidence.

        Args:
            file_path: Path to thread dump file

        Returns:
            DiagnosticEvidence object with analysis results
        """
        # Parse thread dump
        self.threads = self.parser.parse_file(file_path)

        # Initialize evidence
        self.evidence = DiagnosticEvidence()
        self.evidence.source_files['thread_dump'] = file_path
        self.evidence.threads = self.threads
        self.evidence.total_threads = len(self.threads)

        # Get thread state distribution
        self.evidence.thread_state_distribution = self.parser.get_thread_state_distribution()

        # Detect issues
        self._detect_deadlocks()
        self._detect_contention()
        self._analyze_runnable_threads()
        self._check_thread_exhaustion()

        return self.evidence

    def _detect_deadlocks(self):
        """Detect deadlocks and add to evidence."""
        detector = DeadlockDetector(self.threads)
        deadlocks = detector.detect_deadlocks()

        if deadlocks:
            self.evidence.deadlocks = deadlocks
            self.evidence.has_deadlock = True

            for deadlock in deadlocks:
                issue = f"Deadlock detected involving {deadlock.get_cycle_size()} threads"
                self.evidence.add_issue(issue, IssueSeverity.CRITICAL)

            # Add signal
            self.evidence.signals['deadlock_details'] = [
                {
                    'cycle_size': dl.get_cycle_size(),
                    'threads': [t.name for t in dl.threads],
                    'description': dl.cycle_description
                }
                for dl in deadlocks
            ]

    def _detect_contention(self):
        """Detect lock contention and add to evidence."""
        detector = ContentionDetector(self.threads, threshold=self.contention_threshold)
        hotspots = detector.detect_contention_hotspots()

        if hotspots:
            self.evidence.contention_hotspots = hotspots

            # Check for high contention
            high_contention_hotspots = [
                h for h in hotspots
                if h.get_severity() in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]
            ]

            if high_contention_hotspots:
                self.evidence.high_contention = True

                for hotspot in high_contention_hotspots[:3]:  # Top 3
                    issue = (
                        f"High lock contention: {hotspot.contention_count} threads "
                        f"blocked on {hotspot.lock_info.lock_class}"
                    )
                    self.evidence.add_issue(issue, hotspot.get_severity())

            # Add contention signals
            self.evidence.signals['contention_hotspots'] = [
                {
                    'lock_class': h.lock_info.lock_class,
                    'blocked_count': h.contention_count,
                    'severity': h.get_severity().value,
                    'holder': h.holder_thread.name if h.holder_thread else None
                }
                for h in hotspots[:5]
            ]

            # Analyze thread pools
            pool_stats = detector.get_thread_pool_stats()
            if pool_stats:
                self.evidence.signals['thread_pool_stats'] = pool_stats

                # Check for thread pool exhaustion
                for pool_name, stats in pool_stats.items():
                    if stats['utilization'] > 0.9 and stats['total'] > 10:
                        issue = f"Thread pool '{pool_name}' at {stats['utilization']:.0%} utilization"
                        self.evidence.add_issue(issue, IssueSeverity.HIGH)

    def _analyze_runnable_threads(self):
        """Analyze RUNNABLE threads for CPU-bound hotspots."""
        runnable_threads = self.parser.get_threads_by_state(ThreadState.RUNNABLE)
        self.evidence.runnable_threads = runnable_threads

        # Check threshold
        if len(runnable_threads) > self.runnable_threshold:
            issue = f"High number of RUNNABLE threads: {len(runnable_threads)}"
            self.evidence.add_issue(issue, IssueSeverity.MEDIUM)

        # Find common stack patterns in runnable threads
        detector = ContentionDetector(self.threads)
        hotspot_patterns = detector.find_runnable_hotspots()

        if hotspot_patterns:
            self.evidence.runnable_hotspots = list(hotspot_patterns.keys())
            self.evidence.signals['runnable_hotspots'] = hotspot_patterns

            # Report top CPU-bound methods
            sorted_patterns = sorted(
                hotspot_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for method, count in sorted_patterns[:3]:
                if count >= 5:
                    issue = f"CPU-bound hotspot: {count} threads in {method}"
                    self.evidence.add_issue(issue, IssueSeverity.MEDIUM)

    def _check_thread_exhaustion(self):
        """Check for thread exhaustion signals."""
        blocked_count = self.evidence.get_blocked_thread_count()
        waiting_count = self.evidence.get_waiting_thread_count()

        # Check blocked threads
        if blocked_count > self.blocked_threshold:
            issue = f"High number of BLOCKED threads: {blocked_count}"
            severity = (
                IssueSeverity.CRITICAL if blocked_count > self.blocked_threshold * 2
                else IssueSeverity.HIGH
            )
            self.evidence.add_issue(issue, severity)

        # Check if most threads are waiting (possible thread pool exhaustion)
        total = self.evidence.total_threads
        if total > 0:
            waiting_ratio = waiting_count / total
            if waiting_ratio > 0.7 and total > 20:
                issue = f"High thread waiting ratio: {waiting_ratio:.0%} ({waiting_count}/{total})"
                self.evidence.add_issue(issue, IssueSeverity.MEDIUM)

            # Add thread state summary
            self.evidence.signals['thread_state_summary'] = {
                'total': total,
                'blocked': blocked_count,
                'waiting': waiting_count,
                'runnable': len(self.evidence.runnable_threads),
                'blocked_ratio': blocked_count / total if total > 0 else 0,
                'waiting_ratio': waiting_ratio,
            }

    def get_thread_by_name(self, name: str) -> Optional[ThreadInfo]:
        """Find a thread by name."""
        return self.parser.find_thread_by_name(name)

    def get_threads_by_state(self, state: ThreadState) -> List[ThreadInfo]:
        """Get all threads in a specific state."""
        return self.parser.get_threads_by_state(state)

    def format_thread_summary(self) -> str:
        """Format a summary of thread analysis."""
        lines = []
        lines.append("Thread Dump Analysis Summary")
        lines.append("=" * 50)
        lines.append(f"Total threads: {self.evidence.total_threads}")
        lines.append("")

        lines.append("Thread State Distribution:")
        for state, count in sorted(
            self.evidence.thread_state_distribution.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / self.evidence.total_threads * 100) if self.evidence.total_threads > 0 else 0
            lines.append(f"  {state:20s}: {count:4d} ({percentage:5.1f}%)")

        lines.append("")
        lines.append(f"Issues Detected: {len(self.evidence.detected_issues)}")
        for issue in self.evidence.detected_issues:
            lines.append(f"  - {issue}")

        return "\n".join(lines)
