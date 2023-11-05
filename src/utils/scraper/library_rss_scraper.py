import xmltodict

from src.utils import cached_request


def rss_parser(xml_string: str) -> dict:
    """
    將 RSS XML 轉換成 dict。
    """
    xml_string = xml_string.replace("<br />", "")
    dict = xmltodict.parse(xml_string)
    dict = dict["rss"]["channel"]
    return dict


def get_rss_data(rss_type: str) -> dict:
    # 最新消息 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml
    # 電子資源 RSS:         https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml
    # 展覽及活動 RSS:       https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml
    # 南大與人社分館 RSS:   https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml
    url = f"https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_{rss_type}.xml"
    text = cached_request.get(url)
    return rss_parser(text)


def news() -> dict:
    """
    最新消息 RSS: https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml
    """
    url = "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_news.xml"
    text = cached_request.get(url)
    return rss_parser(text)


def eresources() -> dict:
    """
    電子資源 RSS: https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml
    """
    url = "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_eresources.xml"
    text = cached_request.get(url)
    return rss_parser(text)


def exhibit() -> dict:
    """
    展覽及活動 RSS: https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml
    """
    url = "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_exhibit.xml"
    text = cached_request.get(url)
    return rss_parser(text)


def branches() -> dict:
    """
    南大與人社分館 RSS: https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml
    """
    url = "https://www.lib.nthu.edu.tw/bulletin/RSS/export/rss_branches.xml"
    text = cached_request.get(url)
    return rss_parser(text)
