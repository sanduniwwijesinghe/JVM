"""
File handler for JVM diagnostic files.

Handles file detection, validation, and .hprof guidance.
"""

import os
from typing import Optional, Tuple
from pathlib import Path


class FileHandler:
    """
    Handles file operations for JVM diagnostic files.

    Provides:
    - File existence and format validation
    - .hprof file detection and user guidance
    - File type detection
    """

    THREAD_DUMP_EXTENSIONS = ['.txt', '.log', '.dump', '.tdump']
    HEAP_SUMMARY_EXTENSIONS = ['.txt', '.csv', '.log']
    HPROF_EXTENSIONS = ['.hprof']

    def __init__(self):
        pass

    def validate_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that file exists and is readable.

        Args:
            file_path: Path to file

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file_path:
            return False, "File path is empty"

        path = Path(file_path)

        if not path.exists():
            return False, f"File does not exist: {file_path}"

        if not path.is_file():
            return False, f"Path is not a file: {file_path}"

        if not os.access(file_path, os.R_OK):
            return False, f"File is not readable: {file_path}"

        # Check file size (warn if > 100MB)
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > 100:
            return True, f"Warning: Large file ({size_mb:.1f} MB) - parsing may take time"

        return True, ""

    def detect_file_type(self, file_path: str) -> str:
        """
        Detect file type based on extension and content.

        Args:
            file_path: Path to file

        Returns:
            File type: 'thread_dump', 'heap_summary', 'hprof', 'unknown'
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        # Check extension
        if extension in self.HPROF_EXTENSIONS:
            return 'hprof'

        # Try to detect from content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first few lines
                header = f.read(5000)

                # Thread dump indicators
                thread_indicators = [
                    'java.lang.Thread.State:',
                    'tid=0x',
                    '- locked <',
                    '- waiting on <',
                    'Full thread dump',
                    'Thread dump'
                ]

                # Heap summary indicators
                heap_indicators = [
                    'Class Name',
                    'Shallow Heap',
                    'Retained Heap',
                    '#instances',
                    '#bytes',
                    'java.lang.String',
                    'java.util.'
                ]

                thread_score = sum(1 for ind in thread_indicators if ind in header)
                heap_score = sum(1 for ind in heap_indicators if ind in header)

                if thread_score > heap_score and thread_score >= 2:
                    return 'thread_dump'
                elif heap_score >= 2:
                    return 'heap_summary'

        except Exception:
            pass

        return 'unknown'

    def is_hprof_file(self, file_path: str) -> bool:
        """Check if file is a .hprof binary heap dump."""
        if not file_path:
            return False

        path = Path(file_path)
        extension = path.suffix.lower()

        if extension in self.HPROF_EXTENSIONS:
            return True

        # Check magic bytes for HPROF format
        try:
            with open(file_path, 'rb') as f:
                header = f.read(20)
                # HPROF files start with "JAVA PROFILE" string
                if header.startswith(b'JAVA PROFILE'):
                    return True
        except Exception:
            pass

        return False

    def generate_hprof_guidance(self, hprof_path: str) -> str:
        """
        Generate step-by-step guidance for handling .hprof files.

        Args:
            hprof_path: Path to .hprof file

        Returns:
            Formatted guidance string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("HEAP DUMP FILE DETECTED (.hprof)")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"File: {hprof_path}")
        lines.append("")
        lines.append("This tool does not parse binary .hprof files directly.")
        lines.append("Instead, please export a text summary using Eclipse MAT:")
        lines.append("")

        lines.append("STEP-BY-STEP INSTRUCTIONS:")
        lines.append("-" * 80)
        lines.append("")

        lines.append("Step 1: Open Eclipse MAT (Memory Analyzer Tool)")
        lines.append("  - Download from: https://www.eclipse.org/mat/downloads.php")
        lines.append("  - Or use existing installation")
        lines.append("")

        lines.append("Step 2: Load the heap dump")
        lines.append(f"  - File → Open Heap Dump")
        lines.append(f"  - Select: {hprof_path}")
        lines.append("  - Wait for MAT to parse the dump (may take several minutes)")
        lines.append("")

        lines.append("Step 3: Generate Histogram Report")
        lines.append("  - Click on 'Histogram' button in the toolbar")
        lines.append("  - Or: Menu → Query Browser → Histogram")
        lines.append("  - The histogram shows all classes with instance counts and sizes")
        lines.append("")

        lines.append("Step 4: Export Histogram as Text")
        lines.append("  - In the Histogram view, click the export icon (disk icon)")
        lines.append("  - Or: Right-click → Export → Text")
        lines.append("  - Save as: heap_histogram.txt (or any .txt file)")
        lines.append("")

        lines.append("Step 5: Run analysis with the exported summary")
        lines.append("  - Use this command:")
        lines.append(f"    python src/cli.py analyze \\")
        lines.append(f"      --heap-summary heap_histogram.txt")
        lines.append("")
        lines.append("  - Or if you also have a thread dump:")
        lines.append(f"    python src/cli.py analyze \\")
        lines.append(f"      --thread-dump thread_dump.txt \\")
        lines.append(f"      --heap-summary heap_histogram.txt")
        lines.append("")

        lines.append("=" * 80)
        lines.append("WHY NOT PARSE .HPROF DIRECTLY?")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Binary heap dumps are complex and require specialized parsing libraries.")
        lines.append("Benefits of using MAT for export:")
        lines.append("  ✓ Leverages proven, mature tooling (Eclipse MAT)")
        lines.append("  ✓ Aligns with existing IFS operational workflow")
        lines.append("  ✓ Keeps this tool simple, maintainable, and focused")
        lines.append("  ✓ MAT provides additional powerful analysis capabilities")
        lines.append("  ✓ Text summaries are portable and version-control friendly")
        lines.append("")

        lines.append("ALTERNATIVE: Using jmap (if MAT unavailable)")
        lines.append("-" * 80)
        lines.append("")
        lines.append("You can also use jmap to generate a histogram directly:")
        lines.append(f"  jmap -histo:live <pid> > heap_histogram.txt")
        lines.append("")
        lines.append("Or from an existing .hprof file:")
        lines.append(f"  jmap -histo {hprof_path} > heap_histogram.txt")
        lines.append("")
        lines.append("Then run the analysis with the generated heap_histogram.txt")
        lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def check_file_encoding(self, file_path: str) -> str:
        """
        Detect file encoding.

        Args:
            file_path: Path to file

        Returns:
            Encoding string ('utf-8', 'ascii', 'latin-1', etc.)
        """
        # Try to read with different encodings
        encodings = ['utf-8', 'ascii', 'latin-1', 'cp1252']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1000)
                return encoding
            except UnicodeDecodeError:
                continue

        return 'utf-8'  # Default fallback

    def get_file_info(self, file_path: str) -> dict:
        """
        Get file information.

        Args:
            file_path: Path to file

        Returns:
            Dict with file metadata
        """
        path = Path(file_path)

        if not path.exists():
            return {'exists': False}

        stat = path.stat()

        return {
            'exists': True,
            'path': str(path.absolute()),
            'name': path.name,
            'size_bytes': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified': stat.st_mtime,
            'extension': path.suffix,
            'detected_type': self.detect_file_type(file_path),
            'is_hprof': self.is_hprof_file(file_path)
        }

    def create_output_filename(
        self,
        input_file: str,
        output_dir: Optional[str] = None,
        suffix: str = '_diagnostic_report'
    ) -> str:
        """
        Create output filename based on input file.

        Args:
            input_file: Input file path
            output_dir: Output directory (optional)
            suffix: Suffix to add to filename

        Returns:
            Output file path
        """
        input_path = Path(input_file)
        base_name = input_path.stem

        output_name = f"{base_name}{suffix}.txt"

        if output_dir:
            output_path = Path(output_dir) / output_name
        else:
            output_path = input_path.parent / output_name

        return str(output_path)
