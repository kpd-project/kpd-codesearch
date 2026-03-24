"""Общая база: обход файлов, определение языка, игнор паттерны."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

import pathspec
import config


def _load_gitignore(repo_path: Path) -> pathspec.PathSpec | None:
    gitignore = repo_path / ".gitignore"
    if not gitignore.exists():
        return None
    lines = gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)

IGNORE_DIRS = {
    "node_modules", ".git", "target", "dist", "build", "out", ".idea",
    "__pycache__", ".next", ".nuxt", "coverage", ".cache",
    "vendor", "venv", ".venv", "env", ".env",
    ".gradle", ".m2", ".ivy2", ".npm", "e2e", "cypress",
}

IGNORE_FILENAMES = {
    "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "Gemfile.lock", "Cargo.lock", "poetry.lock", "composer.lock",
    "gradle.lockfile", "pubspec.lock",
}

IGNORE_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".lock", ".log", ".snap",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz", ".tgz", ".tar.gz",
    ".exe", ".dll", ".so", ".dylib", ".class", ".jar", ".war",
    ".pyc", ".pyo", ".bin", ".dat", ".db", ".sqlite",
}

# Расширение -> внутренний идентификатор
EXTENSION_TO_LANGUAGE = {
    ".java": "java",
    ".kt": "kotlin",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".vue": "vue",
    ".svelte": "svelte",
    ".py": "python",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".ps1": "powershell",
    ".dockerfile": "dockerfile",
}

# Языки с Tree-sitter (grammar name для treesitter-chunker)
SEMANTIC_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "java",
    "go",
    "rust",
    "ruby",
    "c",
    "cpp",
    "csharp",
    "php",
    "kotlin",
    "scala",
    "vue",
    "html",
    "css",
    "sql",
    "yaml",
    "json",
}

# Алиасы: наш язык -> treesitter-chunker grammar
TS_GRAMMAR_ALIAS = {
    "csharp": "c_sharp",
}


def should_ignore(path: Path) -> bool:
    name = path.name
    if name in IGNORE_DIRS:
        return True
    if name in IGNORE_FILENAMES:
        return True
    if any(name.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return True
    return False


def _classify_file(path: Path, repo_path: Path, gitignore) -> str | None:
    """Возвращает skip_reason или None (= indexed).

    Порядок проверок совпадает с iter_code_files — единый источник истины.
    """
    name = path.name
    if "node_modules" in path.parts:
        return "node_modules_path"
    if name in IGNORE_FILENAMES:
        return "ignored_name"
    if any(name.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return "ignored_extension"
    if gitignore is not None:
        rel = path.relative_to(repo_path).as_posix()
        if gitignore.match_file(rel):
            return "gitignore"
    if path.suffix.lower() not in EXTENSION_TO_LANGUAGE:
        return "unsupported_extension"
    return None


def get_language(path: Path) -> str:
    ext = path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "text")


def get_ts_grammar(lang: str) -> str:
    return TS_GRAMMAR_ALIAS.get(lang, lang)


def walk_repo_tree(repo_path: Path) -> dict:
    """Полный обход репозитория с классификацией каждого файла.

    Возвращает: { "tree": [Node, ...], "meta": { ... } }

    Узел (Node):
      type: "file" | "dir"
      name: str
      path: str  — POSIX, относительно repo_path
      extension: str | None  — для file, с точкой, lower
      indexed: bool | None   — true/false для file; false для IGNORE_DIRS-заглушки; null для обычной dir
      skip_reason: str | None
      children: list | None  — для dir; [] у заглушек IGNORE_DIRS
    """
    gitignore = _load_gitignore(repo_path)

    # trie-словарь: path_posix -> node_dict; корень — {"/": children_list}
    root_children: list = []
    dir_children_map: dict[str, list] = {"": root_children}

    indexed_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(repo_path, topdown=True):
        root_path = Path(root)
        root_rel = root_path.relative_to(repo_path).as_posix()
        parent_key = root_rel if root_rel != "." else ""
        parent_children = dir_children_map.get(parent_key, root_children)

        # Отсекаем IGNORE_DIRS — добавляем заглушки и убираем из обхода
        ignored = [d for d in dirs if d in IGNORE_DIRS]
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for d in sorted(ignored):
            dir_rel = (root_path / d).relative_to(repo_path).as_posix()
            node = {
                "type": "dir",
                "name": d,
                "path": dir_rel,
                "extension": None,
                "indexed": False,
                "skip_reason": "ignored_directory",
                "children": [],
            }
            parent_children.append(node)
            skipped_count += 1

        # Регистрируем обычные папки (чтобы их children заполнялись позже)
        for d in sorted(dirs):
            dir_rel = (root_path / d).relative_to(repo_path).as_posix()
            node: dict = {
                "type": "dir",
                "name": d,
                "path": dir_rel,
                "extension": None,
                "indexed": None,
                "skip_reason": None,
                "children": [],
            }
            parent_children.append(node)
            dir_children_map[dir_rel] = node["children"]

        # Файлы
        for f in sorted(files):
            file_path = root_path / f
            skip_reason = _classify_file(file_path, repo_path, gitignore)
            file_rel = file_path.relative_to(repo_path).as_posix()
            ext = file_path.suffix.lower() or None
            if skip_reason is None:
                indexed_count += 1
            else:
                skipped_count += 1
            node = {
                "type": "file",
                "name": f,
                "path": file_rel,
                "extension": ext,
                "indexed": skip_reason is None,
                "skip_reason": skip_reason,
                "children": None,
            }
            parent_children.append(node)

    return {
        "tree": root_children,
        "meta": {
            "repo": repo_path.name,
            "root_path": repo_path.as_posix(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "indexed_file_count": indexed_count,
            "skipped_file_count": skipped_count,
        },
    }


def iter_code_files(repo_path: Path) -> Iterator[Path]:
    """Файлы, которые войдут в индекс. Единственный источник истины — _classify_file."""
    gitignore = _load_gitignore(repo_path)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            path = Path(root) / f
            if _classify_file(path, repo_path, gitignore) is None:
                yield path


def read_file_content(path: Path, max_size: int = None) -> str:
    if max_size is None:
        max_size = config.FILE_MAX_SIZE
    try:
        if path.stat().st_size > max_size:
            return f"[File too large: {path.stat().st_size} bytes]"
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Error reading file: {e}]"
