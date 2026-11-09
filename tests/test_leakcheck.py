import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "leakcheck.sh"


def run_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["sh", str(root / "scripts" / "leakcheck.sh")], cwd=root, text=True, capture_output=True)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    shutil.copy(SCRIPT, tmp_path / "scripts" / "leakcheck.sh")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    return tmp_path


def test_clean_and_allowlisted_addresses(repository: Path) -> None:
    (repository / "safe.txt").write_text("127.0.0.1 0.0.0.0\n")
    assert run_check(repository).returncode == 0


@pytest.mark.parametrize("content", ["192." + "168.1.5", "127.0.0.1 " + "192." + "168.1.5"])
def test_rejects_content(repository: Path, content: str) -> None:
    (repository / "sample.txt").write_text(content + "\n")
    result = run_check(repository)
    assert result.returncode != 0
    assert "sample.txt" in result.stdout


@pytest.mark.parametrize("private_path", ["/Users" + "/" + "example/file", "/root" + "/" + "example/file"])
@pytest.mark.parametrize("with_denylist", [False, True])
def test_rejects_private_paths(repository: Path, private_path: str, with_denylist: bool) -> None:
    if with_denylist:
        (repository / "scripts" / "leakcheck-denylist.txt").write_text("local-test-marker\n")
    (repository / "sample.txt").write_text(private_path + "\n")
    result = run_check(repository)
    assert result.returncode != 0
    assert "sample.txt" in result.stdout


def test_proc_root_allowlist_is_narrow(repository: Path) -> None:
    path = repository / "sample.txt"
    path.write_text("/proc/123/" + "root/file\n/proc/{pid}/" + "root/file\n")
    assert run_check(repository).returncode == 0
    path.write_text("/proc/123/" + "root/file " + "/root" + "/" + "secret\n")
    assert run_check(repository).returncode != 0
    path.write_text("/proc/not-a-pid/" + "root/file\n")
    assert run_check(repository).returncode != 0


def test_uses_local_denylist(repository: Path) -> None:
    (repository / "scripts" / "leakcheck-denylist.txt").write_text("local-test-marker\n")
    (repository / "sample.txt").write_text("local-test-marker\n")
    result = run_check(repository)
    assert result.returncode != 0
    assert "sample.txt" in result.stdout


def test_rejects_tracked_forbidden_file(repository: Path) -> None:
    (repository / "sample.dll").write_text("data")
    subprocess.run(["git", "add", "sample.dll"], cwd=repository, check=True)
    result = run_check(repository)
    assert result.returncode != 0
    assert "sample.dll" in result.stdout


def test_rejects_staged_content_even_if_working_tree_is_clean(repository: Path) -> None:
    (repository / "scripts" / "leakcheck-denylist.txt").write_text("local-test-marker\n")
    path = repository / "sample.txt"
    path.write_text("local-test-marker\n")
    subprocess.run(["git", "add", "sample.txt"], cwd=repository, check=True)
    path.write_text("safe\n")
    assert run_check(repository).returncode != 0
