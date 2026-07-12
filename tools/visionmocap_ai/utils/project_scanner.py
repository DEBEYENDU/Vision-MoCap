import ast
import re
from pathlib import Path
from typing import List, Dict, Any


def find_python_files(root: Path) -> List[Path]:
    return list(root.rglob("*.py"))


def count_lines(filepath: Path) -> int:
    try:
        with open(filepath, encoding="utf-8") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def find_duplicated_code(root: Path) -> List[dict]:
    results = []
    files = find_python_files(root)
    seen_blocks: dict[str, list[tuple[Path, int]]] = {}
    for filepath in files:
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i in range(len(lines) - 4):
            block = "\n".join(lines[i : i + 5])
            if block.strip() and not block.startswith("#"):
                seen_blocks.setdefault(block, []).append((filepath, i + 1))
    for block, locations in seen_blocks.items():
        if len(locations) > 1:
            results.append({
                "type": "duplicated_code",
                "block": block[:80],
                "locations": [(str(p), l) for p, l in locations],
            })
    return results


def find_dead_code(root: Path) -> List[dict]:
    results = []
    for filepath in find_python_files(root):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_") and not node.name.startswith("__"):
                    continue
                if not _is_function_called(filepath, node.name):
                    results.append({
                        "type": "dead_code",
                        "file": str(filepath),
                        "name": node.name,
                        "line": node.lineno,
                    })
    return results


def _is_function_called(filepath: Path, name: str) -> bool:
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return True
    pattern = rf"(?<!def |class |\.)\b{re.escape(name)}\s*\("
    return bool(re.search(pattern, content))


def find_architecture_violations(root: Path) -> List[dict]:
    results = []
    layer_map = {
        "core": 0,
        "config": 1,
        "camera": 2,
        "pose": 2,
        "motion": 2,
        "recording": 2,
        "animation": 2,
        "blender": 2,
        "playback": 3,
        "gui": 4,
    }
    for filepath in find_python_files(root / "src"):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        rel = filepath.relative_to(root / "src")
        module = rel.parts[0]
        module_level = layer_map.get(module, -1)
        if module_level < 0:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if node.module and node.module.startswith("src."):
                        imported = node.module.split(".")[1]
                        imported_level = layer_map.get(imported, -1)
                        if imported_level > module_level:
                            results.append({
                                "type": "architecture_violation",
                                "file": str(filepath),
                                "line": node.lineno,
                                "detail": f"{module} imports {imported} (violates dependency direction)",
                            })
    return results


def find_missing_docs(root: Path) -> List[dict]:
    results = []
    for filepath in find_python_files(root / "src"):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    results.append({
                        "type": "missing_docstring",
                        "file": str(filepath),
                        "name": node.name,
                        "line": node.lineno,
                    })
    return results


def find_missing_tests(root: Path) -> List[dict]:
    results = []
    src_files = set(find_python_files(root / "src"))
    test_files = set(find_python_files(root / "tests"))
    for src_file in src_files:
        rel = src_file.relative_to(root / "src")
        test_name = f"test_{rel.stem}.py"
        test_path = root / "tests" / "unit" / test_name
        if not test_path.exists():
            results.append({
                "type": "missing_test",
                "file": str(src_file),
                "expected_test": str(test_path),
            })
    return results


def find_large_classes(root: Path, max_lines: int = 200) -> List[dict]:
    results = []
    for filepath in find_python_files(root / "src"):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                start = node.lineno
                end = node.end_lineno or start
                lines = end - start + 1
                if lines > max_lines:
                    results.append({
                        "type": "large_class",
                        "file": str(filepath),
                        "name": node.name,
                        "lines": lines,
                    })
    return results


def find_large_methods(root: Path, max_lines: int = 50) -> List[dict]:
    results = []
    for filepath in find_python_files(root / "src"):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.lineno
                end = node.end_lineno or start
                lines = end - start + 1
                if lines > max_lines:
                    results.append({
                        "type": "large_method",
                        "file": str(filepath),
                        "name": node.name,
                        "lines": lines,
                    })
    return results


def find_unused_imports(root: Path) -> List[dict]:
    results = []
    for filepath in find_python_files(root / "src"):
        try:
            tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
        except SyntaxError:
            continue
        content = filepath.read_text(encoding="utf-8")
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in (node.names if isinstance(node, ast.ImportFrom) else node.names):
                    name = alias.asname or alias.name
                    if name == "*":
                        continue
                    if name not in content.splitlines()[node.lineno - 1]:
                        continue
                    if not _is_name_used(content, name, node.lineno):
                        results.append({
                            "type": "unused_import",
                            "file": str(filepath),
                            "name": name,
                            "line": node.lineno,
                        })
    return results


def _is_name_used(content: str, name: str, exclude_line: int) -> bool:
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        if i == exclude_line:
            continue
        if name in line:
            return True
    return False


def find_todos_and_fixmes(root: Path) -> List[dict]:
    results = []
    for filepath in find_python_files(root / "src"):
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#") and "TODO" in stripped.upper():
                results.append({
                    "type": "todo",
                    "file": str(filepath),
                    "line": i,
                    "text": stripped.lstrip("# "),
                })
            if stripped.startswith("#") and "FIXME" in stripped.upper():
                results.append({
                    "type": "fixme",
                    "file": str(filepath),
                    "line": i,
                    "text": stripped.lstrip("# "),
                })
    return results


def scan_project(root: Path) -> dict:
    findings = []
    findings.extend(find_duplicated_code(root))
    findings.extend(find_dead_code(root))
    findings.extend(find_architecture_violations(root))
    findings.extend(find_missing_docs(root))
    findings.extend(find_missing_tests(root))
    findings.extend(find_large_classes(root))
    findings.extend(find_large_methods(root))
    findings.extend(find_unused_imports(root))
    findings.extend(find_todos_and_fixmes(root))
    return findings
