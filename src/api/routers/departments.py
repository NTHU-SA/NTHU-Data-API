from typing import Dict, Union

from fastapi import APIRouter, HTTPException, Query
from thefuzz import fuzz

from src.api.schemas.departments import Department, Person
from src.utils import nthudata

router = APIRouter()
json_path = "directory.json"


@router.get("/", response_model=list[Department], summary="取得所有部門列表")
async def read_all_departments():
    """
    取得所有部門列表。
    """
    _commit_hash, directory_data = await nthudata.get(json_path)
    return directory_data


@router.get(
    "/search",
    response_model=Dict[str, Union[list[Department], list[Person]]],
    summary="關鍵字搜尋部門與人員名稱",
)
async def fuzzy_search_departments(
    name: str = Query(..., example="校長", title="模糊搜尋關鍵字"),
):
    """
    使用搜尋演算法搜尋部門與人員名稱。
    """
    _commit_hash, directory_data = await nthudata.get(json_path)
    department_results = []
    for dept in directory_data:
        similarity = fuzz.partial_ratio(name, dept["name"])
        if similarity >= 60:  # 相似度門檻值，可以調整
            dept["similarity_score"] = similarity  # 加入相似度分數方便排序
            department_results.append(dept)
    department_results.sort(
        key=lambda x: x.get("similarity_score", 0), reverse=True
    )  # 根據相似度排序

    people_results = []
    for dept in directory_data:
        for person in dept["details"]["people"]:
            similarity = fuzz.partial_ratio(name, person["name"])
            if similarity >= 70:  # 相似度門檻值，可以調整
                person["similarity_score"] = similarity
                people_results.append(person)
    people_results.sort(
        key=lambda x: x.get("similarity_score", 0), reverse=True
    )  # 根據相似度排序

    return {"departments": department_results, "people": people_results}


@router.get(
    "/{index}", response_model=list[Department], summary="依據 index 取得特定部門"
)  # 需要把它往下移，不然 search 會被擋住
async def read_department_by_index(index: str):
    _commit_hash, directory_data = await nthudata.get(json_path)
    for dept in directory_data:
        if dept["index"] == index:
            return [dept]
    raise HTTPException(status_code=404, detail="Department not found")
