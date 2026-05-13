from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_core_project_files_exist() -> None:
    assert (ROOT / "README.md").exists()
    assert (ROOT / "docker-compose.yml").exists()
    assert (ROOT / "frontend").exists()
    assert (ROOT / "backend").exists()
    assert (ROOT / "worker").exists()


def test_runtime_dirs_can_exist_or_be_created() -> None:
    for rel in [
        "data/db",
        "data/uploads",
        "data/thumbnails",
        "data/previews",
        "data/exports",
        "data/backups",
        "logs",
        "reports",
    ]:
        path = ROOT / rel
        path.mkdir(parents=True, exist_ok=True)
        assert path.exists()
