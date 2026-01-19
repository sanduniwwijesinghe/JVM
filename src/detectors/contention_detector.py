"""
Lock contention detector for JVM thread dumps.

Identifies lock contention hotspots where multiple threads are blocked
on the same lock.
"""

from typing import List, Dict
from collections import defaultdict
from ..models.evidence import ThreadInfo, ThreadState, ContentionHotspot, LockInfo


class ContentionDetector:
    """
    Detects lock contention hotspots in JVM thread dumps.

    Identifies locks that have multiple threads blocked waiting for them,
    indicating contention points in the application.
    """

    def __init__(self, threads: List[ThreadInfo], threshold: int = 3):
        """
        Initialize contention detector.

        Args:
            threads: List of ThreadInfo objects
            threshold: Minimum number of blocked threads to consider as contention
        """
        self.threads = threads
        self.threshold = threshold
        self.lock_waiters: Dict[str, List[ThreadInfo]] = defaultdict(list)
        self.lock_holders: Dict[str, ThreadInfo] = {}
        self._build_lock_maps()

    def _build_lock_maps(self):
        """Build maps of locks to waiting threads and holding threads."""
        for thread in self.threads:
            # Map locks to holding threads
            for lock in thread.holding_locks:
                self.lock_holders[lock.lock_id] = thread

            # Map locks to waiting threads
            if thread.waiting_on_lock and thread.is_blocked_or_waiting():
                lock_id = thread.waiting_on_lock.lock_id
                self.lock_waiters[lock_id].append(thread)

    def detect_contention_hotspots(self) -> List[ContentionHotspot]:
        """
        Detect lock contention hotspots.

        Returns:
            List of ContentionHotspot objects sorted by contention count
        """
        hotspots = []

        for lock_id, waiting_threads in self.lock_waiters.items():
            contention_count = len(waiting_threads)

            # Only report if above threshold
            if contention_count >= self.threshold:
                # Get lock info from first waiting thread
                lock_info = waiting_threads[0].waiting_on_lock

                # Find holder thread
                holder = self.lock_holders.get(lock_id)

                hotspot = ContentionHotspot(
                    lock_info=lock_info,
                    blocked_threads=waiting_threads,
                    contention_count=contention_count,
                    holder_thread=holder
                )
                hotspots.append(hotspot)

        # Sort by contention count descending
        hotspots.sort(key=lambda x: x.contention_count, reverse=True)

        return hotspots

    def get_top_contention_hotspots(self, limit: int = 5) -> List[ContentionHotspot]:
        """Get top N contention hotspots."""
        hotspots = self.detect_contention_hotspots()
        return hotspots[:limit]

    def has_high_contention(self, high_threshold: int = 10) -> bool:
        """
        Check if there's high contention.

        Args:
            high_threshold: Number of blocked threads to consider as high contention

        Returns:
            True if any lock has more than high_threshold blocked threads
        """
        hotspots = self.detect_contention_hotspots()
        return any(h.contention_count >= high_threshold for h in hotspots)

    def get_total_blocked_threads(self) -> int:
        """Get total number of blocked threads."""
        return sum(
            1 for t in self.threads
            if t.state == ThreadState.BLOCKED
        )

    def get_most_contended_lock(self) -> ContentionHotspot:
        """Get the most contended lock."""
        hotspots = self.detect_contention_hotspots()
        return hotspots[0] if hotspots else None

    def format_hotspot_report(self, hotspot: ContentionHotspot) -> str:
        """Format a contention hotspot as a human-readable report."""
        lines = []
        lines.append(f"Lock Contention Hotspot [{hotspot.get_severity().value}]:")
        lines.append(f"  Lock: {hotspot.lock_info}")
        lines.append(f"  Blocked threads: {hotspot.contention_count}")
        lines.append("")

        if hotspot.holder_thread:
            lines.append(f"  Held by: {hotspot.holder_thread.name}")
            lines.append(f"    State: {hotspot.holder_thread.state.value}")
            if hotspot.holder_thread.stack_trace:
                lines.append(f"    Top stack frame:")
                top_frames = hotspot.holder_thread.get_top_stack_frames(3)
                for frame in top_frames:
                    lines.append(f"      {frame}")
            lines.append("")

        lines.append(f"  Waiting threads ({min(5, len(hotspot.blocked_threads))} shown):")
        for thread in hotspot.blocked_threads[:5]:
            lines.append(f"    - {thread.name} ({thread.state.value})")

        return "\n".join(lines)

    def find_runnable_hotspots(self) -> Dict[str, int]:
        """
        Find common stack patterns in RUNNABLE threads (CPU-bound hotspots).

        Returns:
            Dict mapping stack frame patterns to occurrence count
        """
        runnable_threads = [
            t for t in self.threads
            if t.state == ThreadState.RUNNABLE and not t.native
        ]

        # Count top stack frame occurrences
        frame_counts = defaultdict(int)

        for thread in runnable_threads:
            if thread.stack_trace:
                # Get top frame (most recent)
                top_frame = thread.stack_trace[0] if thread.stack_trace else None
                if top_frame:
                    # Extract method name
                    method = self._extract_method_from_frame(top_frame)
                    frame_counts[method] += 1

        # Filter to show only patterns with multiple threads
        return {k: v for k, v in frame_counts.items() if v >= 2}

    def _extract_method_from_frame(self, frame: str) -> str:
        """Extract method name from stack frame."""
        # Frame format: "com.example.Class.method(File.java:123)"
        if '(' in frame:
            method_part = frame.split('(')[0]
            return method_part
        return frame

    def get_thread_pool_stats(self) -> Dict[str, any]:
        """
        Analyze thread pool utilization.

        Returns:
            Dict with thread pool statistics
        """
        # Group threads by common prefixes (thread pool names)
        pool_threads = defaultdict(list)

        for thread in self.threads:
            # Extract pool name (e.g., "http-nio-8080-exec" from "http-nio-8080-exec-123")
            pool_name = self._extract_pool_name(thread.name)
            pool_threads[pool_name].append(thread)

        # Calculate stats per pool
        pool_stats = {}
        for pool_name, threads in pool_threads.items():
            if len(threads) >= 3:  # Only report pools with multiple threads
                blocked = sum(1 for t in threads if t.state == ThreadState.BLOCKED)
                waiting = sum(1 for t in threads if t.state in [ThreadState.WAITING, ThreadState.TIMED_WAITING])
                runnable = sum(1 for t in threads if t.state == ThreadState.RUNNABLE)

                pool_stats[pool_name] = {
                    'total': len(threads),
                    'runnable': runnable,
                    'blocked': blocked,
                    'waiting': waiting,
                    'utilization': runnable / len(threads) if threads else 0
                }

        return pool_stats

    def _extract_pool_name(self, thread_name: str) -> str:
        """
        Extract thread pool name from thread name.

        Examples:
            "http-nio-8080-exec-123" -> "http-nio-8080-exec"
            "pool-1-thread-5" -> "pool-1-thread"
            "DubboServerHandler-10.0.0.1:20880-thread-123" -> "DubboServerHandler"
        """
        # Remove trailing numbers
        import re
        # Match common patterns
        patterns = [
            r'(.+-exec)-\d+',           # http-nio-8080-exec-123
            r'(.+-thread)-\d+',         # pool-1-thread-5
            r'(.+)-\d+$',               # general-123
        ]

        for pattern in patterns:
            match = re.match(pattern, thread_name)
            if match:
                return match.group(1)

        # Fallback: remove trailing dash and numbers
        return re.sub(r'-\d+$', '', thread_name)
