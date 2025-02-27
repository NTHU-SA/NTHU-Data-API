from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query
from thefuzz import fuzz

from src.api.models.departments import Department, Person

router = APIRouter()
departments_data = requests.get("https://data.nthusa.tw/directory.json").json()


@router.get("/", response_model=List[Department], summary="取得所有部門列表")
async def read_all_departments():
    """
    取得所有部門列表。
    """
    return departments_data


@router.get(
    "/fuzzy-search",
    response_model=List[Department],
    summary="模糊搜尋部門名稱",
)
async def fuzzy_search_departments(
    name: str = Query(..., example="校長", title="部門名稱模糊關鍵字"),
):
    """
    使用模糊搜尋演算法搜尋部門名稱，找出最相似的部門。
    """
    results = []
    for dept in departments_data:
        similarity = fuzz.partial_ratio(
            name, dept["name"]
        )  # 使用 partial_ratio 進行模糊比對
        if similarity >= 60:  # 相似度門檻值，可以調整
            dept["similarity_score"] = similarity  # 可以加入相似度分數方便排序
            results.append(dept)

    results.sort(
        key=lambda x: x.get("similarity_score", 0), reverse=True
    )  # 根據相似度排序
    return results


@router.get(
    "/{index}", response_model=List[Department], summary="依據 index 取得特定部門"
)  # 需要把它往下移，不然 fuzzy-search 會被擋住
async def read_department_by_index(index: str):
    for dept in departments_data:
        if dept["index"] == index:
            return [dept]
    raise HTTPException(status_code=404, detail="Department not found")


@router.get(
    "/people/fuzzy-search", response_model=List[Person], summary="模糊搜尋人員名稱"
)
async def fuzzy_search_people(
    name: str = Query(..., example="高為元", title="人員名稱模糊關鍵字")
):
    """
    使用模糊搜尋演算法搜尋人員名稱，找出最相似的人員 (跨部門)。
    """
    results = []
    for dept in departments_data:
        for person in dept["details"]["people"]:
            similarity = fuzz.partial_ratio(name, person["name"])
            if similarity >= 70:  # 相似度門檻值，可以調整
                person["similarity_score"] = similarity
                results.append(person)

    results.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
    return results
