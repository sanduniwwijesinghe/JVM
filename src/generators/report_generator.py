"""
Report generator for human-readable diagnostic summaries.

Generates clean, professional reports suitable for:
- Incident reports
- Leadership demos
- Team communication
"""

from datetime import datetime
from typing import Optional
from ..models.evidence import DiagnosticEvidence, IssueSeverity


class ReportGenerator:
    """
    Generates human-readable diagnostic reports.

    Creates structured, professional reports that summarize
    JVM diagnostic findings in a clear, actionable format.
    """

    def __init__(self):
        self.max_threads_to_show = 5
        self.max_stack_frames = 10

    def generate_report(self, evidence: DiagnosticEvidence) -> str:
        """
        Generate a complete human-readable diagnostic report.

        Args:
            evidence: DiagnosticEvidence object

        Returns:
            Formatted report string
        """
        sections = []

        # Title and summary
        sections.append(self._generate_header(evidence))

        # Executive summary
        sections.append(self._generate_executive_summary(evidence))

        # Detailed findings
        if evidence.has_deadlock:
            sections.append(self._generate_deadlock_section(evidence))

        if evidence.high_contention:
            sections.append(self._generate_contention_section(evidence))

        if evidence.runnable_hotspots:
            sections.append(self._generate_cpu_section(evidence))

        if evidence.heap_pressure:
            sections.append(self._generate_heap_section(evidence))

        # Thread state analysis
        sections.append(self._generate_thread_state_section(evidence))

        # Recommendations
        sections.append(self._generate_recommendations(evidence))

        # Footer
        sections.append(self._generate_footer(evidence))

        return "\n\n".join(sections)

    def _generate_header(self, evidence: DiagnosticEvidence) -> str:
        """Generate report header."""
        lines = []
        lines.append("=" * 80)
        lines.append("IFS JVM DIAGNOSTICS REPORT".center(80))
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Generated: {evidence.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)

    def _generate_executive_summary(self, evidence: DiagnosticEvidence) -> str:
        """Generate executive summary section."""
        lines = []
        lines.append("-" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append("")

        # Severity
        severity_label = self._format_severity(evidence.severity)
        lines.append(f"Severity Level: {severity_label}")
        lines.append("")

        # Primary issue
        lines.append("Primary Issue:")
        if evidence.primary_issue:
            lines.append(f"  {evidence.primary_issue}")
        else:
            lines.append("  No critical issues detected")
        lines.append("")

        # Quick stats
        lines.append("Quick Statistics:")
        lines.append(f"  - Total Threads: {evidence.total_threads}")
        lines.append(f"  - Blocked Threads: {evidence.get_blocked_thread_count()}")
        lines.append(f"  - Waiting Threads: {evidence.get_waiting_thread_count()}")
        lines.append(f"  - Deadlocks: {len(evidence.deadlocks)}")
        lines.append(f"  - Contention Hotspots: {len(evidence.contention_hotspots)}")

        if evidence.total_heap_size:
            size_mb = evidence.total_heap_size / (1024 * 1024)
            lines.append(f"  - Heap Size: {size_mb:.2f} MB")

        lines.append("")

        # All detected issues
        if evidence.detected_issues:
            lines.append("Detected Issues:")
            for i, issue in enumerate(evidence.detected_issues, 1):
                lines.append(f"  {i}. {issue}")
        else:
            lines.append("No significant issues detected.")

        return "\n".join(lines)

    def _generate_deadlock_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate deadlock analysis section."""
        lines = []
        lines.append("-" * 80)
        lines.append("DEADLOCK ANALYSIS")
        lines.append("-" * 80)
        lines.append("")

        lines.append(f"⚠️  CRITICAL: {len(evidence.deadlocks)} deadlock(s) detected")
        lines.append("")

        for i, deadlock in enumerate(evidence.deadlocks, 1):
            lines.append(f"Deadlock #{i}:")
            lines.append(f"  Threads involved: {deadlock.get_cycle_size()}")
            lines.append("")
            lines.append("  Cycle:")

            for j, thread in enumerate(deadlock.threads):
                next_idx = (j + 1) % len(deadlock.threads)
                next_thread = deadlock.threads[next_idx]

                lines.append(f"    [{j+1}] Thread: {thread.name}")
                lines.append(f"        State: {thread.state.value}")

                if thread.holding_locks:
                    for lock in thread.holding_locks:
                        lines.append(f"        Holding: {lock.lock_class}")

                if thread.waiting_on_lock:
                    lines.append(f"        Waiting for: {thread.waiting_on_lock.lock_class}")
                    lines.append(f"        (held by: {next_thread.name})")

                lines.append("")

            lines.append("  Impact:")
            lines.append("    - Application is deadlocked and cannot progress")
            lines.append("    - Requires restart or thread dump analysis")
            lines.append("    - Indicates lock ordering issue in code")
            lines.append("")

        return "\n".join(lines)

    def _generate_contention_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate lock contention section."""
        lines = []
        lines.append("-" * 80)
        lines.append("LOCK CONTENTION ANALYSIS")
        lines.append("-" * 80)
        lines.append("")

        lines.append(f"High contention detected on {len(evidence.contention_hotspots)} lock(s)")
        lines.append("")

        for i, hotspot in enumerate(evidence.contention_hotspots[:5], 1):
            severity_label = self._format_severity(hotspot.get_severity())

            lines.append(f"Hotspot #{i} [{severity_label}]:")
            lines.append(f"  Lock Type: {hotspot.lock_info.lock_class}")
            lines.append(f"  Blocked Threads: {hotspot.contention_count}")
            lines.append("")

            if hotspot.holder_thread:
                lines.append(f"  Lock Holder: {hotspot.holder_thread.name}")
                lines.append(f"  Holder State: {hotspot.holder_thread.state.value}")

                if hotspot.holder_thread.stack_trace:
                    lines.append("  Holder Stack (top 5 frames):")
                    for frame in hotspot.holder_thread.get_top_stack_frames(5):
                        lines.append(f"    - {frame}")

            lines.append("")
            lines.append(f"  Waiting Threads (showing {min(5, len(hotspot.blocked_threads))}):")
            for thread in hotspot.blocked_threads[:5]:
                lines.append(f"    - {thread.name} ({thread.state.value})")

            lines.append("")
            lines.append("  Impact:")
            if hotspot.contention_count >= 20:
                lines.append("    - CRITICAL: Severe performance degradation")
            elif hotspot.contention_count >= 10:
                lines.append("    - HIGH: Significant performance impact")
            else:
                lines.append("    - MEDIUM: Noticeable performance impact")
            lines.append("")

        return "\n".join(lines)

    def _generate_cpu_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate CPU-bound analysis section."""
        lines = []
        lines.append("-" * 80)
        lines.append("CPU-BOUND THREAD ANALYSIS")
        lines.append("-" * 80)
        lines.append("")

        lines.append(f"Total RUNNABLE threads: {len(evidence.runnable_threads)}")
        lines.append("")

        hotspots = evidence.signals.get('runnable_hotspots', {})
        if hotspots:
            lines.append("Common Execution Patterns:")
            sorted_hotspots = sorted(hotspots.items(), key=lambda x: x[1], reverse=True)

            for pattern, count in sorted_hotspots[:10]:
                lines.append(f"  - {count} threads: {pattern}")

            lines.append("")
            lines.append("Impact:")
            if len(evidence.runnable_threads) > 50:
                lines.append("    - High CPU utilization detected")
                lines.append("    - May indicate inefficient algorithm or infinite loop")
            else:
                lines.append("    - Moderate CPU activity")
                lines.append("    - Review hotspot methods for optimization opportunities")

        return "\n".join(lines)

    def _generate_heap_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate heap analysis section."""
        lines = []
        lines.append("-" * 80)
        lines.append("HEAP MEMORY ANALYSIS")
        lines.append("-" * 80)
        lines.append("")

        if evidence.total_heap_size:
            size_mb = evidence.total_heap_size / (1024 * 1024)
            lines.append(f"Total Heap Size: {size_mb:.2f} MB")
            lines.append("")

        if evidence.dominant_classes:
            lines.append("Dominant Classes (using >30% heap):")
            lines.append("")

            for hc in evidence.dominant_classes:
                size_mb = hc.shallow_heap / (1024 * 1024)
                lines.append(f"  Class: {hc.class_name}")
                lines.append(f"    Instances: {hc.instance_count:,}")
                lines.append(f"    Shallow Heap: {size_mb:.2f} MB")
                if hc.percentage:
                    lines.append(f"    Heap Usage: {hc.percentage:.1f}%")
                lines.append("")

            lines.append("Impact:")
            lines.append("    - High memory pressure detected")
            lines.append("    - Potential memory leak or excessive object retention")
            lines.append("    - Review object lifecycle and caching strategies")
            lines.append("")

        # Top 10 consumers
        if evidence.heap_classes:
            lines.append("Top 10 Heap Consumers:")
            for i, hc in enumerate(evidence.heap_classes[:10], 1):
                size_mb = hc.shallow_heap / (1024 * 1024)
                pct = f" ({hc.percentage:.1f}%)" if hc.percentage else ""
                lines.append(f"  {i:2d}. {hc.class_name}")
                lines.append(f"      {hc.instance_count:,} instances, {size_mb:.2f} MB{pct}")

        return "\n".join(lines)

    def _generate_thread_state_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate thread state distribution section."""
        lines = []
        lines.append("-" * 80)
        lines.append("THREAD STATE DISTRIBUTION")
        lines.append("-" * 80)
        lines.append("")

        if evidence.thread_state_distribution:
            lines.append(f"Total Threads: {evidence.total_threads}")
            lines.append("")

            # Create a simple bar chart
            max_count = max(evidence.thread_state_distribution.values()) if evidence.thread_state_distribution else 1

            for state, count in sorted(
                evidence.thread_state_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / evidence.total_threads * 100) if evidence.total_threads > 0 else 0
                bar_length = int((count / max_count) * 40)
                bar = "█" * bar_length

                lines.append(f"  {state:20s}: {count:4d} ({percentage:5.1f}%) {bar}")

        # Thread pool stats
        pool_stats = evidence.signals.get('thread_pool_stats', {})
        if pool_stats:
            lines.append("")
            lines.append("Thread Pool Utilization:")
            lines.append("")

            for pool_name, stats in sorted(pool_stats.items()):
                utilization = stats['utilization'] * 100
                lines.append(f"  {pool_name}:")
                lines.append(f"    Total: {stats['total']}, "
                           f"Runnable: {stats['runnable']}, "
                           f"Blocked: {stats['blocked']}, "
                           f"Waiting: {stats['waiting']}")
                lines.append(f"    Utilization: {utilization:.0f}%")

                if utilization > 90:
                    lines.append("    ⚠️  WARNING: High utilization - potential thread pool exhaustion")
                elif utilization > 70:
                    lines.append("    ⚠️  CAUTION: Elevated utilization")

                lines.append("")

        return "\n".join(lines)

    def _generate_recommendations(self, evidence: DiagnosticEvidence) -> str:
        """Generate recommendations section."""
        lines = []
        lines.append("-" * 80)
        lines.append("RECOMMENDED ACTIONS")
        lines.append("-" * 80)
        lines.append("")

        # Generate recommendations based on detected issues
        recommendations = self._build_recommendations(evidence)

        if recommendations['immediate']:
            lines.append("IMMEDIATE (gather information):")
            for i, rec in enumerate(recommendations['immediate'], 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        if recommendations['short_term']:
            lines.append("SHORT-TERM (mitigate impact):")
            for i, rec in enumerate(recommendations['short_term'], 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        if recommendations['long_term']:
            lines.append("LONG-TERM (prevent recurrence):")
            for i, rec in enumerate(recommendations['long_term'], 1):
                lines.append(f"  {i}. {rec}")
            lines.append("")

        lines.append("NOTE: All actions should be performed manually with proper testing")
        lines.append("      and approval in non-production environments first.")

        return "\n".join(lines)

    def _build_recommendations(self, evidence: DiagnosticEvidence) -> dict:
        """Build recommendations based on detected issues."""
        recommendations = {
            'immediate': [],
            'short_term': [],
            'long_term': []
        }

        # Deadlock recommendations
        if evidence.has_deadlock:
            recommendations['immediate'].append(
                "Collect additional thread dumps (3-5) spaced 30 seconds apart"
            )
            recommendations['immediate'].append(
                "Review application logs around the incident time"
            )
            recommendations['short_term'].append(
                "Restart the affected service (if business impact is critical)"
            )
            recommendations['short_term'].append(
                "Review deadlock thread stack traces to identify lock ordering issue"
            )
            recommendations['long_term'].append(
                "Implement consistent lock ordering across codebase"
            )
            recommendations['long_term'].append(
                "Consider using higher-level concurrency utilities (e.g., java.util.concurrent)"
            )

        # Contention recommendations
        if evidence.high_contention:
            recommendations['immediate'].append(
                "Identify the business operation causing high contention"
            )
            recommendations['short_term'].append(
                "Review lock holder code for long-running operations under lock"
            )
            recommendations['long_term'].append(
                "Reduce lock scope - hold locks for shorter duration"
            )
            recommendations['long_term'].append(
                "Consider lock-free data structures or finer-grained locking"
            )

        # CPU recommendations
        if evidence.runnable_hotspots:
            recommendations['immediate'].append(
                "Collect CPU profiling data (e.g., Java Flight Recorder)"
            )
            recommendations['short_term'].append(
                "Review hotspot methods for algorithmic inefficiencies"
            )
            recommendations['long_term'].append(
                "Optimize identified CPU-bound methods"
            )
            recommendations['long_term'].append(
                "Consider caching or pre-computation for expensive operations"
            )

        # Heap recommendations
        if evidence.heap_pressure:
            recommendations['immediate'].append(
                "Monitor heap usage trends over time"
            )
            recommendations['immediate'].append(
                "Collect additional heap dumps for trend analysis"
            )
            recommendations['short_term'].append(
                "Review dominant classes for unnecessary object retention"
            )
            recommendations['long_term'].append(
                "Implement object pooling or caching strategies"
            )
            recommendations['long_term'].append(
                "Review data structures for memory efficiency"
            )

        # Default recommendations if no issues
        if not any(recommendations.values()):
            recommendations['immediate'].append(
                "Continue monitoring - no critical issues detected"
            )
            recommendations['long_term'].append(
                "Establish baseline performance metrics for comparison"
            )

        return recommendations

    def _generate_footer(self, evidence: DiagnosticEvidence) -> str:
        """Generate report footer."""
        lines = []
        lines.append("=" * 80)
        lines.append("END OF REPORT".center(80))
        lines.append("=" * 80)
        lines.append("")
        lines.append("This report was generated by IFS JVM Diagnostics Copilot")
        lines.append("For AI-assisted analysis, use the generated Copilot prompt")
        lines.append("")
        lines.append(f"Report generated: {evidence.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(lines)

    def _format_severity(self, severity: IssueSeverity) -> str:
        """Format severity level with visual indicator."""
        indicators = {
            IssueSeverity.CRITICAL: "🔴 CRITICAL",
            IssueSeverity.HIGH: "🟠 HIGH",
            IssueSeverity.MEDIUM: "🟡 MEDIUM",
            IssueSeverity.LOW: "🟢 LOW",
            IssueSeverity.INFO: "ℹ️  INFO",
        }
        return indicators.get(severity, severity.value)

    def generate_summary_only(self, evidence: DiagnosticEvidence) -> str:
        """Generate a brief summary only (for quick view)."""
        lines = []
        lines.append("JVM Diagnostic Summary")
        lines.append("-" * 50)
        lines.append(f"Severity: {self._format_severity(evidence.severity)}")
        lines.append(f"Primary Issue: {evidence.primary_issue or 'No critical issues'}")
        lines.append("")
        lines.append("Key Findings:")
        for issue in evidence.detected_issues[:5]:
            lines.append(f"  - {issue}")
        return "\n".join(lines)
