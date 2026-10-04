"""
Dining router.

Handles HTTP endpoints for dining information.
"""

from fastapi import APIRouter, Query, Response

from data_api.api.schemas import dining as schemas
from data_api.domain.dining import services

router = APIRouter()


@router.get("", operation_id="getDiningData")
@router.get(
    "/",
    operation_id="getDiningDataDeprecated",
    deprecated=True,
    description="已棄用，請改用 GET /dining。查詢參數與回傳格式不變。",
)
async def get_dining_data(
    response: Response,
    building_name: schemas.DiningBuildingName = Query(None, description="餐廳建築名稱（可選）"),
    restaurant_name: str = Query(None, description="餐廳名稱（可選）"),
    fuzzy: bool = Query(
        True, description="是否進行模糊搜尋；停用時建築名稱完全比對，餐廳名稱使用子字串比對"
    ),
    schedule: schemas.DiningScheduleName | None = Query(
        None,
        description=(
            "營業日篩選（可選）；省略時不篩選。today 使用 Asia/Taipei 日期。"
            "依備註排除指定日休息的餐廳，不代表此刻營業中"
        ),
    ),
) -> list[schemas.DiningBuilding]:
    """
    取得所有餐廳及廠商資料。
    各篩選條件取交集，回傳格式固定依建築分組；營業日篩選後移除沒有符合餐廳的建築。
    資料來源：[總務處經營管理組](https://ddfm.site.nthu.edu.tw/p/404-1494-256455.php?Lang=zh-tw)
    """
    if fuzzy:
        commit_hash, data = await services.dining_service.fuzzy_search_dining_data(
            building_name=building_name,
            restaurant_name=restaurant_name,
            schedule=schedule,
        )
    else:
        commit_hash, data = await services.dining_service.get_dining_data(
            building_name=building_name,
            restaurant_name=restaurant_name,
            schedule=schedule,
        )
    if commit_hash is not None:
        response.headers["X-Data-Commit-Hash"] = commit_hash
    return data
