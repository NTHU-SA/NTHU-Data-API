import operator
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Union

from src import utils


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

    # 定義各個欄位可能出現的關鍵字（同義字）
    FIELD_MAPPING = {
        "id": ["科號", "ID", "id"],
        "chinese_title": ["課程中文名稱", "CHINESE_TITLE", "chinese_title"],
        "english_title": ["課程英文名稱", "ENGLISH_TITLE", "english_title"],
        "credit": ["學分數", "CREDIT", "credit"],
        "size_limit": ["人限", "SIZE_LIMIT", "size_limit"],
        "freshman_reservation": [
            "新生保留人數",
            "FRESHMAN_RESERVATION",
            "freshman_reservation",
        ],
        "object": ["通識對象", "OBJECT", "object"],
        "ge_type": ["通識類別", "GE_TYPE", "ge_type"],
        "language": ["授課語言", "LANGUAGE", "language"],
        "note": ["備註", "NOTE", "note"],
        "suspend": ["停開註記", "SUSPEND", "suspend"],
        "class_room_and_time": [
            "教室與上課時間",
            "CLASS_ROOM_AND_TIME",
            "class_room_and_time",
        ],
        "teacher": ["授課教師", "TEACHER", "teacher"],
        "prerequisite": ["擋修說明", "PREREQUISITE", "prerequisite"],
        "limit_note": ["課程限制說明", "LIMIT_NOTE", "limit_note"],
        "expertise": ["第一二專長對應", "EXPERTISE", "expertise"],
        "program": ["學分學程對應", "PROGRAM", "program"],
        "no_extra_selection": [
            "不可加簽說明",
            "NO_EXTRA_SELECTION",
            "no_extra_selection",
        ],
        "required_optional_note": [
            "必選修說明",
            "REQUIRED_OPTIONAL_NOTE",
            "required_optional_note",
        ],
    }

    @classmethod
    def from_dict(cls, init_data: dict) -> "CoursesData":
        """
        根據 FIELD_MAPPING 從原始資料中找出對應的欄位資料，
        若找不到則給空字串。
        """
        # 準備一個新的 dict，存放轉換後的資料
        data = {}
        for canonical_field, keywords in cls.FIELD_MAPPING.items():
            # 尋找 init_data 中符合任一關鍵字的欄位
            found = False
            for key in keywords:
                if key in init_data:
                    data[canonical_field] = init_data[key]
                    found = True
                    break
            if not found:
                data[canonical_field] = ""
        return cls(**data)

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
            # 使用小寫的 canonical 欄位名稱
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
        遞迴拆解條件樹，結構固定為 [lhs, op, rhs]，
        其中 lhs 與 rhs 可能為 Condition、布林值或巢狀結構。
        """
        if not isinstance(data, list):
            # 若 data 不是 list 則直接檢查條件
            return self._check_condition(data)
        lhs, op, rhs = data
        lhs_value = self._check_condition(lhs)
        rhs_value = self._check_condition(rhs)
        if op == "and":
            return lhs_value and rhs_value
        elif op == "or":
            return lhs_value or rhs_value
        else:
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
    """
    課程資料處理
    """

    def __init__(self) -> None:
        self.course_data: List[CoursesData] = []
        self.last_commit_hash = None

    async def update_data(self) -> None:
        self.last_commit_hash, self.course_data = await utils.get("courses.json")

        # 將 dict 轉換為 CoursesData 物件
        self.course_data = list(map(CoursesData.from_dict, self.course_data))

        print(self.last_commit_hash)

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
    processor = Processor()

    # 範例資料（原始資料中使用中文欄位名稱）
    sample_data = {
        "科號": "11320AES 370100",
        "課程中文名稱": "環境科學與工程",
        "課程英文名稱": "Environmental Science and Engineering",
        "學分數": "3",
        "人限": "",
        "新生保留人數": "0",
        "通識對象": " ",
        "通識類別": "",
        "授課語言": "中",
        "備註": " ",
        "停開註記": "",
        "教室與上課時間": "BMES醫環501\tR7R8R9\n",
        "授課教師": "吳劍侯\tWU, CHIEN-HOU\n",
        "擋修說明": "",
        "課程限制說明": "",
        "第一二專長對應": "環境科技學程(第二專長)",
        "學分學程對應": "(跨領域)永續發展與環境管理學分學程",
        "不可加簽說明": "",
        "必選修說明": "分環所113M  選修\t原科院學士班111B  選修\t",
    }
    # 可用 sample_data 測試 from_dict：
    course_sample = CoursesData.from_dict(sample_data)
    print("轉換後的課程資料: {}", course_sample)

    # 以下為原有的查詢條件範例
    # 範例 1：中文課名為 "文化人類學專題" 且課號為 "11210ANTH651000"
    condition1 = Conditions("chinese_title", "文化人類學專題") & Conditions(
        "id", "11210ANTH651000"
    )
    result1 = processor.query(condition1)
    print("中文課名 與 ID (有一堂課): {}", len(result1))
    print(result1)

    # 範例 2：中文課名為 "化人類學專題" 或課號為 "11210ANTH651000"
    condition2 = Conditions("chinese_title", "化人類學專題") | Conditions(
        "id", "11210ANTH651000"
    )
    result2 = processor.query(condition2)
    print("中文課名 或 ID (有一堂課): {}", len(result2))
    print(result2)

    # 範例 3：中文課名包含 "產業"
    condition3 = Conditions("chinese_title", "產業", regex_match=True)
    result3 = processor.query(condition3)
    print("中文課名包含 '產業' 的課程 (取前5筆): {}", result3[:5])

    # 範例 4：中文課名包含 "產業" 且 credit 為 "2" 且課號包含 "GE"（通識課程）
    condition4 = (
        Conditions("chinese_title", "產業", regex_match=True)
        & Conditions("credit", "2")
        & Conditions("id", "GE", regex_match=True)
    )
    result4 = processor.query(condition4)
    print("符合複合條件的課程 (取前5筆): {}", result4[:5])

    print("總開課數: {}", len(processor.course_data))
    # 範例 5：中文授課 或 英文授課
    condition_ce = Conditions("language", "中") | Conditions("language", "英")
    result_ce = processor.query(condition_ce)
    print("中文授課 或 英文授課 開課數量: {}", len(result_ce))

    # 範例 6：中文授課
    condition_c = Conditions("language", "中")
    result_c = processor.query(condition_c)
    print("中文授課 開課數量: {}", len(result_c))

    # 範例 7：英文授課
    condition_e = Conditions("language", "英")
    result_e = processor.query(condition_e)
    print("英文授課 開課數量: {}", len(result_e))
