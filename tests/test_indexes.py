import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_each_indexed_fiche_has_json():
    index = json.loads((ROOT / "data/indexes/fiches_cee_index.json").read_text(encoding="utf-8"))
    assert index
    for item in index:
        assert (ROOT / item["json_path"]).exists()


def test_chunks_have_required_metadata():
    path = ROOT / "data/indexes/chunks_cee.jsonl"
    assert path.exists()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        chunk = json.loads(line)
        for field in ["chunk_id", "code", "source_file", "document_type", "text"]:
            assert chunk.get(field)
