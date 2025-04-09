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
    if url.startswith("//"):
        return "https:" + url
    else:
        split_url = url.split("://")
        if len(split_url) > 1 and split_url[0] not in ["http", "https"]:
            return "https://" + split_url[1]

    return url
