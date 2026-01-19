#!/usr/bin/env python3
"""
IFS JVM Diagnostics Copilot - CLI

Command-line interface for JVM diagnostic analysis.
"""

import sys
import os
from pathlib import Path
from typing import Optional
import yaml

# Add src to path if running as script
if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.evidence import DiagnosticEvidence
from src.analyzers.thread_analyzer import ThreadAnalyzer
from src.analyzers.heap_analyzer import HeapAnalyzer
from src.generators.copilot_prompt_generator import CopilotPromptGenerator
from src.generators.report_generator import ReportGenerator
from src.utils.file_handler import FileHandler


class JVMDiagnosticsCLI:
    """
    Main CLI application for JVM diagnostics.
    """

    def __init__(self):
        self.config = self._load_config()
        self.file_handler = FileHandler()
        self.thread_analyzer = ThreadAnalyzer(self.config.get('thread_analysis', {}))
        self.heap_analyzer = HeapAnalyzer(self.config.get('heap_analysis', {}))
        self.copilot_generator = CopilotPromptGenerator()
        self.report_generator = ReportGenerator()

    def _load_config(self) -> dict:
        """Load configuration from config file."""
        config_path = Path(__file__).parent.parent / 'config' / 'analysis_config.yaml'

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                return {}

        # Default configuration
        return {
            'thread_analysis': {
                'blocked_threshold': 10,
                'runnable_threshold': 50,
                'contention_threshold': 5
            },
            'heap_analysis': {
                'dominant_class_threshold': 0.3,
                'object_count_threshold': 1000000
            }
        }

    def run(self, args: dict):
        """
        Main entry point for CLI.

        Args:
            args: Parsed command-line arguments
        """
        command = args.get('command', 'analyze')

        if command == 'analyze':
            self.analyze(args)
        elif command == 'version':
            self.show_version()
        elif command == 'help':
            self.show_help()
        else:
            print(f"Unknown command: {command}")
            self.show_help()
            sys.exit(1)

    def analyze(self, args: dict):
        """
        Run diagnostic analysis.

        Args:
            args: Command arguments with file paths
        """
        thread_dump_path = args.get('thread_dump')
        heap_summary_path = args.get('heap_summary')
        hprof_path = args.get('hprof')
        output_path = args.get('output')
        mode = args.get('mode', 'full')  # 'full', 'summary', 'copilot'

        print("=" * 80)
        print("IFS JVM Diagnostics Copilot".center(80))
        print("=" * 80)
        print()

        # Check if .hprof file was provided
        if hprof_path:
            if self.file_handler.is_hprof_file(hprof_path):
                guidance = self.file_handler.generate_hprof_guidance(hprof_path)
                print(guidance)
                return
            else:
                print(f"Error: File does not appear to be a valid .hprof file: {hprof_path}")
                sys.exit(1)

        # Validate inputs
        if not thread_dump_path and not heap_summary_path:
            print("Error: At least one of --thread-dump or --heap-summary is required")
            print()
            self.show_help()
            sys.exit(1)

        # Initialize evidence
        evidence = DiagnosticEvidence()

        # Analyze thread dump
        if thread_dump_path:
            print(f"Analyzing thread dump: {thread_dump_path}")

            # Validate file
            is_valid, error = self.file_handler.validate_file(thread_dump_path)
            if not is_valid:
                print(f"Error: {error}")
                sys.exit(1)

            # Check file type
            file_type = self.file_handler.detect_file_type(thread_dump_path)
            if file_type == 'hprof':
                guidance = self.file_handler.generate_hprof_guidance(thread_dump_path)
                print(guidance)
                return
            elif file_type == 'unknown':
                print(f"Warning: Could not detect file type for {thread_dump_path}")
                print("Attempting to parse as thread dump...")

            try:
                evidence = self.thread_analyzer.analyze_thread_dump(thread_dump_path)
                print(f"  ✓ Parsed {evidence.total_threads} threads")
                if evidence.has_deadlock:
                    print(f"  ⚠️  CRITICAL: Deadlock detected!")
                if evidence.high_contention:
                    print(f"  ⚠️  HIGH: Lock contention detected!")
            except Exception as e:
                print(f"Error analyzing thread dump: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

            print()

        # Analyze heap summary
        if heap_summary_path:
            print(f"Analyzing heap summary: {heap_summary_path}")

            # Validate file
            is_valid, error = self.file_handler.validate_file(heap_summary_path)
            if not is_valid:
                print(f"Error: {error}")
                sys.exit(1)

            # Check file type
            file_type = self.file_handler.detect_file_type(heap_summary_path)
            if file_type == 'hprof':
                guidance = self.file_handler.generate_hprof_guidance(heap_summary_path)
                print(guidance)
                return

            try:
                evidence = self.heap_analyzer.analyze_heap_summary(heap_summary_path, evidence)
                print(f"  ✓ Parsed {len(evidence.heap_classes)} heap classes")
                if evidence.heap_pressure:
                    print(f"  ⚠️  WARNING: Heap pressure detected!")
            except Exception as e:
                print(f"Error analyzing heap summary: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

            print()

        # Generate outputs
        print("Generating diagnostic report...")
        print()

        # Generate report
        if mode in ['full', 'summary']:
            if mode == 'full':
                report = self.report_generator.generate_report(evidence)
            else:
                report = self.report_generator.generate_summary_only(evidence)

            # Output report
            if output_path:
                self._write_output(output_path, report, 'report')
                print(f"✓ Report saved to: {output_path}")
            else:
                print(report)

            print()

        # Generate Copilot prompt
        if mode in ['full', 'copilot']:
            copilot_prompt = self.copilot_generator.generate_prompt(evidence)

            # Determine Copilot prompt output path
            if output_path:
                copilot_path = self._get_copilot_output_path(output_path)
            else:
                # If no output specified, create copilot prompt file anyway
                copilot_path = self._generate_default_output_path(
                    thread_dump_path or heap_summary_path,
                    '_copilot_prompt'
                )

            self._write_output(copilot_path, copilot_prompt, 'Copilot prompt')
            print(f"✓ Copilot prompt saved to: {copilot_path}")
            print()

        # Summary
        print("=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)
        print()
        print(f"Severity: {evidence.severity.value}")
        print(f"Issues detected: {len(evidence.detected_issues)}")
        print()

        if evidence.detected_issues:
            print("Top issues:")
            for issue in evidence.detected_issues[:5]:
                print(f"  - {issue}")
            print()

        print("Next steps:")
        print("  1. Review the diagnostic report for detailed findings")
        print("  2. Copy the Copilot prompt to GitHub Copilot for AI analysis")
        print("  3. Follow recommended actions for safe mitigation")
        print()

    def _write_output(self, file_path: str, content: str, label: str):
        """Write output to file."""
        try:
            output_dir = Path(file_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            print(f"Error writing {label} to {file_path}: {e}")
            sys.exit(1)

    def _get_copilot_output_path(self, report_path: str) -> str:
        """Generate Copilot prompt output path from report path."""
        path = Path(report_path)
        stem = path.stem

        # Remove _report suffix if present
        if stem.endswith('_report'):
            stem = stem[:-7]
        elif stem.endswith('_diagnostic_report'):
            stem = stem[:-18]

        copilot_name = f"{stem}_copilot_prompt.txt"
        return str(path.parent / copilot_name)

    def _generate_default_output_path(self, input_path: str, suffix: str) -> str:
        """Generate default output path."""
        return self.file_handler.create_output_filename(input_path, suffix=suffix)

    def show_version(self):
        """Show version information."""
        print("IFS JVM Diagnostics Copilot")
        print("Version: 1.0.0")
        print("A local diagnostics tool for JVM performance analysis")

    def show_help(self):
        """Show help information."""
        help_text = """
IFS JVM Diagnostics Copilot - Help
===================================

USAGE:
    python src/cli.py analyze [OPTIONS]

OPTIONS:
    --thread-dump PATH      Path to thread dump file (.txt)
    --heap-summary PATH     Path to heap summary file (.txt)
    --hprof PATH            Path to .hprof file (shows export guidance)
    --output PATH           Output file path for report
    --mode MODE             Output mode: full, summary, copilot (default: full)

EXAMPLES:

    # Analyze thread dump only
    python src/cli.py analyze --thread-dump thread_dump.txt

    # Analyze both thread dump and heap summary
    python src/cli.py analyze \\
        --thread-dump thread_dump.txt \\
        --heap-summary heap_histogram.txt

    # Save report to file
    python src/cli.py analyze \\
        --thread-dump thread_dump.txt \\
        --output diagnostic_report.txt

    # Handle .hprof file (shows export instructions)
    python src/cli.py analyze --hprof heap_dump.hprof

    # Generate Copilot prompt only
    python src/cli.py analyze \\
        --thread-dump thread_dump.txt \\
        --mode copilot

WORKFLOW:

    1. Capture JVM dumps:
       - Thread dump: jstack <pid> > thread_dump.txt
       - Heap dump: jmap -dump:format=b,file=heap.hprof <pid>

    2. Export heap summary from Eclipse MAT:
       - Open heap.hprof in Eclipse MAT
       - Generate Histogram report
       - Export as text: heap_histogram.txt

    3. Run analysis:
       python src/cli.py analyze \\
           --thread-dump thread_dump.txt \\
           --heap-summary heap_histogram.txt \\
           --output report.txt

    4. Review report and use Copilot prompt for AI analysis

For more information, see README.md
"""
        print(help_text)


def parse_args():
    """Parse command-line arguments (simple parser)."""
    args = {
        'command': 'analyze',
        'thread_dump': None,
        'heap_summary': None,
        'hprof': None,
        'output': None,
        'mode': 'full'
    }

    # Simple argument parsing
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]

        if arg in ['--help', '-h']:
            args['command'] = 'help'
        elif arg == '--version':
            args['command'] = 'version'
        elif arg == '--thread-dump' and i + 1 < len(sys.argv):
            args['thread_dump'] = sys.argv[i + 1]
            i += 1
        elif arg == '--heap-summary' and i + 1 < len(sys.argv):
            args['heap_summary'] = sys.argv[i + 1]
            i += 1
        elif arg == '--hprof' and i + 1 < len(sys.argv):
            args['hprof'] = sys.argv[i + 1]
            i += 1
        elif arg == '--output' and i + 1 < len(sys.argv):
            args['output'] = sys.argv[i + 1]
            i += 1
        elif arg == '--mode' and i + 1 < len(sys.argv):
            args['mode'] = sys.argv[i + 1]
            i += 1
        elif arg == 'analyze':
            args['command'] = 'analyze'

        i += 1

    return args


def main():
    """Main entry point."""
    try:
        args = parse_args()
        cli = JVMDiagnosticsCLI()
        cli.run(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
