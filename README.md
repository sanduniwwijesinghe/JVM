# JVM Diagnostics Copilot

[![ci](https://github.com/sanduniwwijesinghe/jvm/actions/workflows/ci.yml/badge.svg)](https://github.com/sanduniwwijesinghe/jvm/actions/workflows/ci.yml)

A local, read-only CLI that turns **JVM thread dumps and heap histograms** captured during a
production incident into **structured RCA evidence**: deadlock cycles, lock-contention
hotspots with the holding thread, CPU-bound stacks, thread-pool saturation and memory-pressure
signals. It also writes an **AI-ready prompt** so the evidence can be handed to GitHub Copilot
(or any LLM) for a second opinion, without uploading the raw dump anywhere.

Built from on-call experience: during a P1, scrolling through a 5,000-line `jstack` output to
find out *who holds the lock* takes far longer than it should.

## What it finds

**Thread dumps** (`jstack`, `jcmd <pid> Thread.print`, `kill -3`; HotSpot / OpenJDK 8-21)
- Deadlocks: cycles in the thread *wait-for* graph, with the full cycle path
- Lock contention: locks with N+ waiters, the **holder thread** and its stack
- Lock chains vs. deadlocks (A waits on B waits on C is reported as contention, not as a deadlock)
- CPU-bound hotspots: common top frames across RUNNABLE threads
- Thread-state distribution and per-pool utilisation (e.g. `http-nio-8080-exec`)

**Heap summaries** (Eclipse MAT histogram export, `jmap -histo`)
- Dominant classes by share of heap
- Excessive object counts
- String / collection retention patterns

Every finding gets a severity (`CRITICAL` deadlock, `HIGH`/`MEDIUM` contention scaled by
waiter count, and so on), and the report ends with recommended actions that stay safe to run
manually.

## Quick start

```bash
pip install git+https://github.com/sanduniwwijesinghe/jvm
jvm-diag analyze --thread-dump examples/sample_deadlock_thread_dump.txt
```

From a clone:

```bash
git clone https://github.com/sanduniwwijesinghe/jvm && cd jvm
pip install -e ".[dev]"
pytest                                   # 16 tests

jvm-diag analyze \
  --thread-dump  examples/sample_thread_dump.txt \
  --heap-summary examples/sample_heap_summary.txt \
  --output       out/incident_report.txt
# -> out/incident_report.txt + out/incident_copilot_prompt.txt
```

Sample output (summary):

```
Severity: MEDIUM
Issues detected: 5

Top issues:
  - Lock contention: 5 threads waiting on java.util.concurrent.locks.ReentrantLock$NonfairSync
    <0x00000000d5e7e8a8>, held by 'Thread-2'
  - Excessive object retention: java.lang.String has 2,456,789 instances
  ...
```

## Options

| Option | Description |
|---|---|
| `--thread-dump PATH` | Thread dump text file |
| `--heap-summary PATH` | Eclipse MAT histogram export or `jmap -histo` output |
| `--hprof PATH` | Binary heap dump: prints instructions for exporting a histogram |
| `--output PATH` | Write the report here; the Copilot prompt goes next to it |
| `--mode full\|summary\|copilot` | Full report, executive summary only, or prompt only |
| `--config PATH` | Custom thresholds (see [`default_config.yaml`](src/jvm_diagnostics/default_config.yaml)) |

`python -m jvm_diagnostics ...` works too.

## Incident workflow

```bash
# 1. Capture evidence (2-3 thread dumps ~10 s apart show whether contention persists)
jcmd <pid> Thread.print -l > td1.txt
jcmd <pid> GC.class_histogram > histo.txt        # or: jmap -histo:live <pid>

# 2. Analyse locally
jvm-diag analyze --thread-dump td1.txt --heap-summary histo.txt --output rca/td1_report.txt

# 3. Review the report, then paste rca/td1_copilot_prompt.txt into Copilot Chat
```

For a binary `.hprof`, open it in Eclipse MAT, export **Histogram** as text, and pass that
file as `--heap-summary`. Parsing `.hprof` directly is out of scope on purpose (MAT does it
better).

## How it works

```
thread dump ─▶ ThreadDumpParser ─▶ ThreadInfo[] ─┬▶ DeadlockDetector   (cycle search on wait-for graph)
                                                 ├▶ ContentionDetector (waiters per lock + holder)
                                                 └▶ ThreadAnalyzer     (states, pools, CPU hotspots)
heap summary ─▶ HeapSummaryParser ─▶ HeapClassInfo[] ─▶ HeapAnalyzer   (dominance, counts, retention)
                                                 │
                                    DiagnosticEvidence (issues + severity + signals)
                                                 │
                          ┌──────────────────────┴───────────────────────┐
                    ReportGenerator                              CopilotPromptGenerator
                 (human-readable RCA report)                 (structured prompt for an LLM)
```

- **Wait-for graph**: an edge `A -> B` exists when thread A waits on a lock held by B.
  A cycle is a deadlock; a path without a cycle is a lock chain.
- **Header-aware heap parsing**: MAT column order is read from the header row, so exports with
  reordered columns still map Objects / Shallow / Retained correctly.

## Design principles

- **Local and read-only**: nothing leaves the laptop, nothing is changed on the JVM. Suitable
  for environments where dumps may contain customer data.
- **Evidence, not magic**: the LLM prompt contains extracted facts (counts, lock IDs, top
  frames), which keeps it small and makes the AI's answer checkable.
- **One dependency** (`pyyaml`), pure Python, Python 3.10+.

## Roadmap

- Compare several dumps over time (is the same lock still contended 30 s later?)
- JSON output for ingestion into incident tooling
- Virtual-thread (Loom) aware parsing for JDK 21+
- GC log analysis

## License

MIT. Sample dumps in `examples/` are synthetic.
