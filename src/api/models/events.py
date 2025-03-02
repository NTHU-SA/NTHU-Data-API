from cachetools import TTLCache, cached

from src.utils.scrapers import cac_scraper, goodjob_scraper, rpage_scraper


@cached(cache=TTLCache(maxsize=2, ttl=60 * 60 * 4))
def get_events_list():
    """
    取得所有活動資料。
    """
    event_types = {
        "goodjob": goodjob_scraper.get_announcements(goodjob_scraper.DataType.EVENT),
        "arts_center": cac_scraper.get_events_list(),
        "global_affairs": rpage_scraper.get_announcement(
            "https://oga.site.nthu.edu.tw/p/403-1524-9308-1.php?Lang=zh-tw"
        ),
        "health_center": rpage_scraper.get_announcement(
            "https://health.site.nthu.edu.tw/p/403-1001-7467-1.php?Lang=zh-tw"
        ),
    }
    return event_types
