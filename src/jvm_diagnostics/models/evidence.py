"""
Data models for JVM diagnostic evidence.

These classes represent structured diagnostic information extracted from
JVM thread dumps and heap summaries.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from datetime import datetime


class ThreadState(Enum):
    """JVM thread states."""
    RUNNABLE = "RUNNABLE"
    BLOCKED = "BLOCKED"
    WAITING = "WAITING"
    TIMED_WAITING = "TIMED_WAITING"
    NEW = "NEW"
    TERMINATED = "TERMINATED"
    UNKNOWN = "UNKNOWN"


class IssueSeverity(Enum):
    """Severity levels for detected issues."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class LockInfo:
    """Information about a lock held or waited on by a thread."""
    lock_id: str
    lock_class: str
    holder_thread: Optional[str] = None

    def __str__(self):
        if self.holder_thread:
            return f"{self.lock_class} <{self.lock_id}> (held by {self.holder_thread})"
        return f"{self.lock_class} <{self.lock_id}>"


@dataclass
class ThreadInfo:
    """Information about a JVM thread."""
    name: str
    thread_id: str
    state: ThreadState
    stack_trace: List[str] = field(default_factory=list)
    waiting_on_lock: Optional[LockInfo] = None
    holding_locks: List[LockInfo] = field(default_factory=list)
    native: bool = False
    daemon: bool = False
    priority: int = 5

    def get_top_stack_frames(self, limit: int = 10) -> List[str]:
        """Get the top N stack frames."""
        return self.stack_trace[:limit]

    def is_blocked_or_waiting(self) -> bool:
        """Check if thread is blocked or waiting."""
        return self.state in [ThreadState.BLOCKED, ThreadState.WAITING, ThreadState.TIMED_WAITING]

    def __str__(self):
        return f'"{self.name}" tid={self.thread_id} {self.state.value}'


@dataclass
class DeadlockCycle:
    """Represents a deadlock cycle between threads."""
    threads: List[ThreadInfo]
    lock_chain: List[LockInfo]
    cycle_description: str = ""

    def __post_init__(self):
        if not self.cycle_description:
            self.cycle_description = self._generate_description()

    def _generate_description(self) -> str:
        """Generate human-readable deadlock description."""
        if len(self.threads) < 2:
            return "Invalid deadlock cycle"

        parts = []
        for i, thread in enumerate(self.threads):
            next_idx = (i + 1) % len(self.threads)
            next_thread = self.threads[next_idx]

            held_lock = self.lock_chain[i] if i < len(self.lock_chain) else None
            waiting_lock = thread.waiting_on_lock

            if held_lock and waiting_lock:
                parts.append(
                    f"{thread.name} holds {held_lock.lock_class}, "
                    f"waiting for {waiting_lock.lock_class} (held by {next_thread.name})"
                )

        return " → ".join(parts)

    def get_cycle_size(self) -> int:
        """Return the number of threads in the deadlock."""
        return len(self.threads)


@dataclass
class ContentionHotspot:
    """Represents a lock contention hotspot."""
    lock_info: LockInfo
    blocked_threads: List[ThreadInfo]
    contention_count: int
    holder_thread: Optional[ThreadInfo] = None

    def get_severity(self) -> IssueSeverity:
        """Calculate severity based on contention count."""
        if self.contention_count >= 20:
            return IssueSeverity.CRITICAL
        elif self.contention_count >= 10:
            return IssueSeverity.HIGH
        elif self.contention_count >= 5:
            return IssueSeverity.MEDIUM
        else:
            return IssueSeverity.LOW

    def __str__(self):
        return f"{self.lock_info.lock_class} - {self.contention_count} threads blocked"


@dataclass
class HeapClassInfo:
    """Information about a class in the heap."""
    class_name: str
    instance_count: int
    shallow_heap: int  # bytes
    retained_heap: Optional[int] = None  # bytes, if available
    percentage: Optional[float] = None  # percentage of total heap

    def is_dominant(self, threshold: float = 0.3) -> bool:
        """Check if this class dominates heap usage."""
        return self.percentage is not None and self.percentage > threshold

    def format_size(self, size_bytes: int) -> str:
        """Format byte size to human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"

    def __str__(self):
        size_str = self.format_size(self.shallow_heap)
        pct_str = f" ({self.percentage:.1f}%)" if self.percentage else ""
        return f"{self.class_name}: {self.instance_count:,} instances, {size_str}{pct_str}"


@dataclass
class DiagnosticEvidence:
    """
    Complete diagnostic evidence extracted from JVM dumps.

    This is the central data structure that holds all analysis results
    and is used to generate reports and Copilot prompts.
    """
    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    source_files: Dict[str, str] = field(default_factory=dict)  # type -> file_path

    # Thread dump analysis
    total_threads: int = 0
    thread_state_distribution: Dict[str, int] = field(default_factory=dict)
    threads: List[ThreadInfo] = field(default_factory=list)

    # Deadlock detection
    deadlocks: List[DeadlockCycle] = field(default_factory=list)
    has_deadlock: bool = False

    # Lock contention
    contention_hotspots: List[ContentionHotspot] = field(default_factory=list)
    high_contention: bool = False

    # CPU-bound threads
    runnable_threads: List[ThreadInfo] = field(default_factory=list)
    runnable_hotspots: List[str] = field(default_factory=list)  # common stack patterns

    # Heap analysis
    heap_classes: List[HeapClassInfo] = field(default_factory=list)
    dominant_classes: List[HeapClassInfo] = field(default_factory=list)
    total_heap_size: Optional[int] = None
    heap_pressure: bool = False

    # Issue summary
    detected_issues: List[str] = field(default_factory=list)
    severity: IssueSeverity = IssueSeverity.INFO
    primary_issue: Optional[str] = None

    # Additional signals
    signals: Dict[str, any] = field(default_factory=dict)

    def add_issue(self, issue: str, severity: IssueSeverity):
        """Add a detected issue and update overall severity."""
        self.detected_issues.append(issue)

        # Update severity to highest level
        severity_order = [
            IssueSeverity.INFO,
            IssueSeverity.LOW,
            IssueSeverity.MEDIUM,
            IssueSeverity.HIGH,
            IssueSeverity.CRITICAL
        ]

        if severity_order.index(severity) > severity_order.index(self.severity):
            self.severity = severity
            self.primary_issue = issue

    def get_blocked_thread_count(self) -> int:
        """Count threads in BLOCKED state."""
        return self.thread_state_distribution.get('BLOCKED', 0)

    def get_waiting_thread_count(self) -> int:
        """Count threads in WAITING or TIMED_WAITING state."""
        return (self.thread_state_distribution.get('WAITING', 0) +
                self.thread_state_distribution.get('TIMED_WAITING', 0))

    def get_summary(self) -> str:
        """Generate a brief summary of findings."""
        parts = []

        if self.has_deadlock:
            parts.append(f"{len(self.deadlocks)} deadlock(s)")

        if self.high_contention:
            parts.append(f"{len(self.contention_hotspots)} contention hotspot(s)")

        blocked = self.get_blocked_thread_count()
        if blocked > 0:
            parts.append(f"{blocked} blocked threads")

        if self.heap_pressure:
            parts.append(f"{len(self.dominant_classes)} dominant heap class(es)")

        if not parts:
            return "No critical issues detected"

        return ", ".join(parts)

    def to_dict(self) -> dict:
        """Convert evidence to dictionary for serialization."""
        return {
            'timestamp': self.analysis_timestamp.isoformat(),
            'source_files': self.source_files,
            'summary': {
                'total_threads': self.total_threads,
                'thread_states': self.thread_state_distribution,
                'severity': self.severity.value,
                'primary_issue': self.primary_issue,
                'issues': self.detected_issues,
            },
            'deadlocks': {
                'detected': self.has_deadlock,
                'count': len(self.deadlocks),
                'cycles': [
                    {
                        'threads': [t.name for t in dl.threads],
                        'description': dl.cycle_description
                    }
                    for dl in self.deadlocks
                ]
            },
            'contention': {
                'high_contention': self.high_contention,
                'hotspot_count': len(self.contention_hotspots),
                'hotspots': [
                    {
                        'lock': str(hs.lock_info),
                        'blocked_count': hs.contention_count,
                        'severity': hs.get_severity().value
                    }
                    for hs in self.contention_hotspots
                ]
            },
            'heap': {
                'pressure': self.heap_pressure,
                'total_size': self.total_heap_size,
                'dominant_classes': [
                    {
                        'name': hc.class_name,
                        'instances': hc.instance_count,
                        'size': hc.shallow_heap,
                        'percentage': hc.percentage
                    }
                    for hc in self.dominant_classes
                ]
            },
            'signals': self.signals
        }
