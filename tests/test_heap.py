from jvm_diagnostics.analyzers.heap_analyzer import HeapAnalyzer
from jvm_diagnostics.parsers.heap_summary_parser import HeapSummaryParser


def test_mat_histogram_columns_follow_header(mat_histogram):
    parser = HeapSummaryParser()
    classes = parser.parse_file(str(mat_histogram))

    string = parser.find_class_by_name("java.lang.String")
    assert string.instance_count == 2_456_789  # "Objects" column, not retained heap
    assert string.shallow_heap == 98_271_560
    assert string.retained_heap == 234_567_890
    assert len(classes) == 20


def test_mat_histogram_any_column_order():
    text = (
        "Class Name | Shallow Heap | Retained Heap | Objects\n"
        "com.example.Big | 500 | 900 | 7\n"
    )
    (hc,) = HeapSummaryParser().parse_text(text)
    assert (hc.instance_count, hc.shallow_heap, hc.retained_heap) == (7, 500, 900)


def test_heap_size_prefers_explicit_heap_size(mat_histogram):
    parser = HeapSummaryParser()
    parser.parse_file(str(mat_histogram))
    assert parser.total_heap_size == 1024 * 1024 * 1024  # "Heap Size: 1024 MB"


def test_jmap_histo_format():
    text = (
        " num     #instances         #bytes  class name (module)\n"
        "-------------------------------------------------------\n"
        "   1:       1500000      120000000  [B (java.base@17.0.9)\n"
        "   2:        300000        7200000  java.lang.String (java.base@17.0.9)\n"
        "Total       1800000      127200000\n"
    )
    classes = HeapSummaryParser().parse_text(text)
    assert [c.instance_count for c in classes] == [1_500_000, 300_000]
    assert classes[0].class_name.startswith("[B")


def test_heap_analyzer_flags_excessive_objects(mat_histogram):
    evidence = HeapAnalyzer({"object_count_threshold": 1_000_000}).analyze_heap_summary(
        str(mat_histogram)
    )
    flagged = [i for i in evidence.detected_issues if "Excessive object retention" in i]
    assert len(flagged) == 3  # String, char[], HashMap$Node
    assert any("java.lang.String has 2,456,789 instances" in i for i in flagged)


def test_dominant_class_detected():
    text = (
        "Heap Size: 100 MB\n"
        "Class Name | Objects | Shallow Heap | Retained Heap\n"
        "com.example.LeakyCache | 10 | 41943040 | 41943040\n"
        "java.lang.String | 10 | 1048576 | 1048576\n"
    )
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
        fh.write(text)
    evidence = HeapAnalyzer({"dominant_class_threshold": 0.3}).analyze_heap_summary(fh.name)
    assert evidence.heap_pressure
    assert [c.class_name for c in evidence.dominant_classes] == ["com.example.LeakyCache"]
