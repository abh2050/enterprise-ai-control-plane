"""Versioned price cards parsed from the official pricing page.

``cp pricecheck`` fetches the page, extracts the paid-tier standard prices for each
configured model, and writes ``configs/price_cards/<date>_<backend>.yaml`` with the
source URL, fetch time, and page hash. If a price cannot be parsed, it stops rather than
guess. Costs are integer micro dollars: one token at P USD per million tokens costs
exactly P micro dollars, so ``micros = tokens * price_per_million_usd``.
"""

from __future__ import annotations

import hashlib
import html
import math
import re
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from control_plane.triage.dataset import REPO_ROOT

PRICE_CARD_DIR = REPO_ROOT / "configs" / "price_cards"
PRICING_URLS = {
    "gemini_api": "https://ai.google.dev/gemini-api/docs/pricing",
    "vertex": "https://cloud.google.com/vertex-ai/generative-ai/pricing",
}

_MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


class PriceCheckError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelPrice:
    """Paid-tier standard prices in USD per million tokens."""

    input: Fraction
    output: Fraction  # includes thinking tokens
    cached_input: Fraction
    # Explicit context cache storage, USD per token per hour (0 when not priced).
    cache_storage_per_token_hour: Fraction = Fraction(0)

    def cost_micros(self, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> int:
        uncached = max(0, input_tokens - cached_tokens)
        exact = uncached * self.input + cached_tokens * self.cached_input
        exact += output_tokens * self.output
        return math.ceil(exact)

    def reservation_micros(
        self, counted_input_tokens: int, output_cap: int, cached_tokens: int = 0
    ) -> int:
        """Section 7: input tokens plus 10 percent and the full output cap, rounded up.

        ``counted_input_tokens`` is the uncached part; a cached prefix is reserved at the
        cached rate, also padded by 10 percent.
        """
        padded_input = math.ceil(counted_input_tokens * Fraction(11, 10))
        padded_cached = math.ceil(cached_tokens * Fraction(11, 10))
        return math.ceil(
            padded_input * self.input + padded_cached * self.cached_input + output_cap * self.output
        )

    def storage_micros(self, tokens: int, seconds: int) -> int:
        return math.ceil(
            tokens * Fraction(seconds, 3600) * self.cache_storage_per_token_hour * 1_000_000
        )


@dataclass(frozen=True)
class PriceCard:
    version: str
    backend: str
    source_url: str
    fetched_at: str
    prices: dict[str, ModelPrice]

    def price(self, model_id: str) -> ModelPrice:
        if model_id not in self.prices:
            raise PriceCheckError(f"price card {self.version} has no price for {model_id}")
        return self.prices[model_id]


def _page_text(raw: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", raw, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "\n", text))
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _parse_date(text: str) -> date:
    m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", text)
    if not m or m.group(1) not in _MONTHS:
        raise PriceCheckError(f"cannot parse date in {text!r}")
    return date(int(m.group(3)), _MONTHS[m.group(1)], int(m.group(2)))


def _effective_price(lines: list[str], on: date) -> tuple[Fraction, list[str]]:
    """Pick the text price in effect on ``on`` from lines like '$0.75 through ...'."""
    candidates = []
    for line in lines:
        m = re.match(r"\$(\d+(?:\.\d+)?)", line)
        if not m or "audio" in line or "storage" in line:
            continue
        value = Fraction(m.group(1))
        if "through" in line:
            if on <= _parse_date(line):
                candidates.append(value)
        elif "starting" in line:
            if on >= _parse_date(line):
                candidates.append(value)
        else:
            candidates.append(value)
    if len(candidates) != 1:
        raise PriceCheckError(f"expected one effective price, found {candidates} in {lines}")
    return candidates[0], lines


def _section_prices(text: str, model_id: str, on: date) -> tuple[ModelPrice, dict[str, Any]]:
    start = text.find(f"\n{model_id}\n")
    if start < 0:
        raise PriceCheckError(f"{model_id} not found on the pricing page")
    block = text[start:]
    standard = block.find("\nStandard\n")
    batch = block.find("\nBatch\n")
    if standard < 0 or batch < 0 or batch < standard:
        raise PriceCheckError(f"{model_id}: Standard and Batch sections not found in order")
    lines = block[standard:batch].splitlines()

    def field(label: str) -> tuple[Fraction, list[str]]:
        try:
            i = next(n for n, line in enumerate(lines) if line.startswith(label))
        except StopIteration as exc:
            raise PriceCheckError(f"{model_id}: '{label}' missing") from exc
        j = i + 1
        values = []
        while j < len(lines) and (
            lines[j].startswith("$") or lines[j] == "Free of charge" or lines[j] == "Not available"
        ):
            values.append(lines[j])
            j += 1
        paid = [v for v in values if v.startswith("$")]
        return _effective_price(paid, on)

    inp, inp_src = field("Input price")
    out, out_src = field("Output price")
    cached, cached_src = field("Context caching price")
    evidence = {"input": inp_src, "output": out_src, "context_caching": cached_src}
    return ModelPrice(inp, out, cached), evidence


# Vertex lists models by display name.
VERTEX_DISPLAY_NAMES = {
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash-Lite",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
}


def _vertex_section_prices(
    text: str, model_id: str, on: date, region: str = "Global"
) -> tuple[ModelPrice, dict[str, Any]]:
    """Standard (not Priority or Flex/Batch) table, <= 200K-token tier, one region."""
    display = VERTEX_DISPLAY_NAMES.get(model_id)
    if display is None:
        raise PriceCheckError(f"no Vertex display name for {model_id}")
    header = "\nModel\nType\nRegion\nPrice (/1M tokens)\n<= 200K input tokens\n"
    start = text.find(header)
    if start < 0:
        raise PriceCheckError("standard pricing table not found on the Vertex page")
    end = text.find("\nModel\nType\nRegion\n", start + len(header))
    lines = text[start:end].splitlines()
    heads = [i for i, line in enumerate(lines) if line.startswith("Gemini ")]
    chosen = []
    for n, i in enumerate(heads):
        if lines[i].rstrip("* ").strip() != display:
            continue
        block = lines[i : heads[n + 1] if n + 1 < len(heads) else len(lines)]
        tier = block[1] if len(block) > 1 else ""
        if tier.lower().startswith("through") and on > _parse_date(tier):
            continue
        if tier.lower().startswith("starting") and on < _parse_date(tier):
            continue
        chosen.append(block)
    if len(chosen) != 1:
        raise PriceCheckError(f"{model_id}: expected one price block for {on}, found {len(chosen)}")
    block = chosen[0]

    def row(prefix: str, count: int) -> list[str]:
        try:
            i = next(n for n, line in enumerate(block) if line.startswith(prefix))
            j = next(n for n in range(i + 1, len(block)) if block[n].rstrip("* ") == region)
        except StopIteration as exc:
            raise PriceCheckError(f"{model_id}: '{prefix}' / {region} row missing") from exc
        values = [v for v in block[j + 1 : j + 1 + count + 2] if v != "*"][:count]
        if len(values) != count:
            raise PriceCheckError(f"{model_id}: short row {values}")
        return values

    inp = row("Input (text", 4)
    out = row("Text output", 4)

    def money(v: str) -> Fraction:
        m = re.fullmatch(r"\$(\d+(?:\.\d+)?)", v)
        if not m:
            raise PriceCheckError(f"{model_id}: not a price: {v!r}")
        return Fraction(m.group(1))

    price = ModelPrice(input=money(inp[0]), output=money(out[0]), cached_input=money(inp[2]))
    evidence = {"block_header": block[:2], "region": region, "input_row": inp, "output_row": out}
    return price, evidence


def _vertex_storage_price(text: str, model_id: str) -> tuple[Fraction, list[str]]:
    """Context cache storage, USD per token-hour, <= 200K tier."""
    display = VERTEX_DISPLAY_NAMES[model_id].replace("-", " ")
    start = text.find("Context Cache Storage price for Explicit Caching")
    if start < 0:
        raise PriceCheckError("context cache storage table not found")
    lines = text[start : start + 4000].splitlines()
    for i, line in enumerate(lines):
        names = [n.strip().replace("-", " ") for n in line.split(",")]
        if display in names:
            value = lines[i + 1]
            m = re.fullmatch(r"\$(\d+(?:\.\d+)?)", value)
            if not m:
                raise PriceCheckError(f"{model_id}: storage price not parseable: {value!r}")
            return Fraction(m.group(1)), [line, value]
    raise PriceCheckError(f"{model_id}: no context cache storage price")


def fetch_price_card(backend: str, model_ids: list[str], on: date | None = None) -> Path:
    if backend not in PRICING_URLS:
        raise PriceCheckError(f"no pricing source for backend {backend}")
    url = PRICING_URLS[backend]
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310 (fixed https URL)
        raw = resp.read().decode("utf-8")
    return write_price_card(backend, url, raw, model_ids, on)


def write_price_card(
    backend: str, url: str, raw: str, model_ids: list[str], on: date | None = None
) -> Path:
    fetched = datetime.now(UTC)
    on = on or fetched.date()
    text = _page_text(raw)
    models: dict[str, Any] = {}
    parse = _vertex_section_prices if backend == "vertex" else _section_prices
    for model_id in model_ids:
        price, evidence = parse(text, model_id, on)
        models[model_id] = {
            "input_usd_per_million": str(price.input),
            "output_usd_per_million": str(price.output),
            "cached_input_usd_per_million": str(price.cached_input),
            "page_evidence": evidence,
        }
        if backend == "vertex":
            storage, storage_evidence = _vertex_storage_price(text, model_id)
            models[model_id]["cache_storage_usd_per_token_hour"] = str(storage)
            models[model_id]["page_evidence"]["cache_storage"] = storage_evidence
    version = f"{on.isoformat()}_{backend}"
    card = {
        "version": version,
        "backend": backend,
        "tier": "standard (not priority, flex, or batch); <= 200K input tokens"
        + ("; Global endpoint" if backend == "vertex" else "; paid tier"),
        "source_url": url,
        "fetched_at": fetched.isoformat(),
        "effective_on": on.isoformat(),
        "page_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "provenance": "MEASURED",
        "note": "List prices. Promotional credits-back offers on the page are ignored, so "
        "costs here are an upper bound on billed spend.",
        "models": models,
    }
    PRICE_CARD_DIR.mkdir(parents=True, exist_ok=True)
    path = PRICE_CARD_DIR / f"{version}.yaml"
    path.write_text(yaml.safe_dump(card, sort_keys=False))
    return path


def load_price_card(version: str | None = None, backend: str = "gemini_api") -> PriceCard:
    if version is None:
        cards = sorted(PRICE_CARD_DIR.glob(f"*_{backend}.yaml"))
        if not cards:
            raise PriceCheckError("no price card; run `cp pricecheck`")
        path = cards[-1]
    else:
        path = PRICE_CARD_DIR / f"{version}.yaml"
    data = yaml.safe_load(path.read_text())
    prices = {
        m: ModelPrice(
            Fraction(v["input_usd_per_million"]),
            Fraction(v["output_usd_per_million"]),
            Fraction(v["cached_input_usd_per_million"]),
            Fraction(v.get("cache_storage_usd_per_token_hour", "0")),
        )
        for m, v in data["models"].items()
    }
    return PriceCard(
        data["version"], data["backend"], data["source_url"], data["fetched_at"], prices
    )
