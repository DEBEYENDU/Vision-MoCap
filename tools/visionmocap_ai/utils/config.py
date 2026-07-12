from pathlib import Path
from dataclasses import dataclass, field


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
AI_DIR = PROJECT_ROOT / ".ai"
SRC_DIR = PROJECT_ROOT / "src"
TESTS_DIR = PROJECT_ROOT / "tests"
DOCS_DIR = PROJECT_ROOT / "docs"
TOOLS_DIR = PROJECT_ROOT / "tools"
PROMPTS_DIR = AI_DIR / "prompts"


@dataclass
class ToolConfig:
    project_root: Path = PROJECT_ROOT
    ai_dir: Path = AI_DIR
    src_dir: Path = SRC_DIR
    tests_dir: Path = TESTS_DIR
    docs_dir: Path = DOCS_DIR
    prompts_dir: Path = PROMPTS_DIR
    changelog: Path = PROJECT_ROOT / "CHANGELOG.md"
    roadmap: Path = PROJECT_ROOT / "ROADMAP.md"
    contributing: Path = PROJECT_ROOT / "CONTRIBUTING.md"
    project_status: Path = PROJECT_ROOT / "PROJECT_STATUS.md"
    known_bugs: Path = PROJECT_ROOT / "KNOWN_BUGS.md"
    test_plan: Path = PROJECT_ROOT / "TEST_PLAN.md"
    tasks: Path = PROJECT_ROOT / "TASKS.md"
    context_file: Path = AI_DIR / "CONTEXT.md"
    ai_instructions: Path = AI_DIR / "ai-instructions.md"
    system_overview: Path = AI_DIR / "system-overview.md"
    module_registry: Path = AI_DIR / "module-registry.md"
    data_model: Path = AI_DIR / "data-model.md"
    architecture_rules: Path = AI_DIR / "architecture-rules.md"
    file_map: Path = AI_DIR / "file-map.md"


config = ToolConfig()
