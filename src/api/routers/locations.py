import requests
from fastapi import APIRouter, HTTPException, Query
from thefuzz import fuzz

from src.api.schemas.locations import LocationDetail

router = APIRouter()

map_data = requests.get("https://data.nthusa.tw/maps.json").json()

NOT_FOUND_EXCEPTION = HTTPException(status_code=404, detail="Not found")


@router.get(
    "/",
    response_model=list[LocationDetail],
    summary="取得所有地點列表",
)
async def get_all_location():
    """
    取得所有地點資訊。
    """
    location_list = []
    for campus_locations in map_data.values():
        for location_name, coordinates in campus_locations.items():
            location_list.append(
                LocationDetail(
                    name=location_name,
                    latitude=coordinates["latitude"],
                    longitude=coordinates["longitude"],
                )
            )
    return location_list


@router.get(
    "/search",
    response_model=list[LocationDetail],
    summary="使用名稱模糊搜尋地點",
)
async def search_location_by_get_method(
    name: str = Query(..., example="校門", description="要查詢的地點"),
):
    """
    使用名稱模糊搜尋地點資訊。
    """
    tmp_results = []
    for campus_locations in map_data.values():
        for location_name, coordinates in campus_locations.items():
            similarity = fuzz.partial_ratio(name, location_name)
            if similarity >= 60:
                tmp_results.append(
                    (
                        similarity,  # 儲存相似度
                        LocationDetail(
                            name=location_name,
                            latitude=coordinates["latitude"],
                            longitude=coordinates["longitude"],
                        ),
                    )
                )
    # 先判斷是否與查詢字串相同，再依相似度從高到低排序
    tmp_results.sort(key=lambda x: (x[1].name == name, x[0]), reverse=True)
    location_results = [item[1] for item in tmp_results]
    return location_results or NOT_FOUND_EXCEPTION
