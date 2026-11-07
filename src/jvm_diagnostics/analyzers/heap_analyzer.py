"""
Heap analyzer for JVM heap summary analysis.

Analyzes heap dumps summaries to identify memory pressure signals.
"""

from typing import List, Dict, Optional
from ..models.evidence import DiagnosticEvidence, HeapClassInfo, IssueSeverity
from ..parsers.heap_summary_parser import HeapSummaryParser


class HeapAnalyzer:
    """
    High-level analyzer for heap summary analysis.

    Identifies memory pressure signals including:
    - Dominant classes consuming large portions of heap
    - Excessive object retention
    - Unusual object growth patterns
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize heap analyzer.

        Args:
            config: Configuration dict with thresholds:
                - dominant_class_threshold: Alert if class uses >N% heap (0.0-1.0)
                - object_count_threshold: Alert if >N instances of a class
        """
        self.config = config or {}
        self.dominant_class_threshold = self.config.get('dominant_class_threshold', 0.3)
        self.object_count_threshold = self.config.get('object_count_threshold', 1000000)

        self.parser = HeapSummaryParser()
        self.heap_classes: List[HeapClassInfo] = []

    def analyze_heap_summary(
        self,
        file_path: str,
        evidence: Optional[DiagnosticEvidence] = None
    ) -> DiagnosticEvidence:
        """
        Analyze a heap summary file and update diagnostic evidence.

        Args:
            file_path: Path to heap summary file
            evidence: Existing evidence to update (or create new)

        Returns:
            DiagnosticEvidence object with heap analysis results
        """
        # Parse heap summary
        self.heap_classes = self.parser.parse_file(file_path)

        # Initialize or use existing evidence
        if evidence is None:
            evidence = DiagnosticEvidence()

        evidence.source_files['heap_summary'] = file_path
        evidence.heap_classes = self.heap_classes
        evidence.total_heap_size = self.parser.total_heap_size

        # Analyze heap
        self._detect_dominant_classes(evidence)
        self._detect_excessive_objects(evidence)
        self._analyze_heap_pressure(evidence)

        return evidence

    def _detect_dominant_classes(self, evidence: DiagnosticEvidence):
        """Detect classes that dominate heap usage."""
        dominant_classes = self.parser.get_dominant_classes(
            threshold=self.dominant_class_threshold
        )

        if dominant_classes:
            evidence.dominant_classes = dominant_classes
            evidence.heap_pressure = True

            for heap_class in dominant_classes:
                issue = (
                    f"Dominant heap class: {heap_class.class_name} "
                    f"({heap_class.percentage:.1f}% of heap, "
                    f"{heap_class.instance_count:,} instances)"
                )
                evidence.add_issue(issue, IssueSeverity.HIGH)

            # Add signal
            evidence.signals['dominant_classes'] = [
                {
                    'class_name': hc.class_name,
                    'instances': hc.instance_count,
                    'shallow_heap': hc.shallow_heap,
                    'percentage': hc.percentage
                }
                for hc in dominant_classes
            ]

    def _detect_excessive_objects(self, evidence: DiagnosticEvidence):
        """Detect classes with excessive object counts."""
        excessive_classes = [
            hc for hc in self.heap_classes
            if hc.instance_count > self.object_count_threshold
        ]

        if excessive_classes:
            for heap_class in excessive_classes[:5]:  # Top 5
                issue = (
                    f"Excessive object retention: {heap_class.class_name} "
                    f"has {heap_class.instance_count:,} instances"
                )
                evidence.add_issue(issue, IssueSeverity.MEDIUM)

            # Add signal
            evidence.signals['excessive_objects'] = [
                {
                    'class_name': hc.class_name,
                    'instances': hc.instance_count,
                    'shallow_heap': hc.shallow_heap
                }
                for hc in excessive_classes[:10]
            ]

    def _analyze_heap_pressure(self, evidence: DiagnosticEvidence):
        """Analyze overall heap pressure signals."""
        stats = self.parser.get_summary_stats()

        # Add heap statistics to signals
        evidence.signals['heap_statistics'] = stats

        # Check for concerning patterns

        # 1. High number of String objects (potential string leak)
        string_classes = self.parser.find_classes_by_pattern(r'java\.lang\.String|char\[\]')
        if string_classes:
            total_string_heap = sum(hc.shallow_heap for hc in string_classes)
            if evidence.total_heap_size:
                string_percentage = (total_string_heap / evidence.total_heap_size) * 100
                if string_percentage > 30:
                    issue = f"High String retention: {string_percentage:.1f}% of heap"
                    evidence.add_issue(issue, IssueSeverity.MEDIUM)

        # 2. High number of collection objects (potential collection leak)
        collection_classes = self.parser.find_classes_by_pattern(
            r'java\.util\.(Hash)?Map|java\.util\.(Array)?List|java\.util\.Set'
        )
        if collection_classes:
            total_collections = sum(hc.instance_count for hc in collection_classes)
            if total_collections > 100000:
                issue = f"High collection count: {total_collections:,} collection instances"
                evidence.add_issue(issue, IssueSeverity.LOW)

        # 3. Check for custom classes dominating heap
        custom_classes = [
            hc for hc in self.heap_classes[:20]  # Top 20
            if not hc.class_name.startswith('java.') and
               not hc.class_name.startswith('sun.') and
               hc.percentage and hc.percentage > 5
        ]

        if custom_classes:
            evidence.signals['custom_class_dominance'] = [
                {
                    'class_name': hc.class_name,
                    'percentage': hc.percentage,
                    'instances': hc.instance_count
                }
                for hc in custom_classes
            ]

    def get_top_heap_consumers(self, limit: int = 10) -> List[HeapClassInfo]:
        """Get top N heap consuming classes."""
        return self.parser.get_top_classes(limit)

    def find_class(self, class_name: str) -> Optional[HeapClassInfo]:
        """Find a specific class in heap analysis."""
        return self.parser.find_class_by_name(class_name)

    def format_heap_summary(self, evidence: DiagnosticEvidence) -> str:
        """Format a summary of heap analysis."""
        lines = []
        lines.append("Heap Summary Analysis")
        lines.append("=" * 50)

        if evidence.total_heap_size:
            size_mb = evidence.total_heap_size / (1024 * 1024)
            lines.append(f"Total heap size: {size_mb:.2f} MB")

        lines.append(f"Total classes: {len(evidence.heap_classes)}")
        lines.append("")

        if evidence.dominant_classes:
            lines.append("Dominant Classes:")
            for hc in evidence.dominant_classes[:5]:
                lines.append(f"  {hc}")
            lines.append("")

        lines.append("Top 10 Heap Consumers:")
        for i, hc in enumerate(self.get_top_heap_consumers(10), 1):
            size_mb = hc.shallow_heap / (1024 * 1024)
            lines.append(f"  {i:2d}. {hc.class_name}")
            lines.append(f"      {hc.instance_count:,} instances, {size_mb:.2f} MB")

        return "\n".join(lines)
