#!/usr/bin/env python3
"""Build copyright-conscious in-site reading records for AI Signal.

Public article pages are fetched for short excerpts and structured notes. Full
news articles are never mirrored. Open-access paper PDFs from allow-listed
repositories may be cached and are summarized into sections; the original
source and license metadata always remain visible.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "data" / "ai-news.json"
DEFAULT_OUTPUT = ROOT / "data" / "readers.json"
DEFAULT_PAPERS = ROOT / "papers"
USER_AGENT = "Linyouxue-AI-Signal/2.0 (+https://linyouxue.github.io/ai-news.html)"
TIMEOUT = 24
MAX_HTML_BYTES = 2_500_000
MAX_PDF_BYTES = 12_000_000
MAX_PDF_PAGES = 45

OPEN_PDF_HOSTS = {
    "arxiv.org", "export.arxiv.org", "openreview.net", "cdn.openai.com",
    "proceedings.mlr.press", "aclanthology.org", "openaccess.thecvf.com",
}
SOCIAL_HOSTS = {"x.com", "twitter.com", "weibo.com", "m.weibo.cn", "zhihu.com", "mp.weixin.qq.com"}
SECTION_HEADINGS = {
    "abstract", "introduction", "background", "related work", "method", "methods",
    "methodology", "approach", "experiments", "experimental results", "results",
    "evaluation", "discussion", "limitations", "conclusion", "conclusions", "references",
}


def clean_text(value: Any) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_url(value: Any) -> str:
    text = str(value or "").replace("&amp;", "&").strip()
    return re.sub(r"[\x00-\x20]+", "", text)


def shorten(value: str, limit: int) -> str:
    value = clean_text(value)
    if len(value) <= limit:
        return value
    clipped = value[: limit + 1]
    boundary = max(clipped.rfind("。"), clipped.rfind(". "), clipped.rfind("; "), clipped.rfind(" "))
    if boundary < int(limit * 0.58):
        boundary = limit
    return clipped[:boundary].rstrip(" ,;:") + "…"


class ArticleTextParser(HTMLParser):
    """Collect readable paragraph text without copying navigation or scripts."""

    SKIP = {"script", "style", "nav", "footer", "header", "form", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.capture_tag = ""
        self.buffer: list[str] = []
        self.blocks: list[str] = []
        self.meta: dict[str, str] = {}
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_map = {key.lower(): value or "" for key, value in attrs}
        if tag in self.SKIP:
            self.skip_depth += 1
            return
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key = (attrs_map.get("property") or attrs_map.get("name") or "").lower()
            if key and attrs_map.get("content"):
                self.meta[key] = clean_text(attrs_map["content"])
        if not self.skip_depth and tag in {"p", "li", "blockquote"} and not self.capture_tag:
            self.capture_tag = tag
            self.buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
            return
        if tag == "title":
            self.in_title = False
            title = clean_text(" ".join(self.title_parts))
            if title:
                self.meta["page:title"] = title
        if not self.skip_depth and tag == self.capture_tag:
            block = clean_text(" ".join(self.buffer))
            if 45 <= len(block) <= 5000 and block not in self.blocks:
                self.blocks.append(block)
            self.capture_tag = ""
            self.buffer = []

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self.skip_depth and self.capture_tag:
            self.buffer.append(data)


def request_bytes(url: str, max_bytes: int, accept: str) -> tuple[bytes, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        length = int(response.headers.get("Content-Length") or 0)
        if length and length > max_bytes:
            raise ValueError(f"resource too large ({length} bytes)")
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise ValueError(f"resource exceeds {max_bytes} bytes")
        return body, response.geturl(), response.headers.get("Content-Type", "")


def derive_pdf_url(item: dict[str, Any]) -> str:
    existing = clean_url(item.get("pdf_url"))
    if existing.startswith(("http://", "https://")):
        return existing
    url = clean_url(item.get("url"))
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc.endswith("arxiv.org") and "/abs/" in parsed.path:
        identifier = parsed.path.split("/abs/", 1)[1].strip("/")
        return f"https://arxiv.org/pdf/{identifier}"
    if parsed.netloc.endswith("openreview.net") and parsed.path == "/forum":
        return "https://openreview.net/pdf?" + parsed.query
    return ""


def may_cache_pdf(url: str, item: dict[str, Any]) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower().split(":", 1)[0]
    if any(host == allowed or host.endswith("." + allowed) for allowed in OPEN_PDF_HOSTS):
        return True
    license_name = clean_text(item.get("license")).lower()
    return license_name.startswith(("cc-by", "cc0", "public-domain"))


def download_pdf(url: str, destination: Path) -> None:
    body, _, content_type = request_bytes(url, MAX_PDF_BYTES, "application/pdf")
    if not body.startswith(b"%PDF") and "pdf" not in content_type.lower():
        raise ValueError("source did not return a PDF")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(body)


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages[:MAX_PDF_PAGES]:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:180_000]
    except Exception:
        return ""


def sentences(text: str) -> list[str]:
    chunks = re.split(r"(?<=[。！？!?])\s*|(?<=[.!?])\s+(?=[A-Z0-9])", clean_text(text))
    result = []
    for chunk in chunks:
        chunk = clean_text(chunk)
        if 45 <= len(chunk) <= 520 and chunk not in result:
            result.append(chunk)
    return result


def key_points(text: str, fallback: str, limit: int = 5) -> list[str]:
    candidates = sentences(text) or sentences(fallback)
    if not candidates and fallback:
        candidates = [shorten(fallback, 360)]
    return [shorten(point, 360) for point in candidates[:limit]]


def extract_named_section(text: str, aliases: tuple[str, ...], limit: int = 2600) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    lower_aliases = {alias.lower() for alias in aliases}
    start = -1
    for index, line in enumerate(lines):
        normalized = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", line).strip(" .:").lower()
        if normalized in lower_aliases:
            start = index + 1
            break
    if start < 0:
        return ""
    selected: list[str] = []
    for line in lines[start:]:
        normalized = re.sub(r"^\s*\d+(?:\.\d+)*\s*", "", line).strip(" .:").lower()
        if normalized in SECTION_HEADINGS and selected:
            break
        if line:
            selected.append(line)
        if sum(len(part) for part in selected) >= limit:
            break
    return shorten(" ".join(selected), limit)


def fetch_article(url: str) -> tuple[list[str], dict[str, str], str]:
    body, final_url, content_type = request_bytes(url, MAX_HTML_BYTES, "text/html,application/xhtml+xml;q=0.9,*/*;q=0.5")
    if "pdf" in content_type.lower() or body.startswith(b"%PDF"):
        return [], {}, final_url
    parser = ArticleTextParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    useful = [block for block in parser.blocks if not re.search(r"cookie|sign up|subscribe|all rights reserved", block, flags=re.I)]
    return useful[:24], parser.meta, final_url


def decode_google_news_url(url: str) -> str:
    parsed = urllib.parse.urlparse(clean_url(url))
    if not parsed.netloc.endswith("news.google.com") or "/articles/" not in parsed.path:
        return ""
    try:
        from googlenewsdecoder import gnewsdecoder

        result = gnewsdecoder(url, interval=0)
        decoded = clean_url(result.get("decoded_url")) if result.get("status") else ""
        return decoded if decoded.startswith(("http://", "https://")) else ""
    except Exception:
        return ""


def placeholder_summary(value: str) -> bool:
    value = clean_text(value)
    return value.startswith("来自 ") and "点击查看原始来源" in value


def weak_title(value: str) -> bool:
    normalized = clean_text(value).strip(" -–—|·")
    return len(normalized) < 6 or normalized in {"微信公众平台", "Google News"}


def reading_time(text: str) -> int:
    latin_words = len(re.findall(r"\b[A-Za-z][A-Za-z'-]*\b", text))
    cjk_chars = len(re.findall(r"[\u3400-\u9fff]", text))
    return max(1, round(latin_words / 220 + cjk_chars / 420))


def base_record(item: dict[str, Any]) -> dict[str, Any]:
    url = clean_url(item.get("url"))
    host = urllib.parse.urlparse(url).netloc.lower()
    kind = item.get("content_kind") or ("social" if any(domain in host for domain in SOCIAL_HOSTS) else "paper" if item.get("category") == "research" else "article")
    return {
        "id": item.get("id"),
        "kind": kind,
        "title": item.get("title", "Untitled"),
        "source": item.get("source", "Original source"),
        "source_url": url,
        "published_at": item.get("published_at"),
        "authors": item.get("authors", []),
        "venue": item.get("venue", ""),
        "tags": item.get("tags", []),
        "verification": item.get("verification", "来源待核对"),
        "summary": item.get("summary", ""),
        "rights_note": "本站保留结构化摘要与必要短摘录；完整内容请查看原始来源。",
    }


def build_article_record(item: dict[str, Any], use_network: bool) -> dict[str, Any]:
    record = base_record(item)
    blocks: list[str] = []
    meta: dict[str, str] = {}
    final_url = record["source_url"]
    if use_network and final_url:
        try:
            blocks, meta, final_url = fetch_article(final_url)
            if blocks or meta.get("og:description") or meta.get("description"):
                record["fetch_status"] = "public-page-excerpt"
            elif "索引摘要" in record.get("verification", ""):
                record["fetch_status"] = "indexed-summary"
            else:
                record["fetch_status"] = "summary-only"
        except Exception as error:
            record["fetch_status"] = "indexed-summary" if "索引摘要" in record.get("verification", "") else "summary-only"
            record["fetch_note"] = shorten(str(error), 180)
    else:
        record["fetch_status"] = "indexed-summary" if "索引摘要" in record.get("verification", "") else "summary-only"
    resolved_title = meta.get("og:title") or meta.get("twitter:title") or meta.get("page:title") or ""
    description = meta.get("og:description") or meta.get("description") or meta.get("twitter:description") or ""
    if resolved_title and (weak_title(record["title"]) or len(resolved_title) > len(record["title"]) + 12):
        record["title"] = shorten(resolved_title, 180)
    if description and (
        placeholder_summary(record["summary"])
        or len(description) > len(record["summary"]) + 80
    ):
        record["summary"] = shorten(description, 680)
    description = description or record["summary"]
    excerpt_blocks = [shorten(block, 720) for block in blocks if len(block) >= 70][:3]
    evidence_text = " ".join(excerpt_blocks) or description
    section_title = "公开索引摘要" if record["fetch_status"] == "indexed-summary" else "公开页面要点"
    record.update({
        "resolved_url": final_url,
        "key_points": key_points(evidence_text, record["summary"]),
        "sections": [
            {"title": "内容概览", "body": record["summary"]},
            {"title": section_title, "bullets": key_points(evidence_text, description)},
            {"title": "原文短摘录", "paragraphs": excerpt_blocks},
        ],
        "reading_minutes": reading_time(" ".join([record["summary"], *excerpt_blocks])),
    })
    return record


def build_paper_record(item: dict[str, Any], papers_dir: Path, download: bool) -> dict[str, Any]:
    record = base_record(item)
    record["kind"] = "paper"
    pdf_url = derive_pdf_url(item)
    local_path = papers_dir / f"{item['id']}.pdf"
    pdf_text = ""
    if download and pdf_url and may_cache_pdf(pdf_url, item):
        try:
            if not local_path.exists():
                download_pdf(pdf_url, local_path)
            pdf_text = extract_pdf_text(local_path)
            record["pdf_local"] = f"./papers/{local_path.name}"
            record["fetch_status"] = "open-pdf-cached"
        except Exception as error:
            record["fetch_status"] = "pdf-link-only"
            record["fetch_note"] = shorten(str(error), 180)
    else:
        record["fetch_status"] = "pdf-link-only" if pdf_url else "abstract-only"
    if pdf_url:
        record["pdf_url"] = pdf_url
    abstract = extract_named_section(pdf_text, ("abstract",), 2200) or record["summary"]
    method = extract_named_section(pdf_text, ("method", "methods", "methodology", "approach"), 2800)
    results = extract_named_section(pdf_text, ("results", "experimental results", "evaluation", "experiments"), 2800)
    limits = extract_named_section(pdf_text, ("limitations", "discussion", "conclusion", "conclusions"), 2200)
    evidence = pdf_text[:12000] if pdf_text else abstract
    sections = [{"title": "摘要", "body": abstract}]
    if method:
        sections.append({"title": "方法与技术路线", "body": method})
    if results:
        sections.append({"title": "关键结果", "body": results})
    if limits:
        sections.append({"title": "局限与结论", "body": limits})
    record.update({
        "key_points": key_points(evidence, abstract),
        "sections": sections,
        "reading_minutes": reading_time(pdf_text or abstract),
        "rights_note": "仅缓存明确开放获取来源的 PDF；作者、出处与原始链接保持可见。",
    })
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Build structured reading records and cache open PDFs")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--papers-dir", type=Path, default=DEFAULT_PAPERS)
    parser.add_argument("--download-pdfs", action="store_true")
    parser.add_argument("--no-network", action="store_true")
    parser.add_argument("--max-papers", type=int, default=6)
    args = parser.parse_args()

    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    items = snapshot.get("items", [])
    resolved_count = 0
    if not args.no_network:
        google_items = [
            item
            for item in items
            if urllib.parse.urlparse(clean_url(item.get("url"))).netloc.endswith("news.google.com")
        ]

        def resolve_item(item: dict[str, Any]) -> tuple[dict[str, Any], str]:
            return item, decode_google_news_url(item.get("url", ""))

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as resolver:
            for item, decoded_url in resolver.map(resolve_item, google_items):
                if not decoded_url:
                    continue
                item["index_url"] = item["url"]
                item["url"] = decoded_url
                resolved_count += 1
    paper_ids = []
    for item in items:
        pdf_url = derive_pdf_url(item)
        is_paper = item.get("category") == "research" or item.get("content_kind") == "paper"
        if is_paper and pdf_url and may_cache_pdf(pdf_url, item):
            paper_ids.append(item["id"])
    selected_papers = set(paper_ids[: max(0, args.max_papers)])

    def build(item: dict[str, Any]) -> dict[str, Any]:
        if item.get("category") == "research" or item.get("content_kind") == "paper":
            return build_paper_record(item, args.papers_dir, args.download_pdfs and item.get("id") in selected_papers)
        index_only = (
            "索引摘要" in item.get("verification", "")
            and item.get("url") == item.get("index_url")
        )
        return build_article_record(item, not args.no_network and not index_only)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        records = list(executor.map(build, items))

    if args.download_pdfs and args.papers_dir.exists():
        keep = {f"{identifier}.pdf" for identifier in selected_papers}
        for path in args.papers_dir.glob("*.pdf"):
            if path.name not in keep:
                path.unlink()
        if not any(args.papers_dir.iterdir()):
            shutil.rmtree(args.papers_dir)

    index = {record["id"]: record for record in records if record.get("id")}
    for item in items:
        record = index.get(item.get("id"), {})
        item["reader_status"] = record.get("fetch_status", "summary-only")
        if record.get("resolved_url"):
            item["url"] = record["resolved_url"]
        if record.get("title"):
            item["title"] = record["title"]
        if record.get("summary"):
            item["summary"] = record["summary"]
        if record.get("pdf_local"):
            item["cached_pdf"] = record["pdf_local"]

    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "record_count": len(records),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.snapshot.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    cached = sum(bool(record.get("pdf_local")) for record in records)
    print(f"Built {len(records)} readers; resolved {resolved_count} indexed links; cached {cached} open PDFs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
