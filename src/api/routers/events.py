from fastapi import APIRouter

from src.api import schemas
from src.utils.scrapers import (
    cac_scraper,
    goodjob_scraper,
    library_scraper,
    rpage_scraper,
)

router = APIRouter()


@router.get("/libarys", response_model=list[schemas.events.EventData])
async def get_libarys_events():
    """
    取得圖書館的展覽及活動資料。
    """
    return library_scraper.get_parsed_rss_data("exhibit")


@router.get("/goodjob", response_model=list[schemas.events.EventData])
async def get_goodjob_events():
    """
    取得清華 JOB 讚的職涯活動資料。
    """
    return goodjob_scraper.get_announcements(goodjob_scraper.DataType.EVENT)


@router.get("/arts_center", response_model=list[schemas.events.EventData])
async def get_arts_center_events():
    """
    取得藝術文化總中心的當期活動。
    """
    return cac_scraper.get_events_list()


@router.get("/global_affairs", response_model=list[schemas.events.EventData])
async def get_global_affairs_events():
    """
    取得國際事務處的各類活動資料。
    """
    return rpage_scraper.get_announcement(
        "https://oga.site.nthu.edu.tw/p/403-1524-9308-1.php?Lang=zh-tw"
    )


@router.get("/health_center", response_model=list[schemas.events.EventData])
async def get_health_center_events():
    """
    取得衛生保健組的活動資料。
    """
    return rpage_scraper.get_announcement(
        "https://health.site.nthu.edu.tw/p/403-1001-7467-1.php?Lang=zh-tw"
    )
