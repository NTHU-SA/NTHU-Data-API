from typing import Union

from fastapi import APIRouter, HTTPException, Query
from thefuzz import fuzz

from src.api.schemas.departments import Department, DepartmentPerson
from src.utils import nthudata

router = APIRouter()
JSON_PATH = "directory.json"
FUZZY_SEARCH_THRESHOLD_DEPT = 60
FUZZY_SEARCH_THRESHOLD_PERSON = 70


@router.get("/", response_model=list[Department])
async def get_all_departments():
    """
    取得所有部門與人員資料。
    資料來源：[清華通訊錄](https://tel.net.nthu.edu.tw/nthusearch/)
    """
    _commit_hash, directory_data = await nthudata.get(JSON_PATH)
    return directory_data


@router.get(
    "/search",
    response_model=dict[str, Union[list[Department], list[DepartmentPerson]]],
)
async def fuzzy_search_departments_and_people(
    query: str = Query(..., example="校長"),
):
    """
    使用搜尋演算法搜尋全校部門與人員名稱。
    """
    _commit_hash, directory_data = await nthudata.get(JSON_PATH)
    
    # 搜尋部門
    department_results = []
    for dept in directory_data:
        similarity = fuzz.partial_ratio(query, dept["name"])
        if similarity >= FUZZY_SEARCH_THRESHOLD_DEPT:
            # 創建新的字典避免修改原始資料
            dept_with_score = {**dept, "similarity_score": similarity}
            department_results.append(dept_with_score)
    department_results.sort(key=lambda x: x["similarity_score"], reverse=True)

    # 搜尋人員
    people_results = []
    for dept in directory_data:
        for person in dept["details"]["people"]:
            similarity = fuzz.partial_ratio(query, person["name"])
            if similarity >= FUZZY_SEARCH_THRESHOLD_PERSON:
                # 創建新的字典避免修改原始資料
                person_with_score = {**person, "similarity_score": similarity}
                people_results.append(person_with_score)
    people_results.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {"departments": department_results, "people": people_results}


@router.get("/{index}", response_model=Department)
async def get_department_by_index(index: str):
    """
    根據部門索引取得特定部門資訊。
    """
    _commit_hash, directory_data = await nthudata.get(JSON_PATH)
    for dept in directory_data:
        if dept["index"] == index:
            return dept
    raise HTTPException(status_code=404, detail="Department not found")
