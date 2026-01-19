# Quick Start Guide
## IFS JVM Diagnostics Copilot

Get started with JVM diagnostic analysis in 5 minutes.

---

## Installation

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Verify installation
python src/cli.py --version
```

## Basic Usage

### Scenario 1: Analyze a Thread Dump

```bash
python src/cli.py analyze --thread-dump examples/sample_thread_dump.txt
```

**What you get**:
- Thread state distribution
- Deadlock detection
- Lock contention analysis
- CPU-bound thread identification
- Human-readable report
- GitHub Copilot-ready prompt

### Scenario 2: Analyze Both Thread Dump and Heap Summary

```bash
python src/cli.py analyze \
  --thread-dump examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt \
  --output my_report.txt
```

**Output files**:
- `my_report.txt` - Human-readable diagnostic report
- `my_copilot_prompt.txt` - AI-ready prompt for GitHub Copilot

### Scenario 3: Handle .hprof Files

```bash
python src/cli.py analyze --hprof heap_dump.hprof
```

**Result**: Step-by-step guidance to export text summary from Eclipse MAT

---

## Demo with Sample Data

Run a complete demo using provided sample dumps:

```bash
# Navigate to project root
cd JVM

# Run analysis on sample data
python src/cli.py analyze \
  --thread-dump examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt \
  --output examples/demo_output.txt

# View the generated report
cat examples/demo_output.txt

# View the Copilot prompt
cat examples/demo_copilot_prompt.txt
```

---

## Typical Workflow

### Step 1: Capture JVM Dumps

When an incident occurs, capture diagnostic data:

```bash
# Thread dump
jstack <pid> > thread_dump.txt

# Heap dump
jmap -dump:format=b,file=heap.hprof <pid>
```

### Step 2: Export Heap Summary (if needed)

If you have a `.hprof` file:

1. Open Eclipse MAT
2. Load `heap.hprof`
3. Generate Histogram
4. Export as text → `heap_histogram.txt`

**Alternative**: Use `jmap` directly:
```bash
jmap -histo <pid> > heap_histogram.txt
```

### Step 3: Run Diagnostic Analysis

```bash
python src/cli.py analyze \
  --thread-dump thread_dump.txt \
  --heap-summary heap_histogram.txt \
  --output diagnostic_report.txt
```

### Step 4: Review Results

1. **Read the diagnostic report** (`diagnostic_report.txt`)
   - Executive summary
   - Detailed findings
   - Recommended actions

2. **Use Copilot prompt** for AI analysis
   - Open GitHub Copilot
   - Copy the generated prompt (`diagnostic_copilot_prompt.txt`)
   - Get AI-assisted root cause analysis

### Step 5: Take Action

Follow the recommended actions in the report:
- **Immediate**: Gather additional diagnostics
- **Short-term**: Safe mitigation steps
- **Long-term**: Code improvements

---

## Command Reference

### Basic Commands

```bash
# Show help
python src/cli.py --help

# Show version
python src/cli.py --version

# Analyze thread dump only
python src/cli.py analyze --thread-dump <file>

# Analyze heap summary only
python src/cli.py analyze --heap-summary <file>

# Analyze both
python src/cli.py analyze --thread-dump <file> --heap-summary <file>

# Save output to specific location
python src/cli.py analyze --thread-dump <file> --output <output-file>

# Generate summary only (no detailed report)
python src/cli.py analyze --thread-dump <file> --mode summary

# Generate Copilot prompt only
python src/cli.py analyze --thread-dump <file> --mode copilot
```

### Output Modes

- **`full`** (default): Complete report + Copilot prompt
- **`summary`**: Brief summary only
- **`copilot`**: Copilot prompt only

---

## Configuration

Edit `config/analysis_config.yaml` to customize thresholds:

```yaml
thread_analysis:
  blocked_threshold: 10          # Alert if >10 BLOCKED threads
  runnable_threshold: 50         # Alert if >50 RUNNABLE threads
  contention_threshold: 5        # Alert if >5 threads on same lock

heap_analysis:
  dominant_class_threshold: 0.3  # Alert if class uses >30% heap
  object_count_threshold: 1000000 # Alert if >1M instances
```

---

## Troubleshooting

### Issue: "File does not exist"
**Solution**: Check the file path is correct and accessible

### Issue: "Could not detect file type"
**Solution**: Ensure file contains valid thread dump or heap summary text

### Issue: "Large file warning"
**Solution**: Files >100MB may take longer to parse - this is expected

### Issue: ".hprof file detected"
**Solution**: Follow the provided guidance to export text summary from MAT

---

## Examples for Leadership Demo

### Quick Demo (2 minutes)

```bash
# Show the tool in action
python src/cli.py analyze \
  --thread-dump examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt

# Highlight:
# - Automatic issue detection
# - Clear severity levels
# - Actionable recommendations
# - AI-ready prompts
```

### Full Demo (5 minutes)

```bash
# 1. Show sample dumps
cat examples/sample_thread_dump.txt | head -50

# 2. Run analysis
python src/cli.py analyze \
  --thread-dump examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt \
  --output demo_report.txt

# 3. Show the report
cat demo_report.txt

# 4. Explain Copilot integration
cat demo_copilot_prompt.txt

# 5. Discuss value proposition:
#    - Time savings (manual analysis → automated)
#    - Structured evidence
#    - AI-ready for deeper insights
#    - Safe, read-only operation
```

---

## Next Steps

1. **Test with real dumps**: Use actual production thread/heap dumps
2. **Customize config**: Adjust thresholds for your environment
3. **Integrate with workflow**: Add to incident response runbook
4. **Gather feedback**: Share results with team for validation
5. **Plan Phase 2**: Based on Phase 1 experience

---

## Support

- **Documentation**: See `README.md` for detailed information
- **Sample data**: Check `examples/` directory
- **Configuration**: Edit `config/analysis_config.yaml`
- **Issues**: Contact IFS JVM Performance Engineering team

---

**Remember**: This tool is **read-only** and **safe** - it never modifies systems or automates actions. All recommendations require manual review and approval.
