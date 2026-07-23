#!/usr/bin/env python3
"""Build the static AI intelligence snapshot used by ai-news.html.

This collector discovers signals; ``build_readers.py`` then fetches public page
text and open-access PDFs into the site's reading cache. Individual source
failures are recorded instead of aborting the entire update.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "ai-news.json"
NOW = datetime.now(timezone.utc)
USER_AGENT = "Linyouxue-AI-Signal/1.0 (+https://linyouxue.github.io/ai-news.html)"
TIMEOUT = 28

CATEGORY_LIMITS = {
    "research": 20,
    "impact": 16,
    "frontier": 16,
    "china": 16,
    "voices": 14,
    "bigtech": 14,
    "startups": 14,
    "opensource": 12,
    "policy": 10,
}

IMPACT_KEYWORDS = {
    "conjecture", "theorem", "proof", "mathematics", "math problem", "scientific discovery",
    "protein", "genome", "biology", "drug discovery", "medicine", "medical", "disease",
    "materials science", "battery material", "chemistry", "physics", "climate", "weather forecast",
    "数学", "猜想", "定理", "证明", "生物", "蛋白质", "药物", "医疗", "材料", "物理", "气候",
}

PEOPLE_WATCHLIST = {
    "Elon Musk / xAI": ["elon musk", "@elonmusk", "xai", "grok"],
    "Sam Altman / OpenAI": ["sam altman", "@sama"],
    "Dario Amodei / Anthropic": ["dario amodei"],
    "Demis Hassabis / DeepMind": ["demis hassabis"],
    "Yann LeCun / AMI": ["yann lecun", "@ylecun"],
    "梁文锋 / DeepSeek": ["梁文锋", "liang wenfeng"],
    "杨植麟 / 月之暗面": ["杨植麟", "yang zhilin"],
}

CHINA_WATCHLIST = {
    "Kimi / 月之暗面": ["kimi", "moonshot", "月之暗面"],
    "Qwen / 通义千问": ["qwen", "通义千问", "阿里云百炼"],
    "腾讯元宝 / 混元": ["腾讯元宝", "yuanbao", "hunyuan", "混元", "tencent hy"],
    "智谱 / Z.ai": ["智谱", "zhipu", "z.ai", "glm-"],
    "DeepSeek": ["deepseek"],
    "字节豆包 / Seed": ["字节", "bytedance", "doubao", "豆包", "seedance", "seedream", "seed2"],
}

OFFICIAL_FEEDS = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/news/rss.xml",
        "category": "frontier",
        "tags": ["OpenAI", "Official"],
        "limit": 9,
        "official": True,
    },
    {
        "name": "Google DeepMind",
        "url": "https://deepmind.google/blog/rss.xml",
        "category": "frontier",
        "tags": ["DeepMind", "Official"],
        "limit": 8,
        "official": True,
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "category": "bigtech",
        "tags": ["Google", "Official"],
        "limit": 7,
        "official": True,
    },
    {
        "name": "Microsoft Research",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "category": "bigtech",
        "tags": ["Microsoft", "Research"],
        "limit": 6,
        "official": True,
    },
    {
        "name": "NVIDIA AI",
        "url": "https://blogs.nvidia.com/blog/category/deep-learning/feed/",
        "category": "bigtech",
        "tags": ["NVIDIA", "Infrastructure"],
        "limit": 6,
        "official": True,
    },
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "opensource",
        "tags": ["Hugging Face", "Open Source"],
        "limit": 7,
        "official": True,
    },
]

NEWS_QUERIES = [
    {
        "name": "AI for Mathematics & Science",
        "query": '(AI OR "language model") (conjecture OR theorem OR proof OR "scientific discovery" OR mathematics OR physics) when:30d',
        "category": "impact",
        "tags": ["AI for Science", "Mathematics", "Discovery"],
        "limit": 12,
    },
    {
        "name": "AI for Biology, Medicine & Materials",
        "query": '(AI OR "foundation model") (biology OR protein OR medicine OR "drug discovery" OR materials OR climate) (discovery OR experiment OR breakthrough) when:30d',
        "category": "impact",
        "tags": ["AI for Science", "Biology", "Applied AI"],
        "limit": 12,
    },
    {
        "name": "Academic Startup Radar",
        "query": '("AI startup" OR "AI spinout") (professor OR Stanford OR MIT OR Berkeley OR university) when:30d',
        "category": "startups",
        "tags": ["Academic Startup", "Funding"],
        "limit": 10,
    },
    {
        "name": "World Model Founders",
        "query": '("World Labs" OR "Fei-Fei Li" OR "Physical Intelligence") (startup OR funding OR launches) when:60d',
        "category": "startups",
        "tags": ["Founder Watch", "Embodied AI"],
        "limit": 7,
    },
    {
        "name": "Frontier Lab Monitor",
        "query": '(OpenAI OR Anthropic OR Claude OR xAI OR "Meta AI") (model OR research OR launch OR partnership) when:14d',
        "category": "frontier",
        "tags": ["Frontier Labs", "Industry"],
        "limit": 9,
    },
    {
        "name": "AI Policy Monitor",
        "query": '("AI regulation" OR "AI safety" OR "AI Act" OR "AI copyright") when:21d',
        "category": "policy",
        "tags": ["Policy", "Safety"],
        "limit": 10,
    },
    {
        "name": "Open Source AI Monitor",
        "query": '("open-source AI" OR "open weight model" OR vLLM OR "Hugging Face") when:21d',
        "category": "opensource",
        "tags": ["Open Source", "Models & Tools"],
        "limit": 8,
    },
    {
        "name": "China AI · Kimi & Qwen",
        "query": '(Kimi OR "Moonshot AI" OR 月之暗面 OR Qwen OR 通义千问) (model OR 模型 OR release OR 发布 OR API OR funding) when:30d',
        "category": "china",
        "tags": ["Kimi", "Qwen", "China AI"],
        "limit": 10,
    },
    {
        "name": "China AI · DeepSeek & Zhipu",
        "query": '(DeepSeek OR 智谱 OR Zhipu OR "Z.ai" OR GLM) (model OR 模型 OR release OR 发布 OR open-source) when:30d',
        "category": "china",
        "tags": ["DeepSeek", "Zhipu", "China AI"],
        "limit": 10,
    },
    {
        "name": "China AI · Tencent & ByteDance",
        "query": '(腾讯元宝 OR "Tencent Yuanbao" OR 腾讯混元 OR Hunyuan OR 豆包 OR Doubao OR "ByteDance Seed") (AI OR model OR 模型 OR 发布) when:30d',
        "category": "china",
        "tags": ["Tencent", "ByteDance", "China AI"],
        "limit": 10,
    },
    {
        "name": "Founder & Researcher Posts on X",
        "query": '(site:x.com/elonmusk OR site:x.com/sama OR site:x.com/demishassabis OR site:x.com/ylecun OR site:x.com/__alpoge__) (AI OR model OR research OR Grok OR OpenAI OR DeepMind OR Claude) when:21d',
        "category": "voices",
        "tags": ["X", "Founder Watch", "First-party Post"],
        "limit": 12,
    },
    {
        "name": "China AI Social Monitor",
        "query": '(site:weibo.com OR site:mp.weixin.qq.com OR site:zhihu.com) (Kimi OR 月之暗面 OR Qwen OR 通义千问 OR 腾讯元宝 OR 智谱 OR DeepSeek OR 豆包) (模型 OR AI OR 发布 OR 开源) when:30d',
        "category": "china",
        "tags": ["中国社交媒体", "公开动态", "China AI"],
        "limit": 12,
    },
]

REPUTABLE_PUBLISHERS = {
    "reuters", "associated press", "bloomberg", "financial times", "techcrunch",
    "the verge", "wired", "mit technology review", "cnbc", "venturebeat",
    "nature", "science", "the new york times", "wall street journal",
}


@dataclass
class SourceStatus:
    name: str
    status: str
    count: int = 0
    note: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "count": self.count, "note": self.note}


class PageMetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {str(key).lower(): value or "" for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta":
            key = (attrs_map.get("property") or attrs_map.get("name") or "").lower()
            if key and attrs_map.get("content"):
                self.meta[key] = attrs_map["content"]

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

    @property
    def title(self) -> str:
        return clean_text(" ".join(self._title_parts))


def request_bytes(url: str, attempts: int = 2) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json, application/xml, text/xml, application/rss+xml, text/html;q=0.9, */*;q=0.7",
                },
            )
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read()
        except Exception as error:  # Source failures should not stop other sources.
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(str(last_error or "request failed"))


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def shorten(value: str, limit: int = 680) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    clipped = value[: limit + 1]
    boundary = max(clipped.rfind(". "), clipped.rfind("。"), clipped.rfind("; "), clipped.rfind(" "))
    if boundary < int(limit * 0.62):
        boundary = limit
    return clipped[:boundary].rstrip(" ,;:") + "…"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def first_child_text(element: ET.Element, names: Iterable[str]) -> str:
    targets = {name.lower() for name in names}
    for child in element.iter():
        if child is element:
            continue
        if local_name(child.tag) in targets and child.text:
            return child.text.strip()
    return ""


def entry_link(element: ET.Element) -> str:
    for child in element.iter():
        if local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href.strip()
        if child.text and child.text.strip().startswith("http"):
            return child.text.strip()
    return first_child_text(element, ["guid"])


def parse_datetime(value: Any) -> datetime | None:
    raw = clean_text(value)
    if not raw:
        return None
    try:
        date = parsedate_to_datetime(raw)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        pass
    normalized = raw.replace("Z", "+00:00")
    try:
        date = datetime.fromisoformat(normalized)
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        return date.astimezone(timezone.utc)
    except ValueError:
        return None


def iso_or_now(value: Any) -> str:
    date = parse_datetime(value) or NOW
    return date.isoformat(timespec="seconds").replace("+00:00", "Z")


def item_id(url: str, title: str) -> str:
    return hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def normalized_title(title: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", title.lower())


def publisher_priority(source: str) -> int:
    lowered = source.lower()
    return 8 if any(name in lowered for name in REPUTABLE_PUBLISHERS) else 0


def classify_item(default: str, title: str, summary: str, tags: Iterable[str] = ()) -> str:
    """Promote concrete cross-domain results and first-party posts into their own lanes."""
    haystack = " ".join([title, summary, *tags]).lower()
    if default in {"frontier", "bigtech"} and any(keyword in haystack for keyword in IMPACT_KEYWORDS):
        return "impact"
    if default == "frontier" and any(marker in haystack for marker in ("site:x.com", "first-party post")):
        return "voices"
    return default


def score_item(category: str, published_at: str, official: bool = False, indexed: bool = False, source: str = "") -> int:
    base = {"impact": 70, "research": 66, "frontier": 64, "china": 63, "voices": 62, "startups": 61, "bigtech": 57, "policy": 54, "opensource": 52}.get(category, 50)
    date = parse_datetime(published_at)
    age_days = max(0.0, (NOW - date).total_seconds() / 86400) if date else 90
    freshness = max(0, round(18 - min(age_days, 90) / 5))
    return base + freshness + (18 if official else 0) + (12 if indexed else 0) + publisher_priority(source)


def make_item(
    *, title: str, summary: str, source: str, url: str, published_at: Any,
    category: str, tags: list[str] | None = None, official: bool = False,
    indexed: bool = False, authors: list[str] | None = None, venue: str = "",
    pdf_url: str = "", license_name: str = "", content_kind: str = "",
    verification: str = "",
) -> dict[str, Any] | None:
    title, url = clean_text(title), clean_text(url)
    if len(title) < 5 or not url.startswith(("http://", "https://")):
        return None
    date_iso = iso_or_now(published_at)
    clean_summary = shorten(summary)
    if len(clean_summary) < 32:
        clean_summary = f"来自 {source} 的最新更新。点击查看原始来源、完整内容与上下文。"
    identifier = item_id(url, title)
    normalized_tags = [clean_text(tag) for tag in (tags or []) if clean_text(tag)][:4]
    category = classify_item(category, title, clean_summary, normalized_tags)
    if not content_kind:
        social_hosts = ("x.com", "twitter.com", "weibo.com", "zhihu.com", "mp.weixin.qq.com")
        content_kind = "paper" if category == "research" else "social" if any(host in url.lower() for host in social_hosts) else "article"
    if not verification:
        verification = "论文索引" if indexed else "官方来源" if official else "公开社交原帖" if content_kind == "social" else "媒体或公开网页"
    payload = {
        "id": identifier,
        "category": category,
        "title": title,
        "summary": clean_summary,
        "source": clean_text(source) or "Original source",
        "url": url,
        "published_at": date_iso,
        "tags": normalized_tags,
        "importance": score_item(category, date_iso, official=official, indexed=indexed, source=source),
        "content_kind": content_kind,
        "verification": verification,
        "reader_url": f"./reader.html?id={identifier}",
    }
    if authors:
        payload["authors"] = [clean_text(author) for author in authors if clean_text(author)][:5]
    if venue:
        payload["venue"] = clean_text(venue)
    if pdf_url.startswith(("http://", "https://")):
        payload["pdf_url"] = pdf_url
    if license_name:
        payload["license"] = clean_text(license_name)
    return payload


def fetch_feed(source: dict[str, Any], use_entry_source: bool = False) -> tuple[list[dict[str, Any]], SourceStatus]:
    try:
        root = ET.fromstring(request_bytes(source["url"]))
        entries = [element for element in root.iter() if local_name(element.tag) in {"item", "entry"}]
        items: list[dict[str, Any]] = []
        for entry in entries[: source.get("limit", 8) * 2]:
            title = first_child_text(entry, ["title"])
            link = entry_link(entry)
            description = first_child_text(entry, ["description", "summary", "content", "encoded"])
            published = first_child_text(entry, ["pubdate", "published", "updated", "date"])
            entry_source = first_child_text(entry, ["source"]) if use_entry_source else ""
            publisher = clean_text(entry_source) or source["name"]
            if entry_source and title.endswith(f" - {publisher}"):
                title = title[: -(len(publisher) + 3)].rstrip()
            source_tags = source.get("tags", [])
            social_signal = any(tag in {"X", "First-party Post", "中国社交媒体", "公开动态"} for tag in source_tags)
            item = make_item(
                title=title,
                summary=description,
                source=publisher,
                url=link,
                published_at=published,
                category=source["category"],
                tags=source_tags,
                official=bool(source.get("official")),
                content_kind="social" if social_signal else "",
                verification="公开平台索引，需查看原帖" if social_signal else "",
            )
            if item:
                items.append(item)
            if len(items) >= source.get("limit", 8):
                break
        return items, SourceStatus(source["name"], "ok", len(items))
    except Exception as error:
        return [], SourceStatus(source["name"], "error", 0, shorten(str(error), 120))


def reconstruct_abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    max_position = max((position for positions in index.values() for position in positions), default=-1)
    if max_position < 0:
        return ""
    words = [""] * (max_position + 1)
    for word, positions in index.items():
        for position in positions:
            if 0 <= position < len(words):
                words[position] = word
    return " ".join(filter(None, words))


def fetch_openalex() -> tuple[list[dict[str, Any]], SourceStatus]:
    source_name = "OpenAlex Conference Index"
    start_date = (NOW - timedelta(days=250)).date().isoformat()
    params = {
        "filter": f"primary_location.source.type:conference,primary_topic.subfield.id:1702,from_publication_date:{start_date}",
        "sort": "publication_date:desc",
        "per-page": "30",
        "select": "id,doi,title,publication_date,primary_location,best_oa_location,open_access,authorships,abstract_inverted_index,keywords,primary_topic,cited_by_count,type",
    }
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    try:
        data = json.loads(request_bytes(url).decode("utf-8"))
        items: list[dict[str, Any]] = []
        for work in data.get("results", []):
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            if len(abstract) < 80:
                continue
            location = work.get("primary_location") or {}
            best_oa = work.get("best_oa_location") or {}
            open_access = work.get("open_access") or {}
            venue = clean_text((location.get("source") or {}).get("display_name"))
            destination = work.get("doi") or location.get("landing_page_url") or work.get("id")
            authors = [((entry.get("author") or {}).get("display_name") or "") for entry in work.get("authorships", [])]
            keywords = [entry.get("display_name", "") for entry in work.get("keywords", [])[:3]]
            topic = clean_text((work.get("primary_topic") or {}).get("display_name"))
            tags = [tag for tag in [topic, *keywords] if tag]
            item = make_item(
                title=work.get("title", ""),
                summary=abstract,
                source="OpenAlex",
                url=destination,
                published_at=work.get("publication_date"),
                category="research",
                tags=tags,
                indexed=True,
                authors=authors,
                venue=venue,
                pdf_url=clean_text(best_oa.get("pdf_url") or location.get("pdf_url")),
                license_name=clean_text(best_oa.get("license") or open_access.get("oa_status")),
                content_kind="paper",
                verification="OpenAlex 收录 · 开放获取状态已标注",
            )
            if item:
                item["citations"] = int(work.get("cited_by_count") or 0)
                items.append(item)
            if len(items) >= CATEGORY_LIMITS["research"]:
                break
        return items, SourceStatus(source_name, "ok", len(items))
    except Exception as error:
        return [], SourceStatus(source_name, "error", 0, shorten(str(error), 120))


def page_metadata(raw: str) -> tuple[str, str, str]:
    parser = PageMetadataParser()
    parser.feed(raw)
    title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or parser.title
    description = parser.meta.get("og:description") or parser.meta.get("description") or parser.meta.get("twitter:description") or ""
    published = parser.meta.get("article:published_time") or parser.meta.get("date") or ""
    if not published:
        match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
        published = match.group(1) if match else ""
    title = re.sub(r"\s*\|\s*Anthropic\s*$", "", clean_text(title), flags=re.I)
    return title, clean_text(description), clean_text(published)


def fetch_anthropic() -> tuple[list[dict[str, Any]], SourceStatus]:
    source_name = "Anthropic"
    try:
        root = ET.fromstring(request_bytes("https://www.anthropic.com/sitemap.xml"))
        pages: list[tuple[datetime, str, str]] = []
        for node in root.iter():
            if local_name(node.tag) != "url":
                continue
            location = first_child_text(node, ["loc"])
            lastmod = first_child_text(node, ["lastmod"])
            path = urllib.parse.urlparse(location).path.lower()
            if not path.startswith(("/news/", "/research/", "/engineering/")):
                continue
            pages.append((parse_datetime(lastmod) or datetime(1970, 1, 1, tzinfo=timezone.utc), location, lastmod))
        pages.sort(reverse=True)
        def fetch_page(page: tuple[datetime, str, str]) -> dict[str, Any] | None:
            _, url, fallback_date = page
            try:
                raw = request_bytes(url, attempts=1).decode("utf-8", errors="replace")
                title, description, published = page_metadata(raw)
                path = urllib.parse.urlparse(url).path.lower()
                tags = ["Anthropic", "Engineering" if path.startswith("/engineering/") else "Research" if path.startswith("/research/") else "Official"]
                return make_item(
                    title=title,
                    summary=description,
                    source="Anthropic",
                    url=url,
                    published_at=published or fallback_date,
                    category="frontier",
                    tags=tags,
                    official=True,
                )
            except Exception:
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            parsed = list(executor.map(fetch_page, pages[:12]))
        items = [item for item in parsed if item][:8]
        return items, SourceStatus(source_name, "ok" if items else "error", len(items), "" if items else "No recent pages parsed")
    except Exception as error:
        return [], SourceStatus(source_name, "error", 0, shorten(str(error), 120))


def google_news_url(query: str) -> str:
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)


def collect_all() -> tuple[list[dict[str, Any]], list[SourceStatus]]:
    items: list[dict[str, Any]] = []
    statuses: list[SourceStatus] = []

    jobs: list[tuple[Any, tuple[Any, ...]]] = [(fetch_openalex, ()), (fetch_anthropic, ())]
    jobs.extend((fetch_feed, (source,)) for source in OFFICIAL_FEEDS)
    for query in NEWS_QUERIES:
        source = {**query, "url": google_news_url(query["query"]), "official": False}
        jobs.append((fetch_feed, (source, True)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(function, *arguments) for function, arguments in jobs]
        for future in concurrent.futures.as_completed(futures):
            batch, status = future.result()
            items.extend(batch)
            statuses.append(status)

    return items, statuses


def deduplicate_and_limit(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduplicated: dict[str, dict[str, Any]] = {}
    for item in items:
        key = normalized_title(item["title"])
        if len(key) < 10:
            key = item["url"]
        current = deduplicated.get(key)
        if current is None or item["importance"] > current["importance"] or len(item.get("summary", "")) > len(current.get("summary", "")) + 120:
            deduplicated[key] = item

    by_category: dict[str, list[dict[str, Any]]] = {category: [] for category in CATEGORY_LIMITS}
    for item in deduplicated.values():
        if item["category"] in by_category:
            by_category[item["category"]].append(item)

    selected: list[dict[str, Any]] = []
    for category, limit in CATEGORY_LIMITS.items():
        ranked = sorted(
            by_category[category],
            key=lambda item: (item.get("importance", 0), parse_datetime(item.get("published_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc)),
            reverse=True,
        )
        selected.extend(ranked[:limit])

    selected.sort(
        key=lambda item: (item.get("importance", 0), parse_datetime(item.get("published_at")) or datetime(1970, 1, 1, tzinfo=timezone.utc)),
        reverse=True,
    )
    return selected


def build_analysis(items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {category: [item for item in items if item["category"] == category] for category in CATEGORY_LIMITS}
    searchable = [
        (item, " ".join([item.get("title", ""), item.get("summary", ""), item.get("source", ""), *item.get("tags", [])]).lower())
        for item in items
    ]
    coverage = {
        company: sum(any(term.lower() in haystack for term in terms) for _, haystack in searchable)
        for company, terms in CHINA_WATCHLIST.items()
    }
    covered = [company for company, count in coverage.items() if count]
    people_coverage = {
        person: sum(any(term.lower() in haystack for term in terms) for _, haystack in searchable)
        for person, terms in PEOPLE_WATCHLIST.items()
    }

    research_titles = "、".join(f"《{shorten(item['title'], 58)}》" for item in grouped["research"][:2]) or "本期会议论文"
    china_titles = "、".join(f"《{shorten(item['title'], 52)}》" for item in grouped["china"][:2]) or "中国模型公司的新动作"
    impact_titles = "、".join(f"《{shorten(item['title'], 52)}》" for item in grouped["impact"][:2]) or "AI 在数学与科学中的新贡献"
    industry_count = len(grouped["frontier"]) + len(grouped["bigtech"])
    covered_text = "、".join(covered) if covered else "Kimi、Qwen、腾讯元宝/混元、智谱、DeepSeek 与字节豆包/Seed"

    paragraphs = [
        f"研究侧共收录 {len(grouped['research'])} 条信号，重点包括 {research_titles}。与只看榜单相比，更值得持续观察的是论文能否把 Agent 的可靠性、评测完整性与推理成本一起向前推进。",
        f"AI 跨领域贡献收录 {len(grouped['impact'])} 条，代表性事件包括 {impact_titles}。这类结果会区分官方论文、可核验反例、媒体报道与尚待同行评审的社交平台首发，避免把‘可计算验证’和‘完成学术确认’混为一谈。",
        f"中国 AI 板块本期收录 {len(grouped['china'])} 条动态，已覆盖 {covered_text}。代表性变化包括 {china_titles}；竞争正在从单次模型发布延伸到开源策略、Agent 产品入口、国产算力适配和价格体系。",
        f"产业侧共有 {industry_count} 条前沿实验室与大厂动态、{len(grouped['voices'])} 条关键人物公开信号，另有 {len(grouped['startups'])} 条创业和 {len(grouped['policy'])} 条政策安全更新。模型能力、算力供给、创始人判断、产品分发与合规成本正在变成同一个竞争问题。",
    ]
    takeaways = [
        {"title": "科研判断", "body": "优先关注带公开证明、实验或可复核数据的 AI 科研贡献，并持续更新同行验证状态。"},
        {"title": "中国 AI", "body": f"当前重点覆盖 {len(covered)}/{len(CHINA_WATCHLIST)} 组公司；没有新消息的公司仍保留在持续监控名单中。"},
        {"title": "产业判断", "body": "开放权重、低价 API、消费端入口和国产算力适配，正在共同决定模型能否形成规模化使用。"},
    ]
    return {
        "title": "从模型竞速走向产品、算力与生态：本期 AI 趋势观察",
        "lead": f"本期共整理 {len(items)} 条有效信号。下面不是新闻复述，而是把论文、公司、创业与政策放在同一张图里后的编辑性判断。",
        "paragraphs": paragraphs,
        "takeaways": takeaways,
        "china_watch_coverage": coverage,
        "people_watch_coverage": people_coverage,
    }


def build_payload(items: list[dict[str, Any]], statuses: list[SourceStatus]) -> dict[str, Any]:
    counts = {category: sum(item["category"] == category for item in items) for category in CATEGORY_LIMITS}
    return {
        "schema_version": 2,
        "generated_at": NOW.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "item_count": len(items),
        "category_counts": counts,
        "analysis": build_analysis(items),
        "sources": [status.as_dict() for status in statuses],
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Update the static AI news snapshot")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    raw_items, statuses = collect_all()
    items = deduplicate_and_limit(raw_items)
    if len(items) < 8:
        print(f"Refusing to replace the snapshot: only {len(items)} usable items were collected.", file=sys.stderr)
        return 1

    payload = build_payload(items, statuses)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    healthy = sum(status.status == "ok" for status in statuses)
    print(f"Wrote {len(items)} items from {healthy}/{len(statuses)} healthy sources to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
