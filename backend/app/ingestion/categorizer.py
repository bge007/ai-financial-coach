"""Transaction auto-categorization: rules first, OpenRouter LLM fallback."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable, Awaitable

import yaml
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Category
from app.models.category_rule import CategoryRule
from app.models.category_cache import CategoryCache

from app.core.paths import config_path

_CONFIG_PATH = config_path("category_rules.yaml")

VALID_CATEGORIES = {c.value for c in Category}

LLMBatchFn = Callable[[list[str]], Awaitable[dict[int, str]]]


class LLMCategoryBatch(BaseModel):
    """Strict JSON shape expected from the LLM fallback."""

    categories: dict[str, str] = Field(default_factory=dict)


def normalize_description(description: str) -> str:
    text = (description or "").upper()
    text = re.sub(r"\s+", " ", text).strip()
    return text


def description_hash(description: str) -> str:
    return hashlib.sha256(normalize_description(description).encode("utf-8")).hexdigest()


def load_global_rules(path: Path | None = None) -> list[dict[str, Any]]:
    cfg = path or _CONFIG_PATH
    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    rules = data.get("rules") or []
    # Sort descending priority so first match wins when iterating.
    return sorted(rules, key=lambda r: int(r.get("priority", 0)), reverse=True)


def _compile_patterns(patterns: list[str]) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error:
            continue
    return compiled


class Categorizer:
    """Two-stage categorizer: YAML/DB rules, then batched LLM with cache."""

    def __init__(
        self,
        global_rules: list[dict[str, Any]] | None = None,
        llm_batch: LLMBatchFn | None = None,
    ):
        self.global_rules = global_rules if global_rules is not None else load_global_rules()
        self._compiled_global: list[tuple[Category, int, list[re.Pattern[str]]]] = []
        for rule in self.global_rules:
            cat = rule.get("category")
            if cat not in VALID_CATEGORIES:
                continue
            pats = _compile_patterns(list(rule.get("patterns") or []))
            if pats:
                self._compiled_global.append(
                    (Category(cat), int(rule.get("priority", 0)), pats)
                )
        self.llm_batch = llm_batch

    def match_rules(
        self,
        description: str,
        user_rules: list[CategoryRule] | None = None,
    ) -> Category | None:
        normalized = normalize_description(description)

        # User rules (manual corrections) always win — sorted by priority desc.
        for rule in sorted(user_rules or [], key=lambda r: r.priority, reverse=True):
            try:
                if re.search(rule.pattern, normalized, re.IGNORECASE):
                    return Category(rule.category)
            except re.error:
                continue

        for category, _prio, patterns in self._compiled_global:
            for pat in patterns:
                if pat.search(normalized):
                    return category
        return None

    async def categorize_many(
        self,
        descriptions: list[str],
        db: AsyncSession,
        user_id: int,
        *,
        use_llm: bool = True,
    ) -> list[Category]:
        """Categorize a list of descriptions; returns one Category per input."""
        if not descriptions:
            return []

        user_rules = await self._load_user_rules(db, user_id)
        results: list[Category | None] = [None] * len(descriptions)
        need_llm: list[tuple[int, str]] = []

        # Stage 1: rules
        for i, desc in enumerate(descriptions):
            hit = self.match_rules(desc, user_rules)
            if hit is not None:
                results[i] = hit
            else:
                need_llm.append((i, desc))

        if not need_llm or not use_llm:
            return [r or Category.other for r in results]

        # Stage 1.5: cache lookup for remaining
        still_need: list[tuple[int, str]] = []
        for i, desc in need_llm:
            cached = await self._cache_get(db, description_hash(desc))
            if cached is not None:
                results[i] = cached
            else:
                still_need.append((i, desc))

        if not still_need or self.llm_batch is None:
            return [r or Category.other for r in results]

        # Stage 2: LLM in batches of 50
        for batch_start in range(0, len(still_need), 50):
            batch = still_need[batch_start : batch_start + 50]
            descs = [d for _, d in batch]
            try:
                mapping = await self.llm_batch(descs)
            except Exception:
                mapping = {}

            for local_idx, (orig_i, desc) in enumerate(batch):
                raw = mapping.get(local_idx) or mapping.get(str(local_idx))  # type: ignore[arg-type]
                cat = self._coerce_category(raw)
                results[orig_i] = cat
                await self._cache_put(db, description_hash(desc), cat)

        await db.commit()
        return [r or Category.other for r in results]

    async def categorize_one(
        self,
        description: str,
        db: AsyncSession,
        user_id: int,
        *,
        use_llm: bool = True,
    ) -> Category:
        cats = await self.categorize_many([description], db, user_id, use_llm=use_llm)
        return cats[0]

    @staticmethod
    def _coerce_category(raw: Any) -> Category:
        if raw is None:
            return Category.other
        text = str(raw).strip().lower()
        if text in VALID_CATEGORIES:
            return Category(text)
        return Category.other

    @staticmethod
    async def _load_user_rules(db: AsyncSession, user_id: int) -> list[CategoryRule]:
        result = await db.execute(
            select(CategoryRule).where(
                (CategoryRule.user_id == user_id) | (CategoryRule.user_id.is_(None))
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def _cache_get(db: AsyncSession, digest: str) -> Category | None:
        row = await db.get(CategoryCache, digest)
        if row is None:
            return None
        if row.category in VALID_CATEGORIES:
            return Category(row.category)
        return Category.other

    @staticmethod
    async def _cache_put(db: AsyncSession, digest: str, category: Category) -> None:
        existing = await db.get(CategoryCache, digest)
        if existing is None:
            db.add(CategoryCache(description_hash=digest, category=category.value))
        else:
            existing.category = category.value


def parse_llm_category_json(raw: str, batch_size: int) -> dict[int, str]:
    """Parse LLM JSON into {index: category}; invalid → empty / skipped."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    # Accept either {"0": "dining", ...} or {"categories": {...}}
    if isinstance(data, dict) and "categories" in data:
        try:
            validated = LLMCategoryBatch.model_validate(data)
            data = validated.categories
        except ValidationError:
            return {}

    if not isinstance(data, dict):
        return {}

    out: dict[int, str] = {}
    for k, v in data.items():
        try:
            idx = int(k)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < batch_size:
            out[idx] = str(v)
    return out


async def default_openrouter_batch(descriptions: list[str]) -> dict[int, str]:
    """Call OpenRouter for category labels. Returns {} if unconfigured/fails."""
    from app.core.config import get_settings
    from openai import AsyncOpenAI

    settings = get_settings()
    if not settings.openrouter_api_key:
        return {}

    client = AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        default_headers={
            "HTTP-Referer": settings.frontend_url,
            "X-Title": "MoneyMitra",
        },
    )
    numbered = "\n".join(f"{i}: {d}" for i, d in enumerate(descriptions))
    allowed = ", ".join(sorted(VALID_CATEGORIES))
    prompt = (
        "Categorize each bank-transaction description into exactly one category.\n"
        f"Allowed categories: {allowed}\n"
        "Return ONLY JSON of the form {\"0\": \"dining\", \"1\": \"rent\", ...} "
        "with integer string keys matching the input indices. No prose.\n\n"
        f"{numbered}"
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
    except Exception:
        return {}
    return parse_llm_category_json(content, len(descriptions))


def make_default_categorizer() -> Categorizer:
    return Categorizer(llm_batch=default_openrouter_batch)
