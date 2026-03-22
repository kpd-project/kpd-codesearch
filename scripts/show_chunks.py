"""
Демонстрация чанкинга: один файл целиком, все чанки с полным содержимым.
Запуск: python scripts/show_chunks.py
Результат: scripts/show_chunks_output.md
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from rag.chunker import chunk_file

# Небольшой файл — показываем целиком все чанки
REPO = "pdf-2"
FILE = "src/queue/worker.ts"


def main():
    base = config.REPOS_BASE_PATH
    path = base / REPO / FILE
    if not path.exists():
        print(f"Файл не найден: {path}")
        return

    chunks = chunk_file(path, REPO, base / REPO)
    out_path = Path(__file__).parent / "show_chunks_output.md"

    lines = []
    lines.append(f"# Чанкинг файла `{REPO}/{FILE}`")
    lines.append("")
    lines.append(f"**Всего чанков: {len(chunks)}**")
    lines.append("")
    lines.append("## Что это")
    lines.append("")
    lines.append("Tree-sitter режет файл по узлам AST. Каждый узел = отдельный чанк:")
    lines.append("- `import_statement` — каждый импорт")
    lines.append("- `export_statement` + `function_declaration` — часто дублируют друг друга (export обёртка)")
    lines.append("- `variable_declarator` — присваивания, в т.ч. внутри функций (слишком мелко)")
    lines.append("- `arrow_function` — callback целиком (норм)")
    lines.append("")
    lines.append("**Проблема:** чанков слишком много, есть дубли. Для RAG лучше оставлять только топ-уровень: импорты, экспорты, функции/классы целиком.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for i, c in enumerate(chunks, 1):
        meta = c["metadata"]
        content = c["content"]
        node_type = meta.get("type", "?")
        lang = meta.get("language", "")

        lines.append(f"## Чанк {i} — `{node_type}`")
        lines.append("")
        lines.append("```")
        lines.append(content.rstrip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Результат записан в: {out_path.absolute()}")
    print(f"Чанков: {len(chunks)}")
    for i, c in enumerate(chunks, 1):
        print(f"  {i}. {c['metadata'].get('type', '?')} ({len(c['content'])} символов)")


if __name__ == "__main__":
    main()
