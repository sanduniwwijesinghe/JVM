"""
GitHub Copilot prompt generator.

Generates structured prompts for GitHub Copilot to analyze JVM diagnostic evidence.
"""

from typing import Optional
from ..models.evidence import DiagnosticEvidence, IssueSeverity


class CopilotPromptGenerator:
    """
    Generates AI-ready prompts for GitHub Copilot.

    The prompts contain:
    - JVM context and environment
    - Extracted diagnostic evidence
    - Safety constraints
    - Request for root cause analysis
    """

    def __init__(self):
        self.max_stack_frames = 10
        self.max_threads_detail = 5

    def generate_prompt(self, evidence: DiagnosticEvidence) -> str:
        """
        Generate a complete Copilot prompt from diagnostic evidence.

        Args:
            evidence: DiagnosticEvidence object

        Returns:
            Formatted prompt string for GitHub Copilot
        """
        sections = []

        # Header
        sections.append(self._generate_header())

        # Context
        sections.append(self._generate_context(evidence))

        # Evidence
        sections.append(self._generate_evidence_section(evidence))

        # Safety constraints
        sections.append(self._generate_safety_constraints())

        # Request
        sections.append(self._generate_analysis_request(evidence))

        return "\n\n".join(sections)

    def _generate_header(self) -> str:
        """Generate prompt header."""
        return """# JVM Diagnostic Analysis Request

You are a senior JVM performance engineer analyzing a production incident.
Review the diagnostic evidence below and provide your expert analysis."""

    def _generate_context(self, evidence: DiagnosticEvidence) -> str:
        """Generate context section."""
        lines = ["## Context"]
        lines.append("")
        lines.append("**Environment**: Production JVM Application")
        lines.append(f"**Analysis Date**: {evidence.analysis_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        if evidence.source_files:
            lines.append("**Data Sources**:")
            for source_type, file_path in evidence.source_files.items():
                lines.append(f"  - {source_type}: {file_path}")

        lines.append("")
        lines.append("**Incident Summary**:")
        lines.append(f"  - Severity: {evidence.severity.value}")
        lines.append(f"  - Primary Issue: {evidence.primary_issue or 'Under investigation'}")
        lines.append(f"  - Total Threads: {evidence.total_threads}")

        return "\n".join(lines)

    def _generate_evidence_section(self, evidence: DiagnosticEvidence) -> str:
        """Generate evidence section with all findings."""
        sections = []

        sections.append("## Diagnostic Evidence")
        sections.append("")

        # Thread state distribution
        if evidence.thread_state_distribution:
            sections.append("### Thread State Distribution")
            sections.append("")
            for state, count in sorted(
                evidence.thread_state_distribution.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                percentage = (count / evidence.total_threads * 100) if evidence.total_threads > 0 else 0
                sections.append(f"- **{state}**: {count} threads ({percentage:.1f}%)")
            sections.append("")

        # Deadlocks
        if evidence.has_deadlock:
            sections.append("### Deadlock Detection")
            sections.append("")
            sections.append(f"**{len(evidence.deadlocks)} deadlock(s) detected**")
            sections.append("")

            for i, deadlock in enumerate(evidence.deadlocks, 1):
                sections.append(f"#### Deadlock {i}")
                sections.append(f"- Cycle size: {deadlock.get_cycle_size()} threads")
                sections.append(f"- Description: {deadlock.cycle_description}")
                sections.append("")
                sections.append("Threads involved:")

                for thread in deadlock.threads[:self.max_threads_detail]:
                    sections.append(f"- **{thread.name}** ({thread.state.value})")

                    if thread.waiting_on_lock:
                        sections.append(f"  - Waiting for: {thread.waiting_on_lock}")

                    if thread.holding_locks:
                        sections.append(f"  - Holding: {thread.holding_locks[0]}")

                    if thread.stack_trace:
                        sections.append("  - Top stack frames:")
                        for frame in thread.get_top_stack_frames(3):
                            sections.append(f"    - `{frame}`")

                sections.append("")

        # Lock contention
        if evidence.high_contention:
            sections.append("### Lock Contention Hotspots")
            sections.append("")

            for i, hotspot in enumerate(evidence.contention_hotspots[:3], 1):
                sections.append(f"#### Hotspot {i} [{hotspot.get_severity().value}]")
                sections.append(f"- Lock: `{hotspot.lock_info.lock_class}`")
                sections.append(f"- Blocked threads: {hotspot.contention_count}")

                if hotspot.holder_thread:
                    sections.append(f"- Held by: **{hotspot.holder_thread.name}** ({hotspot.holder_thread.state.value})")

                    if hotspot.holder_thread.stack_trace:
                        sections.append("- Holder stack trace:")
                        for frame in hotspot.holder_thread.get_top_stack_frames(5):
                            sections.append(f"  - `{frame}`")

                sections.append("")

        # CPU-bound threads
        if evidence.runnable_hotspots:
            sections.append("### CPU-Bound Hotspots")
            sections.append("")
            sections.append(f"**{len(evidence.runnable_threads)} RUNNABLE threads detected**")
            sections.append("")
            sections.append("Common patterns:")

            hotspots = evidence.signals.get('runnable_hotspots', {})
            for pattern, count in sorted(hotspots.items(), key=lambda x: x[1], reverse=True)[:5]:
                sections.append(f"- `{pattern}`: {count} threads")

            sections.append("")

        # Heap analysis
        if evidence.heap_pressure:
            sections.append("### Heap Memory Pressure")
            sections.append("")

            if evidence.total_heap_size:
                size_mb = evidence.total_heap_size / (1024 * 1024)
                sections.append(f"**Total heap size**: {size_mb:.2f} MB")
                sections.append("")

            if evidence.dominant_classes:
                sections.append("**Dominant classes**:")
                for hc in evidence.dominant_classes[:5]:
                    sections.append(f"- `{hc.class_name}`")
                    sections.append(f"  - Instances: {hc.instance_count:,}")
                    if hc.percentage:
                        sections.append(f"  - Heap usage: {hc.percentage:.1f}%")
                sections.append("")

        # Thread pool stats
        pool_stats = evidence.signals.get('thread_pool_stats', {})
        if pool_stats:
            sections.append("### Thread Pool Utilization")
            sections.append("")
            for pool_name, stats in list(pool_stats.items())[:5]:
                utilization = stats['utilization'] * 100
                sections.append(f"- **{pool_name}**")
                sections.append(f"  - Total: {stats['total']}, Runnable: {stats['runnable']}, Blocked: {stats['blocked']}")
                sections.append(f"  - Utilization: {utilization:.0f}%")
            sections.append("")

        # All detected issues
        if evidence.detected_issues:
            sections.append("### Detected Issues")
            sections.append("")
            for issue in evidence.detected_issues:
                sections.append(f"- {issue}")
            sections.append("")

        return "\n".join(sections)

    def _generate_safety_constraints(self) -> str:
        """Generate safety constraints section."""
        return """## Safety Constraints

**IMPORTANT**: Your analysis must respect these constraints:

1. **Read-Only Analysis**: Only analyze provided evidence, do not suggest actions that modify systems
2. **Manual Actions Only**: All recommended actions must be manual, safe, and reversible
3. **No Automation**: Do not suggest automated remediation, restarts, or infrastructure changes
4. **No Production Changes**: Do not recommend direct production environment modifications
5. **Human-in-the-Loop**: All actions require human review and approval

**Acceptable Actions**:
- Code review and analysis
- Configuration review (read-only)
- Log analysis and correlation
- Manual testing in non-production environments
- Gathering additional diagnostic data
- Consulting documentation and team knowledge

**Unacceptable Actions**:
- Automatic service restarts
- Code deployment or rollback
- Infrastructure scaling or changes
- Database operations
- Cache clearing or manipulation
- Feature flag changes"""

    def _generate_analysis_request(self, evidence: DiagnosticEvidence) -> str:
        """Generate the analysis request section."""
        lines = ["## Analysis Request"]
        lines.append("")
        lines.append("Please provide your expert analysis following this structure:")
        lines.append("")

        lines.append("### 1. Issue Explanation")
        lines.append("Explain the detected issue(s) in clear, non-technical language suitable for incident reports.")
        lines.append("")

        lines.append("### 2. Root Cause Analysis")
        lines.append("Identify the probable root cause based on the evidence. Consider:")

        if evidence.has_deadlock:
            lines.append("- Why did the deadlock occur? What is the lock ordering issue?")
        if evidence.high_contention:
            lines.append("- What is causing the lock contention? Is it a hotspot in the code?")
        if evidence.runnable_hotspots:
            lines.append("- What is causing the CPU-bound behavior? Is it an inefficient algorithm?")
        if evidence.heap_pressure:
            lines.append("- What is causing the memory pressure? Is there a memory leak?")

        lines.append("")

        lines.append("### 3. Confidence Assessment")
        lines.append("State your confidence level in the root cause analysis:")
        lines.append("- **High**: Clear evidence and well-known patterns")
        lines.append("- **Medium**: Strong indicators but some ambiguity")
        lines.append("- **Low**: Multiple possible causes, need more data")
        lines.append("")

        lines.append("### 4. Recommended Next Actions")
        lines.append("Suggest **safe, manual** next steps in priority order:")
        lines.append("")
        lines.append("**Immediate** (to gather more information):")
        lines.append("- What additional diagnostics should be collected?")
        lines.append("- What logs or metrics should be reviewed?")
        lines.append("")
        lines.append("**Short-term** (to mitigate the issue):")
        lines.append("- What manual, reversible actions can reduce impact?")
        lines.append("- What configuration should be reviewed?")
        lines.append("")
        lines.append("**Long-term** (to prevent recurrence):")
        lines.append("- What code changes should be considered?")
        lines.append("- What architectural improvements would help?")
        lines.append("")

        lines.append("### 5. Additional Context Needed")
        lines.append("List any additional information that would improve the analysis:")
        lines.append("- Missing metrics or logs")
        lines.append("- Application context (business logic, expected load)")
        lines.append("- Historical patterns or previous incidents")
        lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("**Note**: Focus on actionable insights that help the engineering team")
        lines.append("understand and resolve the issue safely and effectively.")

        return "\n".join(lines)

    def generate_short_prompt(self, evidence: DiagnosticEvidence) -> str:
        """
        Generate a shorter, more focused prompt for quick analysis.

        Args:
            evidence: DiagnosticEvidence object

        Returns:
            Short prompt string
        """
        lines = []

        lines.append("# Quick JVM Diagnostic Analysis")
        lines.append("")
        lines.append(f"**Severity**: {evidence.severity.value}")
        lines.append(f"**Primary Issue**: {evidence.primary_issue or 'Multiple issues detected'}")
        lines.append("")

        lines.append("**Key Evidence**:")
        for issue in evidence.detected_issues[:5]:
            lines.append(f"- {issue}")

        lines.append("")
        lines.append("**Question**: What is the most likely root cause and what safe, manual action")
        lines.append("should the team take immediately to mitigate this issue?")
        lines.append("")
        lines.append("(Provide a concise analysis with high/medium/low confidence level)")

        return "\n".join(lines)
