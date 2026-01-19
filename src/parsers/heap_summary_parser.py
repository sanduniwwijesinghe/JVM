"""
Heap summary parser for Eclipse MAT and jmap histogram exports.

Parses text summaries of heap dumps including:
- Class histograms
- Dominant object reports
- Retained heap information
"""

import re
from typing import List, Optional, Dict
from ..models.evidence import HeapClassInfo


class HeapSummaryParser:
    """
    Parser for heap summary text files exported from Eclipse MAT or jmap.

    Supported formats:
    - Eclipse MAT Histogram export (CSV-like)
    - jmap -histo output
    - Eclipse MAT Dominator Tree export
    """

    # Regex patterns for different heap summary formats

    # Eclipse MAT histogram format:
    # Class Name | Shallow Heap | Retained Heap | Objects
    MAT_HISTOGRAM_PATTERN = re.compile(
        r'([^\|]+?)\s*\|\s*([0-9,]+)\s*\|\s*([0-9,]+)\s*\|\s*([0-9,]+)'
    )

    # jmap -histo format:
    # num     #instances         #bytes  class name
    # 1:         123456       12345678  java.lang.String
    JMAP_PATTERN = re.compile(
        r'^\s*\d+:\s+(\d+)\s+(\d+)\s+(.+)$'
    )

    # Alternative format with commas
    # java.lang.String    1,234,567 instances    123,456,789 bytes
    ALT_PATTERN = re.compile(
        r'^(.+?)\s+([\d,]+)\s+instances?\s+([\d,]+)\s+bytes?'
    )

    # Size patterns (MB, KB, etc.)
    SIZE_PATTERN = re.compile(r'([\d,.]+)\s*(MB|KB|GB|B)', re.IGNORECASE)

    # Percentage patterns
    PERCENT_PATTERN = re.compile(r'([\d.]+)\s*%')

    def __init__(self):
        self.heap_classes: List[HeapClassInfo] = []
        self.total_heap_size: Optional[int] = None
        self.raw_text: str = ""

    def parse_file(self, file_path: str) -> List[HeapClassInfo]:
        """
        Parse a heap summary file and return list of HeapClassInfo objects.

        Args:
            file_path: Path to heap summary text file

        Returns:
            List of HeapClassInfo objects
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            self.raw_text = f.read()

        return self.parse_text(self.raw_text)

    def parse_text(self, text: str) -> List[HeapClassInfo]:
        """
        Parse heap summary text and return list of HeapClassInfo objects.

        Args:
            text: Heap summary text content

        Returns:
            List of HeapClassInfo objects
        """
        self.raw_text = text
        self.heap_classes = []

        # Try to detect total heap size
        self._extract_total_heap_size(text)

        lines = text.split('\n')

        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or self._is_header_line(line):
                continue

            # Try different parsing patterns
            heap_class = self._parse_line(line)
            if heap_class:
                self.heap_classes.append(heap_class)

        # Calculate percentages if we have total heap size
        if self.total_heap_size:
            self._calculate_percentages()

        # Sort by shallow heap size descending
        self.heap_classes.sort(key=lambda x: x.shallow_heap, reverse=True)

        return self.heap_classes

    def _is_header_line(self, line: str) -> bool:
        """Check if line is a header line."""
        header_keywords = [
            'class name', 'instances', 'bytes', 'shallow heap',
            'retained heap', 'objects', '#instances', '#bytes'
        ]
        line_lower = line.lower()
        return any(keyword in line_lower for keyword in header_keywords)

    def _parse_line(self, line: str) -> Optional[HeapClassInfo]:
        """Try to parse a single line using different patterns."""
        # Try Eclipse MAT format
        match = self.MAT_HISTOGRAM_PATTERN.search(line)
        if match:
            class_name = match.group(1).strip()
            shallow_heap = self._parse_number(match.group(2))
            retained_heap = self._parse_number(match.group(3))
            instance_count = self._parse_number(match.group(4))

            return HeapClassInfo(
                class_name=class_name,
                instance_count=instance_count,
                shallow_heap=shallow_heap,
                retained_heap=retained_heap if retained_heap > 0 else None
            )

        # Try jmap format
        match = self.JMAP_PATTERN.match(line)
        if match:
            instance_count = int(match.group(1))
            shallow_heap = int(match.group(2))
            class_name = match.group(3).strip()

            return HeapClassInfo(
                class_name=class_name,
                instance_count=instance_count,
                shallow_heap=shallow_heap
            )

        # Try alternative format
        match = self.ALT_PATTERN.match(line)
        if match:
            class_name = match.group(1).strip()
            instance_count = self._parse_number(match.group(2))
            shallow_heap = self._parse_number(match.group(3))

            return HeapClassInfo(
                class_name=class_name,
                instance_count=instance_count,
                shallow_heap=shallow_heap
            )

        return None

    def _parse_number(self, text: str) -> int:
        """Parse a number from text, handling commas and other formatting."""
        # Remove commas and whitespace
        cleaned = text.replace(',', '').replace(' ', '').strip()
        try:
            return int(cleaned)
        except ValueError:
            return 0

    def _parse_size_with_unit(self, text: str) -> Optional[int]:
        """Parse size with unit (MB, KB, etc.) and return bytes."""
        match = self.SIZE_PATTERN.search(text)
        if not match:
            return None

        value = float(match.group(1).replace(',', ''))
        unit = match.group(2).upper()

        multipliers = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024,
        }

        return int(value * multipliers.get(unit, 1))

    def _extract_total_heap_size(self, text: str):
        """Try to extract total heap size from text."""
        # Look for patterns like "Total: 1024 MB" or "Heap size: 1.5 GB"
        patterns = [
            r'total.*?:\s*([\d,.]+\s*(?:MB|KB|GB|B))',
            r'heap size.*?:\s*([\d,.]+\s*(?:MB|KB|GB|B))',
            r'used.*?:\s*([\d,.]+\s*(?:MB|KB|GB|B))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = self._parse_size_with_unit(match.group(1))
                if size:
                    self.total_heap_size = size
                    return

    def _calculate_percentages(self):
        """Calculate percentage of total heap for each class."""
        if not self.total_heap_size:
            return

        for heap_class in self.heap_classes:
            heap_class.percentage = (heap_class.shallow_heap / self.total_heap_size) * 100

    def get_dominant_classes(self, threshold: float = 0.1) -> List[HeapClassInfo]:
        """
        Get classes that use more than threshold (default 10%) of heap.

        Args:
            threshold: Percentage threshold (0.0 to 1.0)

        Returns:
            List of dominant HeapClassInfo objects
        """
        return [
            hc for hc in self.heap_classes
            if hc.percentage and hc.percentage > (threshold * 100)
        ]

    def get_top_classes(self, limit: int = 10) -> List[HeapClassInfo]:
        """Get top N classes by shallow heap size."""
        return self.heap_classes[:limit]

    def find_class_by_name(self, class_name: str) -> Optional[HeapClassInfo]:
        """Find a heap class by name (exact match)."""
        for hc in self.heap_classes:
            if hc.class_name == class_name:
                return hc
        return None

    def find_classes_by_pattern(self, pattern: str) -> List[HeapClassInfo]:
        """Find heap classes matching a pattern (regex)."""
        regex = re.compile(pattern, re.IGNORECASE)
        return [hc for hc in self.heap_classes if regex.search(hc.class_name)]

    def get_total_instances(self) -> int:
        """Get total number of object instances across all classes."""
        return sum(hc.instance_count for hc in self.heap_classes)

    def get_total_shallow_heap(self) -> int:
        """Get total shallow heap size across all classes."""
        return sum(hc.shallow_heap for hc in self.heap_classes)

    def get_summary_stats(self) -> Dict[str, any]:
        """Get summary statistics."""
        return {
            'total_classes': len(self.heap_classes),
            'total_instances': self.get_total_instances(),
            'total_shallow_heap': self.get_total_shallow_heap(),
            'total_heap_size': self.total_heap_size,
            'top_class': self.heap_classes[0] if self.heap_classes else None,
            'dominant_classes': len(self.get_dominant_classes(0.1))
        }
