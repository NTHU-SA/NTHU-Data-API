from fastapi import APIRouter, HTTPException, Query
from thefuzz import fuzz

from src.api.schemas.locations import LocationDetail
from src.utils import nthudata

router = APIRouter()
JSON_PATH = "maps.json"
FUZZY_SEARCH_THRESHOLD = 60


@router.get(
    "/",
    response_model=list[LocationDetail],
)
async def get_all_locations():
    """
    取得校內所有地點資訊。
    資料來源：[國立清華大學校園地圖](https://www.nthu.edu.tw/campusmap)
    """
    _commit_hash, map_data = await nthudata.get(JSON_PATH)
    return [
        LocationDetail(
            name=location_name,
            latitude=coordinates["latitude"],
            longitude=coordinates["longitude"],
        )
        for campus_locations in map_data.values()
        for location_name, coordinates in campus_locations.items()
    ]


@router.get(
    "/search",
    response_model=list[LocationDetail],
)
async def fuzzy_search_locations(
    query: str = Query(..., example="校門", description="要查詢的地點"),
):
    """
    使用名稱模糊搜尋地點資訊。
    """
    _commit_hash, map_data = await nthudata.get(JSON_PATH)
    tmp_results = []
    for campus_locations in map_data.values():
        for location_name, coordinates in campus_locations.items():
            similarity = fuzz.partial_ratio(query, location_name)
            if similarity >= FUZZY_SEARCH_THRESHOLD:
                tmp_results.append(
                    (
                        similarity,
                        LocationDetail(
                            name=location_name,
                            latitude=coordinates["latitude"],
                            longitude=coordinates["longitude"],
                        ),
                    )
                )

    if not tmp_results:
        raise HTTPException(status_code=404, detail="Not found")

    # 先判斷是否與查詢字串相同，再依相似度從高到低排序
    tmp_results.sort(key=lambda x: (x[1].name == query, x[0]), reverse=True)
    return [item[1] for item in tmp_results]
