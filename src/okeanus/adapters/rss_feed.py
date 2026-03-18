"""Generic RSS/Atom feed adapter — one adapter serves dozens of ocean news feeds.

Configure with a feed URL and optional category tag. The adapter parses
RSS 2.0 and Atom feeds using the built-in xml.etree parser (no feedparser
dependency needed).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree as ET

from okeanus.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)

# Well-known ocean/maritime RSS feeds
FEEDS: dict[str, str] = {
    "gcaptain": "https://gcaptain.com/feed/",
    "splash247": "https://splash247.com/feed/",
    "hellenic_shipping": "https://www.hellenicshippingnews.com/feed/",
    "marinelink": "https://www.marinelink.com/news/rss",
    "safety4sea": "https://safety4sea.com/feed/",
    "loadstar": "https://theloadstar.com/feed/",
    "cimsec": "https://cimsec.org/feed/",
    "mongabay_oceans": "https://news.mongabay.com/list/oceans/feed/",
    "offshore_energy": "https://www.offshore-energy.biz/feed/",
    "offshore_wind": "https://www.offshorewind.biz/feed/",
    "world_maritime_news": "https://feeds.feedburner.com/worldmaritimenews/Ltoh",
    "container_news": "https://container-news.com/feed/",
    "dredging_today": "https://www.dredgingtoday.com/feed/",
    "naval_today": "https://www.navaltoday.com/feed/",
    "baird_maritime": "https://www.bairdmaritime.com/feed/",
    "usni_news": "https://news.usni.org/feed",
    "intrafish_fisheries": "https://www.intrafish.com/rss_fisheries",
    "intrafish_aquaculture": "https://www.intrafish.com/rss_aquaculture",
    "conservation_intl": "https://feeds.feedburner.com/ConservationInternationalBlog",
    "ocean_conservancy": "https://oceanconservancy.org/blog/feed/",
    "revelator": "https://therevelator.org/feed/",
    "arxiv_ocean": "https://rss.arxiv.org/rss/physics.ao-ph",
    "imo_news": "https://www.imo.org/en/about/pages/rss.aspx",
}

# Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"


class RssFeedAdapter(BaseAdapter):
    """Generic RSS/Atom feed connector for ocean news aggregation."""

    def __init__(
        self,
        *,
        feed_url: str = "",
        feed_name: str = "",
        category: str = "maritime_news",
        **kwargs: Any,
    ) -> None:
        super().__init__(requests_per_second=1.0, **kwargs)
        self._feed_url = feed_url
        self._feed_name = feed_name or "rss"
        self._category = category

    @property
    def source_name(self) -> str:
        return f"rss_{self._feed_name}" if self._feed_name else "rss_feed"

    @property
    def source_url(self) -> str:
        return self._feed_url

    @property
    def update_frequency(self) -> str:
        return "varies"

    async def fetch(
        self,
        bbox: tuple[float, float, float, float],
        time_start: datetime,
        time_end: datetime,
        **params: Any,
    ) -> list[dict[str, Any]]:
        """Fetch and parse an RSS/Atom feed, filtering by time window.

        Extra params:
            feed_url: Override the configured feed URL
            feed_name: Override the configured feed name
            feeds: List of feed keys from FEEDS dict to fetch (multi-feed mode)
            limit: Max items to return (default 50)
        """
        limit = params.get("limit", 50)

        # Multi-feed mode: fetch several named feeds
        feed_keys = params.get("feeds", [])
        if feed_keys:
            all_items: list[dict[str, Any]] = []
            for key in feed_keys:
                url = FEEDS.get(key)
                if not url:
                    continue
                items = await self._fetch_one_feed(
                    url, key, time_start, time_end, limit=limit
                )
                all_items.extend(items)
            all_items.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
            return all_items[:limit]

        # Single-feed mode
        feed_url = params.get("feed_url", self._feed_url)
        feed_name = params.get("feed_name", self._feed_name)
        if not feed_url:
            # No specific feed — fall back to a curated default set
            default_keys = ["gcaptain", "marinelink", "usni_news"]
            all_items = []
            for key in default_keys:
                url = FEEDS.get(key)
                if not url:
                    continue
                items = await self._fetch_one_feed(
                    url, key, time_start, time_end, limit=limit
                )
                all_items.extend(items)
            all_items.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
            return all_items[:limit]

        return await self._fetch_one_feed(
            feed_url, feed_name, time_start, time_end, limit=limit
        )

    async def _fetch_one_feed(
        self,
        url: str,
        name: str,
        time_start: datetime,
        time_end: datetime,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch and parse a single RSS/Atom feed."""
        try:
            resp = await self._request(
                "GET",
                url,
                headers={"User-Agent": "Okeanus/1.0 (ocean data aggregator)"},
            )
            xml_text = resp.text
        except Exception as exc:
            logger.error("RSS fetch failed for %s: %s", name, exc)
            return []

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            logger.error("RSS XML parse failed for %s: %s", name, exc)
            return []

        # Detect feed type
        if root.tag == "rss" or root.find("channel") is not None:
            return self._parse_rss(root, name, time_start, time_end, limit)
        elif root.tag == f"{{{ATOM_NS}}}feed" or root.tag == "feed":
            return self._parse_atom(root, name, time_start, time_end, limit)
        else:
            logger.warning("Unknown feed format for %s: root tag=%s", name, root.tag)
            return []

    def _parse_rss(
        self,
        root: ET.Element,
        name: str,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse RSS 2.0 feed."""
        channel = root.find("channel")
        if channel is None:
            return []

        observations: list[dict[str, Any]] = []
        for item in channel.findall("item"):
            if len(observations) >= limit:
                break

            title = _text(item, "title")
            link = _text(item, "link")
            description = _text(item, "description")
            pub_date = _text(item, "pubDate")
            category = _text(item, "category")

            ts = _parse_rss_date(pub_date)
            if ts is None:
                ts = datetime.now(timezone.utc)

            # Filter by time window
            ts_aware = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            if ts_aware < time_start or ts_aware > time_end:
                continue

            observations.append({
                "obs_type": "news",
                "timestamp": ts_aware,
                "geometry": None,
                "source_id": f"rss-{name}-{_slug(title or link)}",
                "source_name": f"RSS:{name}",
                "quality_score": None,
                "payload": {
                    "title": title,
                    "url": link,
                    "summary": _strip_html(description or "")[:500],
                    "category": category or self._category,
                    "feed_name": name,
                },
            })

        return observations

    def _parse_atom(
        self,
        root: ET.Element,
        name: str,
        time_start: datetime,
        time_end: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Parse Atom feed."""
        ns = ATOM_NS
        observations: list[dict[str, Any]] = []

        entries = root.findall(f"{{{ns}}}entry") or root.findall("entry")
        for entry in entries:
            if len(observations) >= limit:
                break

            title = _text(entry, f"{{{ns}}}title") or _text(entry, "title")
            link_el = entry.find(f"{{{ns}}}link") or entry.find("link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary = (
                _text(entry, f"{{{ns}}}summary")
                or _text(entry, "summary")
                or _text(entry, f"{{{ns}}}content")
                or _text(entry, "content")
            )
            updated = (
                _text(entry, f"{{{ns}}}updated")
                or _text(entry, "updated")
                or _text(entry, f"{{{ns}}}published")
                or _text(entry, "published")
            )

            ts = _parse_iso_date(updated) if updated else None
            if ts is None:
                ts = datetime.now(timezone.utc)

            ts_aware = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
            if ts_aware < time_start or ts_aware > time_end:
                continue

            observations.append({
                "obs_type": "news",
                "timestamp": ts_aware,
                "geometry": None,
                "source_id": f"rss-{name}-{_slug(title or link)}",
                "source_name": f"RSS:{name}",
                "quality_score": None,
                "payload": {
                    "title": title,
                    "url": link,
                    "summary": _strip_html(summary or "")[:500],
                    "category": self._category,
                    "feed_name": name,
                },
            })

        return observations


def _text(el: ET.Element, tag: str) -> str:
    """Safely extract text from an XML element."""
    child = el.find(tag)
    return (child.text or "").strip() if child is not None else ""


def _parse_rss_date(s: str) -> datetime | None:
    """Parse RFC 2822 date (RSS pubDate format)."""
    if not s:
        return None
    try:
        return parsedate_to_datetime(s)
    except (ValueError, TypeError):
        return _parse_iso_date(s)


def _parse_iso_date(s: str) -> datetime | None:
    """Parse ISO 8601 date."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _slug(s: str) -> str:
    """Create a short slug for source_id."""
    return re.sub(r"[^a-z0-9]+", "-", s.lower().strip())[:60]
