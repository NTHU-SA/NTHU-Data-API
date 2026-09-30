from urllib.parse import urlsplit, urlunsplit


def url_corrector(url: str) -> str:
    """
    Fix the URL under different conditions:
        If the URL starts with "//", prepend "https:" to it.
        If the URL contains "://" but does not start with "http" or "https", prepend "https://" to it.

    Args:
        url (str): The URL to be fixed.

    Returns:
        str: The fixed URL.
    """
    if url is None:
        return url

    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    else:
        split_url = url.split("://")
        if len(split_url) > 1 and split_url[0] not in ["http", "https"]:
            return "https://" + split_url[1]

    return url


def rss_image_url_corrector(url: object) -> object:
    """Encode library RSS image path spaces without re-encoding existing escapes."""
    if not isinstance(url, str):
        return url

    url = url_corrector(url)
    # Let HttpUrl reject controls rather than allowing urlsplit to strip them.
    if any(ord(character) < 32 for character in url):
        return url

    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=parts.path.replace(" ", "%20")))
