from fastapi import APIRouter
from src.utils.scraper import rpage_scraper, library_rss_scraper, goodjob_scraper

router = APIRouter(
    prefix="/events",
    tags=["events"],
    responses={404: {"description": "Not found"}},
)


@router.get("/libarys")
async def get_libarys_events():
    """
    取得圖書館的展覽及活動資料。
    """
    return library_rss_scraper.exhibit()


@router.get("/global_affairs")
async def get_global_affairs_events():
    """
    取得國際事務處的活動資料。
    """
    return rpage_scraper.announcement(
        "https://oga.site.nthu.edu.tw/p/403-1524-9308-1.php?Lang=zh-tw"
    )


@router.get("/health_center")
async def get_health_center_events():
    """
    取得衛生保健組的活動資料。
    """
    return rpage_scraper.announcement(
        "https://health.site.nthu.edu.tw/p/403-1001-7467-1.php?Lang=zh-tw"
    )


@router.get("/bulletin/art_and_cultural")
async def get_bulletin_art_and_cultural_events():
    """
    取得清華公佈欄的藝文活動。
    """
    return rpage_scraper.announcement(
        "https://bulletin.site.nthu.edu.tw/p/403-1086-5083-1.php?Lang=zh-tw"
    )


@router.get("/bulletin/academic")
async def get_bulletin_academic_events():
    """
    取得清華公佈欄的學術活動。
    """
    return rpage_scraper.announcement(
        "https://bulletin.site.nthu.edu.tw/p/403-1086-5084-1.php?Lang=zh-tw"
    )


@router.get("/bulletin/student")
async def get_bulletin_student_events():
    """
    取得清華公佈欄的學生活動。
    """
    return rpage_scraper.announcement(
        "https://bulletin.site.nthu.edu.tw/p/403-1086-5085-1.php?Lang=zh-tw"
    )


@router.get("/goodjob")
async def get_goodjob_events():
    """
    取得清華 JOB 讚的活動資料。
    """
    return goodjob_scraper.get("01003")
