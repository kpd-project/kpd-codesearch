from pydantic import BaseModel, Field
from typing import Optional


class SearchQuery(BaseModel):
    text: str = Field(description="Поисковый запрос для поиска в коде")
    repo: Optional[str] = Field(default=None, description="Репозиторий для поиска (имя коллекции в индексе) или null — по всем")
    top_k: Optional[int] = Field(default=None, description="Количество результатов")
    min_score: Optional[float] = Field(default=None, description="Минимальный порог релевантности (0-1)")


class AnalystResponse(BaseModel):
    queries: list[SearchQuery] = Field(description="Список поисковых запросов")
    analysis: str = Field(description="Анализ запроса пользователя: что ищем и почему")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Уверенность в поиске (0-1)")


class AnswererResponse(BaseModel):
    answer: Optional[str] = Field(default=None, description="Финальный ответ пользователю")
    need_more: bool = Field(default=False, description="Нужен ли дополнительный поиск")
    queries: Optional[list[SearchQuery]] = Field(default=None, description="Дополнительные запросы для поиска")
    hints: Optional[list[str]] = Field(default=None, description="Подсказки для Analyst при следующем поиске")


class SearchResult(BaseModel):
    content: str = Field(description="Содержимое чанка")
    path: str = Field(description="Путь к файлу")
    repo: str = Field(description="Название репозитория")
    language: str = Field(default="", description="Язык программирования")
    type: str = Field(default="", description="Тип элемента (function, class, etc)")
    score: float = Field(description="Релевантность результата")


class SummarizedContext(BaseModel):
    summary: str = Field(description="Сжатое описание найденного")
    citations: list[str] = Field(default_factory=list, description="Ключевые фрагменты кода")
    files_involved: list[str] = Field(default_factory=list, description="Затронутые файлы")
    confidence: float = Field(default=0.8, description="Уверенность в релевантности")


class PipelineState(BaseModel):
    iteration: int = Field(default=1, description="Текущая итерация")
    original_question: str = Field(description="Исходный вопрос пользователя")
    analyst_response: Optional[AnalystResponse] = Field(default=None)
    search_results: list[SearchResult] = Field(default_factory=list)
    summarized_context: Optional[SummarizedContext] = Field(default=None)
    answerer_response: Optional[AnswererResponse] = Field(default=None)
    total_tokens: dict = Field(default_factory=lambda: {"analyst": 0, "answerer": 0, "total": 0})