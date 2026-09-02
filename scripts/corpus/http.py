from urllib.request import Request, urlopen

from .schema import SourceCandidate


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36 "
    "MedQueryDemoCorpusCollector/1.0"
)


def _decode_page(payload: bytes, content_type: str) -> str:
    charset = "utf-8"
    if "charset=" in content_type:
        charset = content_type.rsplit("charset=", 1)[1].split(";", 1)[0].strip()
    for candidate in (charset, "utf-8", "gb18030"):
        try:
            return payload.decode(candidate)
        except (LookupError, UnicodeDecodeError):
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_page(source: SourceCandidate, user_agent: str) -> tuple[bytes, str]:
    request = Request(
        source.url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        },
    )
    with urlopen(request) as response:
        payload = response.read()
        content_type = response.headers.get("Content-Type", "")
    return payload, _decode_page(payload, content_type)
