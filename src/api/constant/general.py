from fastapi import Query

# for all routers
LIMITS_QUERY = Query(None, ge=1, example=5, description="最大回傳資料筆數")
