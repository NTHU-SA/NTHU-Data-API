from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field, HttpUrl


class NewsletterArticle(BaseModel):
    title: Optional[str] = Field(..., description="電子報標題")
    link: Optional[HttpUrl] = Field(..., description="電子報網址")
    date: Optional[str] = Field(None, description="發布日期")


class NewsletterInfo(BaseModel):
    name: str = Field(..., description="該電子報名稱")
    link: HttpUrl = Field(..., description="該電子報網址")
    details: Dict = Field(..., description="該電子報詳細資訊")
    articles: list[NewsletterArticle] = Field(..., description="該電子報文章列表")


class NewsletterName(str, Enum):
    藝術文化總中心電子報 = "藝術文化總中心電子報"
    域報_Field_Cast = "域報 Field Cast"
    校長同意權人投票事務委員會 = "校長同意權人投票事務委員會"
    國立清華大學校長遴選委員會 = "國立清華大學校長遴選委員會"
    清華校友總會會務訊息 = "清華校友總會會務訊息"
    築思脈動_Pulse_of_Education = "築思脈動(Pulse of Education)"
    心諮系雙週例講座 = "心諮系雙週例講座"
    愛慾電子報報 = "愛慾電子報報"
    教學發展中心電子報_教師 = "教學發展中心電子報-教師"
    清華校友電子報 = "清華校友電子報"
    清華大學化學系電子報 = "清華大學化學系電子報"
    國立清華大學核工暨工科系友會電子報 = "國立清華大學核工暨工科系友會電子報"
    國立清華大學動機系系友電子報 = "國立清華大學動機系系友電子報"
    清華大學化工系友電子報 = "清華大學化工系友電子報"
    國立清華大學學生會電子報 = "國立清華大學學生會電子報"
    台灣語言學通訊 = "台灣語言學通訊"
    教務處綜合教務組電子報 = "教務處綜合教務組電子報"
    課務電子報 = "課務電子報"
    清華大學工工系電子報 = "清華大學工工系電子報"
    語文中心電子報 = "語文中心電子報"
    eecs_students = "eecs-students"
    科管院職涯電子報 = "科管院職涯電子報"
    人事室電子報 = "人事室電子報"
    研發處電子報_教職 = "研發處電子報-教職"
    學生事務報_學生 = "學生事務報-學生"
    數學系電子報 = "數學系電子報"
    電機工程學系電子報_學生 = "電機工程學系電子報(學生)"
    秘書處_全校教職員 = "秘書處-全校教職員"
    住宿書院電子報 = "住宿書院電子報"
    主計室電子報 = "主計室電子報"
    國立清華大學圖書館_學生 = "國立清華大學圖書館-學生"
    諮商中心_心窩報報 = "諮商中心-心窩報報"
    NTHU_Newsletter = "NTHU-Newsletter"
    NTHU_Division_of_Health_Service = "NTHU-Division of Health Service"
    人社院學士班電子報 = "人社院學士班電子報"
    人文社會學院電子報 = "人文社會學院電子報"
    新聞剪輯電子報 = "新聞剪輯電子報"
    清華簡訊 = "清華簡訊"
    計中_教育訓練 = "計中-教育訓練"
