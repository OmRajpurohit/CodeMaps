from pathlib import Path

from backend.app.ingestion.detector import language_detector


def test_language_detector_python_fixture():
    fixture_dir = Path("fixtures/python_project")
    structure = language_detector.scan_repository(fixture_dir)

    assert structure.total_files >= 7
    assert structure.primary_language == "Python"
    assert "Python" in structure.languages
    assert structure.total_loc > 0


def test_language_detector_ts_fixture():
    fixture_dir = Path("fixtures/ts_project")
    structure = language_detector.scan_repository(fixture_dir)

    assert structure.total_files >= 3
    assert structure.primary_language == "TypeScript"
    assert "TypeScript" in structure.languages
    assert structure.total_loc > 0
