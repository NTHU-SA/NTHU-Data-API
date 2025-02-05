import json
import operator
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from cachetools import TTLCache, cached

from src.utils import cached_requests


# =============================================================================
# 課程資料類別
# =============================================================================
@dataclass
class CoursesData:
    id: str
    chinese_title: str
    english_title: str
    credit: str
    size_limit: str
    freshman_reservation: str
    object: str
    ge_type: str
    language: str
    note: str
    suspend: str
    class_room_and_time: str
    teacher: str
    prerequisite: str
    limit_note: str
    expertise: str
    program: str
    no_extra_selection: str
    required_optional_note: str

    @classmethod
    def from_dict(cls, init_data: dict) -> CoursesData:
        # 為避免依賴 dict 的順序，直接以 key 取值
        return cls(
            id=init_data.get("id", ""),
            chinese_title=init_data.get("chinese_title", ""),
            english_title=init_data.get("english_title", ""),
            credit=init_data.get("credit", ""),
            size_limit=init_data.get("size_limit", ""),
            freshman_reservation=init_data.get("freshman_reservation", ""),
            object=init_data.get("object", ""),
            ge_type=init_data.get("ge_type", ""),
            language=init_data.get("language", ""),
            note=init_data.get("note", ""),
            suspend=init_data.get("suspend", ""),
            class_room_and_time=init_data.get("class_room_and_time", ""),
            teacher=init_data.get("teacher", ""),
            prerequisite=init_data.get("prerequisite", ""),
            limit_note=init_data.get("limit_note", ""),
            expertise=init_data.get("expertise", ""),
            program=init_data.get("program", ""),
            no_extra_selection=init_data.get("no_extra_selection", ""),
            required_optional_note=init_data.get("required_optional_note", ""),
        )

    def __repr__(self) -> str:
        return str(self.__dict__)


# =============================================================================
# 條件判斷
# =============================================================================
@dataclass
class Condition:
    row_field: str
    matcher: Union[str, re.Pattern]
    regex_match: bool = False

    def __post_init__(self):
        # 統一使用小寫的欄位名稱以方便比對
        self.row_field = self.row_field.lower()

    def check(self, course: CoursesData) -> bool:
        field_data = getattr(course, self.row_field, "")
        if self.regex_match:
            return re.search(self.matcher, field_data) is not None
        else:
            return field_data == self.matcher


# 複合條件的類型（支援 Condition、布林值或巢狀結構）
ConditionType = Union[Condition, bool, dict, list]


@dataclass
class Conditions:
    # condition_stat 儲存條件樹，預設為單一條件結構，
    # 若傳入 list_build_target 則直接作為複合條件樹使用
    condition_stat: Any = field(default=None)
    course: Optional[CoursesData] = field(default=None, init=False)

    def __init__(
        self,
        row_field: Optional[str] = None,
        matcher: Optional[Union[str, re.Pattern]] = None,
        regex_match: bool = False,
        *,
        list_build_target: Optional[List[Any]] = None,
    ):
        if list_build_target is not None:
            self.condition_stat = list_build_target
        elif row_field is not None and matcher is not None:
            # 預設結構為單一條件，後面再與其他條件結合
            self.condition_stat = [
                Condition(row_field, matcher, regex_match),
                "and",
                True,
            ]
        else:
            raise ValueError("必須傳入 row_field 與 matcher，或 list_build_target")
        self.course = None

    def __and__(self, other: "Conditions") -> "Conditions":
        return Conditions(
            list_build_target=[self.condition_stat, "and", other.condition_stat]
        )

    def __or__(self, other: "Conditions") -> "Conditions":
        return Conditions(
            list_build_target=[self.condition_stat, "or", other.condition_stat]
        )

    def _solve_condition_stat(self, data: Any) -> bool:
        """
        遞迴拆解條件樹，結構固定為 [lhs, op, rhs]，其中 lhs 與 rhs 可能為 Condition、布林值或巢狀結構。
        """
        if not isinstance(data, list):
            # 若 data 不是 list 則直接檢查條件
            return self._check_condition(data)
        lhs, op, rhs = data
        lhs_value = self._check_condition(lhs)
        rhs_value = self._check_condition(rhs)
        match op:
            case "and":
                return lhs_value and rhs_value
            case "or":
                return lhs_value or rhs_value
            case _:
                raise ValueError(f"Unknown operator: {op}")

    def _check_condition(self, item: ConditionType) -> bool:
        if isinstance(item, dict):
            # 若為 dict，視為傳入 Condition 的關鍵字參數
            return Condition(**item).check(self.course)
        elif isinstance(item, list):
            return self._solve_condition_stat(item)
        elif isinstance(item, Condition):
            return item.check(self.course)
        elif isinstance(item, bool):
            return item
        else:
            raise TypeError(f"無法處理的條件項目：{item}")

    def accept(self, course: CoursesData) -> bool:
        """根據 condition_stat 判斷該課程是否滿足所有條件"""
        self.course = course
        return self._solve_condition_stat(self.condition_stat)


# =============================================================================
# Processor - 課程資料處理器
# =============================================================================
class Processor:
    NTHU_COURSE_DATA_URL = "https://api-json.nthusa.tw/courses/lastest.json"

    def __init__(self, json_path: Optional[str] = None) -> None:
        self.course_data: List[CoursesData] = self._get_course_data(json_path)

    @cached(cache=TTLCache(maxsize=1, ttl=60 * 60))
    def _get_course_data(self, json_path: Optional[str] = None) -> List[CoursesData]:
        """
        取得課程資料，若提供 json_path 則由檔案讀取，
        否則利用 cached_requests 從網路上取得資料。
        """
        if json_path:
            with open(json_path, "r", encoding="utf-8") as f:
                course_data_dict_list = json.load(f)
        else:
            course_data_resp, _ = cached_requests.get(
                self.NTHU_COURSE_DATA_URL, update=True, auto_headers=True
            )
            course_data_dict_list = json.loads(course_data_resp)
        return [CoursesData.from_dict(data) for data in course_data_dict_list]

    def update(self, json_path: Optional[str] = None) -> None:
        self.course_data = self._get_course_data(json_path)

    def list_selected_fields(self, field: str) -> List[str]:
        """回傳所有課程中指定欄位的非空字串集合"""
        fields_set = {
            getattr(course, field).strip()
            for course in self.course_data
            if getattr(course, field).strip()
        }
        return list(fields_set)

    def list_credit(self, credit: float, op: str = "") -> List[CoursesData]:
        ops = {
            "gt": operator.gt,
            "lt": operator.lt,
            "gte": operator.ge,
            "lte": operator.le,
            "eq": operator.eq,
            "": operator.eq,
        }
        cmp_op = ops.get(op, operator.eq)
        return [
            course
            for course in self.course_data
            if cmp_op(float(course.credit), credit)
        ]

    def query(self, conditions: Conditions) -> List[CoursesData]:
        """搜尋所有符合條件的課程，傳入的 conditions 為複合條件樹"""
        return [course for course in self.course_data if conditions.accept(course)]


# =============================================================================
# 主程式測試區
# =============================================================================
if __name__ == "__main__":
    from loguru import logger

    processor = Processor()

    # 條件範例 1：中文課名為 "文化人類學專題" 且課號為 "11210ANTH651000"
    condition1 = Conditions("CHINESE_TITLE", "文化人類學專題") & Conditions(
        "ID", "11210ANTH651000"
    )
    result1 = processor.query(condition1)
    logger.info("中文課名 與 ID (有一堂課): {}", len(result1))
    logger.info(result1)

    # 條件範例 2：中文課名為 "化人類學專題" 或課號為 "11210ANTH651000"
    condition2 = Conditions("CHINESE_TITLE", "化人類學專題") | Conditions(
        "ID", "11210ANTH651000"
    )
    result2 = processor.query(condition2)
    logger.info("中文課名 或 ID (有一堂課): {}", len(result2))
    logger.info(result2)

    # 條件範例 3：中文課名包含 "產業"
    condition3 = Conditions("CHINESE_TITLE", "產業", regex_match=True)
    result3 = processor.query(condition3)
    logger.info("中文課名包含 '產業' 的課程 (取前5筆): {}", result3[:5])

    # 條件範例 4：中文課名包含 "產業" 且 CREDIT 為 "2" 且課號包含 "GE"（通識課程）
    condition4 = (
        Conditions("CHINESE_TITLE", "產業", regex_match=True)
        & Conditions("CREDIT", "2")
        & Conditions("ID", "GE", regex_match=True)
    )
    result4 = processor.query(condition4)
    logger.info("符合複合條件的課程 (取前5筆): {}", result4[:5])

    logger.info("總開課數: {}", len(processor.course_data))
    # 條件範例 5：中文授課 或 英文授課
    condition_ce = Conditions("LANGUAGE", "中") | Conditions("LANGUAGE", "英")
    result_ce = processor.query(condition_ce)
    logger.info("中文授課 或 英文授課 開課數量: {}", len(result_ce))

    # 條件範例 6：中文授課
    condition_c = Conditions("LANGUAGE", "中")
    result_c = processor.query(condition_c)
    logger.info("中文授課 開課數量: {}", len(result_c))

    # 條件範例 7：英文授課
    condition_e = Conditions("LANGUAGE", "英")
    result_e = processor.query(condition_e)
    logger.info("英文授課 開課數量: {}", len(result_e))
