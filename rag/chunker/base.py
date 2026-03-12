"""Общая база: обход файлов, определение языка, игнор паттерны."""

import os
from pathlib import Path
from typing import Iterator

import pathspec


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


def get_language(path: Path) -> str:
    ext = path.suffix.lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "text")


def get_ts_grammar(lang: str) -> str:
    return TS_GRAMMAR_ALIAS.get(lang, lang)


def iter_code_files(repo_path: Path) -> Iterator[Path]:
    gitignore = _load_gitignore(repo_path)
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            path = Path(root) / f
            if "node_modules" in path.parts or should_ignore(path):
                continue
            if gitignore is not None:
                rel = path.relative_to(repo_path).as_posix()
                if gitignore.match_file(rel):
                    continue
            if path.suffix.lower() in EXTENSION_TO_LANGUAGE:
                yield path


def read_file_content(path: Path, max_size: int = 500_000) -> str:
    try:
        if path.stat().st_size > max_size:
            return f"[File too large: {path.stat().st_size} bytes]"
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"[Error reading file: {e}]"
