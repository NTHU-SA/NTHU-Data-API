import json
import re

import requests
from cachetools import TTLCache, cached


class CoursesData:
    """課程資料的資料類別。

    Attributes:
        id(``str``): 科號。
        chinese_title(``str``): 課程中文名稱。
        english_title(``str``): 課程英文名稱。
        credit(``str``): 學分數。
        size_limit(``str``): 人限：若為空字串表示無人數限制。
        freshman_reservation(``str``): 新生保留人數：若為0表示無新生保留人數。
        object(``str``): 通識對象：[代碼說明(課務組)](https://curricul.site.nthu.edu.tw/p/404-1208-11133.php)。
        ge_type(``str``): 通識類別。
        language(``str``): 授課語言："中"、"英"。
        note(``str``): 備註。
        suspend(``str``): 停開註記："停開"或空字串。
        class_room_and_time(``str``):教室與上課時間：一間教室對應一個上課時間，中間以tab分隔；多個上課教室以new line字元分開。
        teacher(``str``): 授課教師：多位教師授課以new line字元分開；教師中英文姓名以tab分開。
        prerequisite(``str``): 擋修說明：會有html entities。
        limit_note(``str``): 課程限制說明。
        expertise(``str``): 第一二專長對應：對應多個專長用tab字元分隔。
        program(``str``): 學分學程對應：用半形/分隔。
        no_extra_selection(``str``): 不可加簽說明。
        required_optional_note(``str``): 必選修說明：多個必選修班級用tab字元分隔。
    """

    def __init__(self, init_data: dict) -> None:
        keys = [
            "id",
            "chinese_title",
            "english_title",
            "credit",
            "size_limit",
            "freshman_reservation",
            "object",
            "ge_type",
            "language",
            "note",
            "suspend",
            "class_room_and_time",
            "teacher",
            "prerequisite",
            "limit_note",
            "expertise",
            "program",
            "no_extra_selection",
            "required_optional_note",
        ]

        init_data_values = list(init_data.values())

        for i, key in enumerate(keys):
            setattr(self, key, init_data_values[i])

    def __repr__(self) -> str:
        return str(vars(self))


class Condition:
    """利用資訊確認 query 是否成功的最小單位。

    比對課程資料的欄位，確認是否滿足設定的配對（match）條件，可使用全等比對或正則表達式。

    Attributes:
        row_field(``str``): 用以指定要配對的欄位。
        matcher(``str``): 判斷式。
        regex_match(``bool``): 當 ``True`` 時將 matcher 視為正則表達式，反之視為普通字串並使用全等比對。
    """

    def __init__(self, row_field: str, matcher: str, regex_match: bool) -> None:
        self.row_field = row_field.lower()
        self.matcher = matcher
        self.regex_match = regex_match

    def check(self, course: CoursesData) -> bool:
        """確認是否滿足判斷式。"""

        course_data_dict = vars(course)
        field_data = course_data_dict[self.row_field]

        if self.regex_match == True:
            match_res = re.search(self.matcher, field_data)
            return False if match_res == None else True
        else:
            return field_data == self.matcher


class Conditions:
    """包裝 Condition 類別，組合成特別的結構以處理條件之 AND 、 OR 邏輯。

    將條件邏輯包裝進 list，模擬不同條件間 AND 、 OR 的邏輯組合。初始化參數與 Condition 相同，是傳遞參數的角色。

    Attributes:
        condition_stat(``list[Condition | str | bool]``): 特定結構模擬出的表達式格式。
        course(``Course``): 當前套用條件的課程。
    """

    def __init__(
        self, row_field: str, matcher: str | re.Pattern[str], regex_match: bool = False
    ) -> None:
        self.condition_stat = [Condition(row_field, matcher, regex_match), "and", True]
        self.course = None

    def __and__(self, condition2):
        """Override bitwise ``and`` operator 當成 logical ``and``。"""

        self.condition_stat = [self.condition_stat, "and", condition2.condition_stat]
        return self

    def __or__(self, condition2):
        """Override bitwise ``or`` operator 當成 logical ``or``。"""

        self.condition_stat = [self.condition_stat, "or", condition2.condition_stat]
        return self

    def _solve_condition_stat(self, data: list) -> bool:
        """遞迴函式，拆分成 左手邊、運算子、右手邊，將左右手遞迴解成 ``bool`` 之後，再算出這一層的結果。"""

        lhs, op, rhs = data

        if type(lhs) == list:
            lhs = self._solve_condition_stat(lhs)
        elif type(lhs) == Condition:
            lhs = lhs.check(self.course)

        if type(rhs) == list:
            rhs = self._solve_condition_stat(rhs)
        elif type(rhs) == Condition:
            rhs = rhs.check(self.course)

        if op == "and":
            return lhs and rhs
        elif op == "or":
            return lhs or rhs

    def accept(self, course: CoursesData) -> bool:
        """包裝遞迴函式供外部使用，回傳以該課程計算多個條件運算後的結果。"""

        self.course = course
        return self._solve_condition_stat(self.condition_stat)


class Processor:
    """可以添加 query 條件的課程資料。

    Attributes:
        course_data (``list[Course]``): 轉換為 Course 類別的課程資料。
    """

    NTHU_COURSE_DATA_URL = (
        "https://www.ccxp.nthu.edu.tw/ccxp/INQUIRE/JH/OPENDATA/open_course_data.json"
    )

    def __init__(self, json_path=None) -> None:
        self.course_data = self._get_course_data(json_path)

    @cached(cache=TTLCache(maxsize=1, ttl=60 * 60))
    def _get_course_data(self, json_path=None) -> list[CoursesData]:
        """TODO: error handler."""
        if json_path != None:
            # 使用 json 模組讀取檔案
            with open(json_path, "r", encoding="utf-8") as f:
                course_data_dict_list = json.load(f)
        else:
            # 使用 requests 模組取得網頁資料
            course_data_resp = requests.get(self.NTHU_COURSE_DATA_URL)
            course_data_dict_list = json.loads(course_data_resp.text)
        return list(map(CoursesData, course_data_dict_list))

    def update(self, json_path=None):
        self.course_data = self._get_course_data(json_path)

    def list_selected_fields(self, field) -> list:
        """列出所有課程的某個欄位。
        Args:
            field (str): 欲列出的欄位。
        Returns:
            list: 所有課程的某個欄位。
        """
        fields_list = [
            getattr(course, field).strip()
            for course in self.course_data
            if getattr(course, field).strip()
        ]
        fields_list = list(set(fields_list))
        return fields_list

    def list_credit(self, credit: float, op: str = None) -> list:
        res = []
        if op == None or op == "":
            res = [
                course for course in self.course_data if float(course.credit) == credit
            ]
        elif op == "gt":
            res = [
                course for course in self.course_data if float(course.credit) > credit
            ]
        elif op == "lt":
            res = [
                course for course in self.course_data if float(course.credit) < credit
            ]
        elif op == "gte":
            res = [
                course for course in self.course_data if float(course.credit) >= credit
            ]
        elif op == "lte":
            res = [
                course for course in self.course_data if float(course.credit) <= credit
            ]

        return res

    def query(self, conditions: Conditions) -> list[CoursesData]:
        """搜尋所有符合條件的課程。

        Args:
            conditions (Conditions): 欲套用的條件式。

        Returns:
            list[Course]: 所有符合條件的課程。
        """

        res = []

        for course in self.course_data:
            if conditions.accept(course):
                res.append(course)

        return res


if __name__ == "__main__":
    from loguru import logger

    course_data = Processor(json_path="data/courses/11210.json")

    # 中文課名為"文化人類學專題" 且 課號為"11210ANTH651000"
    condition1 = Conditions("CHINESE_TITLE", "文化人類學專題") & Conditions(
        "ID", "11210ANTH651000"
    )
    logger.info("中文課名 與 ID (有一堂課): ", len(course_data.query(condition1)))
    logger.info(course_data.query(condition1))

    # 中文課名為"化人類學專題" 或 課號為"11210ANTH651000"
    condition2 = Conditions("CHINESE_TITLE", "化人類學專題") | Conditions(
        "ID", "11210ANTH651000"
    )
    logger.info("中文課名 或 ID (有一堂課): ", len(course_data.query(condition2)))
    logger.info(course_data.query(condition2))

    # 中文課名包含"產業"
    condition3 = Conditions("CHINESE_TITLE", "產業", True)
    logger.info(course_data.query(condition3)[:5])

    # 中文課名包含"產業" 且 課號包含 "GE"，即通識課程
    condition4 = (
        Conditions("CHINESE_TITLE", "產業", True)
        & Conditions("CREDIT", "2")
        & Conditions("ID", "GE", True)
    )
    logger.info(course_data.query(condition4)[:5])

    logger.info(f"總開課數: {len(course_data.course_data)}")
    # 中文授課 或 英文授課
    condition_ce = Conditions("LANGUAGE", "中") | Conditions("LANGUAGE", "英")
    logger.info(f"中文授課 或 英文授課 開課數量: {len(course_data.query(condition_ce))}")
    # 中文授課
    condition_c = Conditions("LANGUAGE", "中")
    logger.info(f"中文授課 開課數量: {len(course_data.query(condition_c))}")
    # 英文授課
    condition_e = Conditions("LANGUAGE", "英")
    logger.info(f"英文授課 開課數量: {len(course_data.query(condition_e))}")
