from fastapi import Path, Query

# for routers/buses.py
DEFAULT_LIMIT_DAY_CURRENT = 5
BUS_TYPE_PATH = Path(..., example="main", description="車種選擇 校本部公車 或 南大區間車")
BUS_DIRECTION_PATH = Path(..., example="up", description="上山或下山")
BUS_TYPE_QUERY = Query(..., example="main", description="車種選擇 校本部公車 或 南大區間車")
BUS_DAY_QUERY = Query(
    ...,
    example="weekday",
    description=f"平日、假日或目前時刻。選擇 current 預設回傳 {DEFAULT_LIMIT_DAY_CURRENT} 筆資料。",
)
BUS_DIRECTION_QUERY = Query(..., example="up", description="上山或下山")
STOPS_NAME_PATH = Path(..., example="北校門口", description="公車站牌名稱")
