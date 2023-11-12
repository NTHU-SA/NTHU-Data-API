from fastapi import APIRouter, Path

from src.api import schemas
from src.utils.scrapers import library_scraper

router = APIRouter()


@router.get("/space", response_model=list[schemas.resources.LibrarySpace])
def get_library_space_data():
    """
    取得空間使用資訊。
    """
    return library_scraper.get_space_data()


@router.get(
    "/lost_and_found", response_model=list[schemas.resources.LibraryLostAndFound]
)
def get_library_lost_and_found():
    """
    取得失物招領資訊。
    """
    return library_scraper.get_lost_and_found()


@router.get("/rss/{rss}", response_model=list[schemas.resources.RssItem])
def get_library_rss_data(
    rss: schemas.resources.LibraryRssType = Path(
        ...,
        description="RSS 類型：最新消息(news)、電子資源(eresources)、展覽及活動(exhibit)、南大與人社分館(branches)",
    )
):
    """
    取得指定RSS資料。
    """
    return library_scraper.get_rss_data(rss.value)


@router.get(
    "/openinghours/{libaray_name}", response_model=schemas.resources.LibraryOpeningHour
)
def get_library_opening_hours(
    libaray_name: schemas.resources.LibraryName = Path(
        ..., description="圖書館代號：總圖(mainlib)、人社圖書館(hslib)、南大圖書館(nandalib)"
    )
):
    """
    取得指定圖書館的開放時間。
    """
    return library_scraper.get_opening_hours(libaray_name)


@router.get("/goods", response_model=schemas.resources.LibraryNumberOfGoods)
def get_library_number_of_goods():
    """
    取得總圖換證數量資訊。
    """
    return library_scraper.get_number_of_goods()
