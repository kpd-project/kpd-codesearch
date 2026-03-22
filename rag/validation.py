"""Проверки пользовательского ввода до RAG."""


def validate_user_question(text: str | None) -> str | None:
    """None — можно искать; иначе текст ошибки для пользователя."""
    if text is None:
        return "Введите непустой вопрос."
    raw = str(text).strip()
    if not raw:
        return "Введите непустой вопрос."
    # без пробелов — оценка «одна буква/цифра подряд»
    compact = "".join(raw.split())
    if len(compact) < 2:
        return "Вопрос слишком короткий. Сформулируйте запрос по коду."
    if len(compact) >= 3 and len(set(compact)) <= 1:
        return "Нужен осмысленный запрос по коду, а не повтор одного символа."
    return None
