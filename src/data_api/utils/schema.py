def url_corrector(url: object) -> object:
    """
    Fix the URL under different conditions:
        If the URL starts with "//", prepend "https:" to it.
        If the URL contains "://" but does not start with "http" or "https", prepend "https://" to it.

    Args:
        url (object): The value to validate, corrected only when it is a string.

    Returns:
        object: The fixed URL or the original non-string value for downstream validation.
    """
    if not isinstance(url, str):
        return url

    url = url.strip()
    if url.startswith("//"):
        return "https:" + url
    else:
        split_url = url.split("://")
        if len(split_url) > 1 and split_url[0] not in ["http", "https"]:
            return "https://" + split_url[1]

    return url
