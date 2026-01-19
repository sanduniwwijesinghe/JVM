# IFS JVM Diagnostics Copilot

A **Phase-1 local diagnostics tool** for JVM performance analysis that helps reduce Root Cause Analysis (RCA) effort by extracting structured evidence from JVM dumps and generating AI-ready diagnostic prompts.

## Purpose

This tool is designed for IFS engineering teams to:
- Quickly analyze JVM thread dumps and heap summaries captured from production incidents
- Extract structured diagnostic evidence (deadlocks, contention, memory pressure)
- Generate GitHub Copilot-ready prompts for AI-assisted root cause analysis
- Produce human-readable diagnostic summaries for leadership demos

## Key Features

✅ **100% Local Execution** - Runs entirely on your laptop, no cloud dependencies
✅ **Read-Only & Safe** - No automated remediation, no infrastructure changes
✅ **Enterprise-Ready** - Designed for IFS operational constraints
✅ **Copilot Integration** - Generates structured prompts for GitHub Copilot
✅ **Demo-Friendly** - Clean, professional output for stakeholder presentations

## What It Analyzes

### Thread Dump Analysis
- Thread state distribution (RUNNABLE, BLOCKED, WAITING, TIMED_WAITING)
- Deadlock detection with full cycle paths
- Lock contention hotspots
- CPU-bound thread identification
- Thread pool exhaustion signals

### Heap Analysis
- Memory pressure indicators from summaries
- Dominant object classes
- Excessive object retention patterns
- Heap growth signals

## Architecture

```
┌─────────────────┐
│  JVM Dumps      │
│  - Thread dump  │──┐
│  - Heap summary │  │
│  - .hprof       │  │
└─────────────────┘  │
                     │  Parse & Extract
                     ▼
┌─────────────────────────────────┐
│  IFS JVM Diagnostics Copilot    │
│  - Thread analyzer              │
│  - Deadlock detector            │
│  - Contention analyzer          │
│  - Heap pressure analyzer       │
└─────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────┐
│  Structured Evidence            │
│  - Signals                      │
│  - Counts                       │
│  - Stack traces                 │
└─────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────┐
│  GitHub Copilot Prompt          │
│  + Human-Readable Report        │
└─────────────────────────────────┘
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd JVM

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Command

```bash
# Analyze a thread dump
python src/cli.py analyze --thread-dump /path/to/thread_dump.txt

# Analyze both thread dump and heap summary
python src/cli.py analyze \
  --thread-dump /path/to/thread_dump.txt \
  --heap-summary /path/to/heap_summary.txt

# Output to file
python src/cli.py analyze \
  --thread-dump /path/to/thread_dump.txt \
  --output /path/to/report.txt
```

### Handling .hprof Files

When you have a `.hprof` heap dump file, use the guidance command:

```bash
python src/cli.py analyze --hprof /path/to/heap_dump.hprof
```

This will:
1. Detect the `.hprof` file
2. Provide step-by-step instructions to export a text summary using Eclipse MAT
3. Wait for you to complete the export
4. Continue analysis with the exported summary

**Why not parse .hprof directly?**
Binary heap dump files are complex and require specialized tools like Eclipse MAT. This tool focuses on analyzing *text summaries* exported from MAT, keeping the implementation simple, maintainable, and aligned with existing IFS workflows.

### Example Workflow

```bash
# 1. Capture JVM dumps (existing IFS process)
#    - Thread dump: jstack <pid> > thread_dump.txt
#    - Heap dump: jmap -dump:format=b,file=heap.hprof <pid>

# 2. Export heap summary from Eclipse MAT
#    File -> Open Heap Dump -> heap.hprof
#    Generate "Histogram" report -> Export as text

# 3. Run diagnostic analysis
python src/cli.py analyze \
  --thread-dump thread_dump.txt \
  --heap-summary heap_histogram.txt \
  --output diagnostic_report.txt

# 4. Review the generated report and Copilot prompt
cat diagnostic_report.txt

# 5. Copy the Copilot prompt section to GitHub Copilot for AI reasoning
```

## Output Format

The tool generates two outputs:

### 1. Human-Readable Diagnostic Summary
```
JVM Diagnostic Summary
---------------------
Detected Issue: Deadlock detected with high thread contention
Severity: CRITICAL

Key Evidence:
- Deadlock involving 3 threads
- 45 threads in BLOCKED state
- Lock contention on java.util.concurrent.locks.ReentrantLock

Probable Root Cause:
- Thread-1 holds Lock-A, waiting for Lock-B
- Thread-2 holds Lock-B, waiting for Lock-A
- (High confidence - classic deadlock pattern)

Recommended Actions:
1. Immediate: Review thread dumps for lock ordering
2. Short-term: Implement lock timeout mechanisms
3. Long-term: Refactor to eliminate circular dependencies
```

### 2. GitHub Copilot Prompt
A structured prompt containing:
- JVM context and environment details
- Extracted evidence with thread traces
- Safety constraints for AI reasoning
- Request for root cause analysis

## Project Structure

```
ifs-jvm-diagnostics-copilot/
├── README.md                     # This file
├── requirements.txt              # Python dependencies
├── config/
│   └── analysis_config.yaml      # Analysis thresholds and rules
├── src/
│   ├── cli.py                    # Main CLI entry point
│   ├── models/
│   │   └── evidence.py           # Evidence data models
│   ├── parsers/
│   │   ├── thread_dump_parser.py # Thread dump parsing
│   │   └── heap_summary_parser.py# Heap summary parsing
│   ├── analyzers/
│   │   ├── thread_analyzer.py    # Thread state analysis
│   │   └── heap_analyzer.py      # Heap pressure analysis
│   ├── detectors/
│   │   ├── deadlock_detector.py  # Deadlock detection
│   │   └── contention_detector.py# Lock contention detection
│   ├── generators/
│   │   ├── copilot_prompt_generator.py  # Copilot prompt generation
│   │   └── report_generator.py   # Human-readable reports
│   └── utils/
│       └── file_handler.py       # File I/O and .hprof handling
├── templates/
│   └── copilot_prompt_template.txt  # Copilot prompt template
└── examples/
    ├── sample_thread_dump.txt    # Example thread dump
    ├── sample_heap_summary.txt   # Example heap summary
    └── demo_output.txt           # Example output

```

## Design Decisions

### 1. **Python-Based Implementation**
- **Why**: Simple, readable, excellent text processing libraries
- **Enterprise fit**: Widely available, low barrier to adoption

### 2. **No .hprof Binary Parsing**
- **Why**: Complex format, requires specialized libraries, high maintenance
- **Instead**: Detect .hprof files and guide users to export MAT summaries
- **Benefit**: Leverages existing IFS process (Eclipse MAT), keeps tool simple

### 3. **GitHub Copilot Integration**
- **Why**: Copilot is already approved and available in IFS
- **How**: Generate structured prompts that Copilot can reason about
- **Safety**: Prompts explicitly constrain Copilot to SAFE, MANUAL recommendations

### 4. **Read-Only Operation**
- **Why**: Enterprise safety, no risk of unintended changes
- **Scope**: Analysis only, no automated remediation

### 5. **Modular Architecture**
- **Why**: Easy to extend, test, and maintain
- **Benefit**: Can add new detectors/analyzers without touching core logic

## Configuration

Edit `config/analysis_config.yaml` to customize:

```yaml
thread_analysis:
  blocked_threshold: 10        # Alert if >10 BLOCKED threads
  runnable_threshold: 50       # Alert if >50 RUNNABLE threads
  contention_threshold: 5      # Alert if >5 threads on same lock

heap_analysis:
  dominant_class_threshold: 0.3  # Alert if class uses >30% heap
  object_count_threshold: 1000000 # Alert if >1M instances

severity_mapping:
  deadlock: CRITICAL
  high_contention: HIGH
  thread_exhaustion: HIGH
  memory_pressure: MEDIUM
```

## Testing with Sample Data

```bash
# Run with provided sample dumps
python src/cli.py analyze \
  --thread-dump examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt \
  --output examples/demo_output.txt
```

## Demo Preparation

For leadership demos:

1. **Prepare Sample Dumps**: Use examples/ directory or sanitized production dumps
2. **Run Analysis**: Execute CLI command
3. **Show Output**: Display the human-readable summary
4. **Highlight Value**:
   - Time saved (manual analysis → automated extraction)
   - Structured evidence for RCA
   - AI-ready prompts for deeper reasoning
5. **Discuss Next Steps**: Phase-2 enhancements based on feedback

## What This Tool Does NOT Do

❌ Parse .hprof binary files directly
❌ Integrate with Eclipse MAT or fastthread.io APIs
❌ Modify cloud infrastructure or AKS
❌ Perform automated remediation
❌ Restart services or change configurations
❌ Connect to production monitoring systems

## Limitations & Assumptions

- **Manual Dump Capture**: Assumes dumps are captured using existing IFS process
- **Text-Based Analysis**: Works with text exports, not binary formats
- **Single-Point-in-Time**: Analyzes individual dumps, not time-series data
- **Heuristic-Based**: Uses patterns and thresholds, not ML models
- **Local Only**: No remote execution or API calls

## Roadmap (Future Phases)

**Phase 2** (Based on Phase-1 Feedback):
- Multi-dump correlation (before/after comparison)
- Historical pattern recognition
- Custom rule definition UI
- Integration with IFS incident management

**Phase 3** (Future Consideration):
- VS Code extension for in-editor analysis
- Automated dump collection (if/when approved)
- Real-time monitoring integration (if/when approved)

## Support & Contribution

- **Issues**: Open an issue in the repository
- **Questions**: Contact the IFS JVM Performance Engineering team
- **Contributions**: Follow IFS contribution guidelines

## License

Internal use only - IFS Engineering

---

**Built with ❤️ by IFS JVM Performance Engineering Team**
**Designed for enterprise safety and operational excellence**
