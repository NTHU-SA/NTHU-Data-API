from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, RootModel, field_validator


class CourseFieldName(str, Enum):
    id = "id"
    chinese_title = "chinese_title"
    english_title = "english_title"
    credit = "credit"
    size_limit = "size_limit"
    freshman_reservation = "freshman_reservation"
    object = "object"
    ge_type = "ge_type"
    language = "language"
    note = "note"
    suspend = "suspend"
    class_room_and_time = "class_room_and_time"
    teacher = "teacher"
    prerequisite = "prerequisite"
    limit_note = "limit_note"
    expertise = "expertise"
    program = "program"
    no_extra_selection = "no_extra_selection"
    required_optional_note = "required_optional_note"


class CourseLanguage(str, Enum):
    Chinese = "中"
    English = "英"


class CourseCreditOperation(str, Enum):
    GreaterThan = "gt"
    LessThan = "lt"
    GreaterThanOrEqual = "gte"
    LessThanOrEqual = "lte"


class CourseData(BaseModel):
    id: str = Field(..., description="課號")
    chinese_title: str = Field(..., description="課程中文名稱")
    english_title: str = Field(..., description="課程英文名稱")
    credit: str = Field(..., description="學分數")
    size_limit: str = Field(..., description="人限：若為空字串表示無人數限制")
    freshman_reservation: str = Field(
        ..., description="新生保留人數：若為0表示無新生保留人數"
    )
    object: str = Field(
        ...,
        description="通識對象：[代碼說明(課務組)](https://curricul.site.nthu.edu.tw/p/404-1208-11133.php)",
    )
    ge_type: str = Field(..., description="通識類別")
    language: CourseLanguage = Field(..., description='授課語言："中"、"英"')
    note: str = Field(..., description="備註")
    suspend: str = Field(..., description='停開註記："停開"或空字串')
    class_room_and_time: str = Field(
        ...,
        description="教室與上課時間：一間教室對應一個上課時間，中間以tab分隔；多個上課教室以new line字元分開",
    )
    teacher: str = Field(
        ...,
        description="授課教師：多位教師授課以new line字元分開；教師中英文姓名以tab分開",
    )
    prerequisite: str = Field(..., description="擋修說明：會有html entities")
    limit_note: str = Field(..., description="課程限制說明")
    expertise: str = Field(..., description="第一二專長對應：對應多個專長用tab字元分隔")
    program: str = Field(..., description="學分學程對應：用半形/分隔")
    no_extra_selection: str = Field(..., description="不可加簽說明")
    required_optional_note: str = Field(
        ..., description="必選修說明：多個必選修班級用tab字元分隔"
    )


class CourseCondition(BaseModel):
    row_field: CourseFieldName = Field(..., description="搜尋的欄位名稱")
    matcher: str = Field(..., description="搜尋的值")
    regex_match: bool = Field(False, description="是否使用正則表達式")


class CourseQueryOperation(str, Enum):
    and_ = "and"
    or_ = "or"


class CourseQueryCondition(RootModel):
    root: list[
        Union[Union["CourseQueryCondition", CourseCondition], CourseQueryOperation]
    ]

    @field_validator("root")
    def check_query(cls, v):
        POST_ERROR_INFO = " Also, FYI, the structure of query must be like this: [(nested) Condition, Operation, (nested) Condition]."
        if len(v) != 3:
            raise ValueError(
                "Each level of query must have 3 elements." + POST_ERROR_INFO
            )
        elif type(v[0]) not in [CourseQueryCondition, CourseCondition]:
            raise TypeError(
                "The first element of query must be a Condition or nested Condition."
                + POST_ERROR_INFO
            )
        elif type(v[1]) is not CourseQueryOperation:
            raise TypeError(
                'The second element of query must be a Operation (i.e. "and" or "or").'
                + POST_ERROR_INFO
            )
        elif type(v[2]) not in [CourseQueryCondition, CourseCondition]:
            raise TypeError(
                "The third element of query must be a Condition or nested Condition."
                + POST_ERROR_INFO
            )
        return v


class CourseListName(str, Enum):
    weeks16 = "16weeks"
    microcredits = "microcredits"
    xclass = "xclass"


class CourseSemester(str, Enum):
    latest = "latest"
    _11120 = "11120"
    _11210 = "11210"
    _11220 = "11220"
