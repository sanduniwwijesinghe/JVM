"""
Deadlock detector for JVM thread dumps.

Detects circular wait conditions between threads and locks.
"""

from typing import List, Set, Dict, Optional, Tuple
from ..models.evidence import ThreadInfo, DeadlockCycle, LockInfo


class DeadlockDetector:
    """
    Detects deadlocks in JVM thread dumps.

    Implements cycle detection in the wait-for graph where:
    - Nodes are threads
    - Edges represent "waiting for lock held by" relationships
    """

    def __init__(self, threads: List[ThreadInfo]):
        self.threads = threads
        self.lock_holders: Dict[str, ThreadInfo] = {}
        self.wait_for_graph: Dict[str, List[str]] = {}  # thread_id -> [waiting_for_thread_ids]
        self._build_lock_holder_map()
        self._build_wait_for_graph()

    def _build_lock_holder_map(self):
        """Build map of lock_id -> thread holding the lock."""
        for thread in self.threads:
            for lock in thread.holding_locks:
                self.lock_holders[lock.lock_id] = thread

    def _build_wait_for_graph(self):
        """
        Build wait-for graph.

        For each thread, find which threads it's waiting on
        (threads holding locks this thread is waiting for).
        """
        for thread in self.threads:
            self.wait_for_graph[thread.thread_id] = []

            if thread.waiting_on_lock:
                lock_id = thread.waiting_on_lock.lock_id
                holder = self.lock_holders.get(lock_id)

                if holder and holder.thread_id != thread.thread_id:
                    self.wait_for_graph[thread.thread_id].append(holder.thread_id)

    def detect_deadlocks(self) -> List[DeadlockCycle]:
        """
        Detect all deadlock cycles in the thread dump.

        Returns:
            List of DeadlockCycle objects
        """
        deadlocks = []
        visited = set()

        for thread in self.threads:
            if thread.thread_id not in visited:
                cycle = self._find_cycle_from_thread(thread.thread_id, visited)
                if cycle:
                    deadlock = self._create_deadlock_cycle(cycle)
                    if deadlock:
                        deadlocks.append(deadlock)

        return deadlocks

    def _find_cycle_from_thread(
        self,
        start_thread_id: str,
        global_visited: Set[str]
    ) -> Optional[List[str]]:
        """
        Use DFS to find a cycle starting from the given thread.

        Args:
            start_thread_id: Starting thread ID
            global_visited: Set of already processed threads

        Returns:
            List of thread IDs forming a cycle, or None if no cycle
        """
        stack = []
        visited = set()
        rec_stack = set()

        return self._dfs_cycle(start_thread_id, visited, rec_stack, stack, global_visited)

    def _dfs_cycle(
        self,
        thread_id: str,
        visited: Set[str],
        rec_stack: Set[str],
        stack: List[str],
        global_visited: Set[str]
    ) -> Optional[List[str]]:
        """DFS helper for cycle detection."""
        visited.add(thread_id)
        rec_stack.add(thread_id)
        stack.append(thread_id)
        global_visited.add(thread_id)

        # Check all threads this thread is waiting on
        for next_thread_id in self.wait_for_graph.get(thread_id, []):
            if next_thread_id not in visited:
                cycle = self._dfs_cycle(
                    next_thread_id, visited, rec_stack, stack, global_visited
                )
                if cycle:
                    return cycle
            elif next_thread_id in rec_stack:
                # Found a cycle - extract it from stack
                cycle_start_idx = stack.index(next_thread_id)
                return stack[cycle_start_idx:]

        # Backtrack
        rec_stack.remove(thread_id)
        stack.pop()
        return None

    def _create_deadlock_cycle(self, thread_ids: List[str]) -> Optional[DeadlockCycle]:
        """Create a DeadlockCycle object from a list of thread IDs."""
        if len(thread_ids) < 2:
            return None

        # Get ThreadInfo objects
        threads = []
        thread_map = {t.thread_id: t for t in self.threads}

        for tid in thread_ids:
            thread = thread_map.get(tid)
            if not thread:
                return None
            threads.append(thread)

        # Build lock chain
        lock_chain = []
        for i, thread in enumerate(threads):
            # Get the lock this thread is holding that the next thread wants
            if thread.holding_locks:
                # Find which lock the next thread is waiting for
                next_thread = threads[(i + 1) % len(threads)]
                if next_thread.waiting_on_lock:
                    for lock in thread.holding_locks:
                        if lock.lock_id == next_thread.waiting_on_lock.lock_id:
                            lock_chain.append(lock)
                            break

        return DeadlockCycle(threads=threads, lock_chain=lock_chain)

    def has_deadlock(self) -> bool:
        """Check if any deadlock exists."""
        deadlocks = self.detect_deadlocks()
        return len(deadlocks) > 0

    def get_threads_in_deadlock(self) -> Set[str]:
        """Get set of thread names involved in deadlocks."""
        deadlocks = self.detect_deadlocks()
        thread_names = set()

        for deadlock in deadlocks:
            for thread in deadlock.threads:
                thread_names.add(thread.name)

        return thread_names

    def format_deadlock_report(self, deadlock: DeadlockCycle) -> str:
        """Format a deadlock cycle as a human-readable report."""
        lines = []
        lines.append(f"Deadlock detected involving {deadlock.get_cycle_size()} threads:")
        lines.append("")

        for i, thread in enumerate(deadlock.threads):
            next_idx = (i + 1) % len(deadlock.threads)
            next_thread = deadlock.threads[next_idx]

            lines.append(f"Thread: {thread.name}")
            lines.append(f"  State: {thread.state.value}")

            if thread.holding_locks:
                lines.append(f"  Holding locks:")
                for lock in thread.holding_locks:
                    lines.append(f"    - {lock}")

            if thread.waiting_on_lock:
                lines.append(f"  Waiting for: {thread.waiting_on_lock}")
                lines.append(f"    (held by {next_thread.name})")

            lines.append("")

        lines.append("Deadlock cycle:")
        lines.append(f"  {deadlock.cycle_description}")

        return "\n".join(lines)
