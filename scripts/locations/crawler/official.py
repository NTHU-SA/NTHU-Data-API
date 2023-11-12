import json
import re

# https://www.nthu.edu.tw/campusmap
# https://campusmap.cc.nthu.edu.tw/
# https://campusmap.cc.nthu.edu.tw/en
# https://campusmap.cc.nthu.edu.tw/sd
# https://campusmap.cc.nthu.edu.tw/sden

data_main = """
    <option value="24.796538, 120.997015">光復路校門</option> 
    <option value="24.79557, 120.99748">東校門</option> 
    <option value="24.79570, 120.99652">第四綜合大樓</option>
    <option value="24.79534, 120.99649">創新育成中心(舊)</option>
    <option value="24.796533, 120.995204">動機化學實驗館</option> 
    <option value="24.79620, 120.99599">化學館</option>
    <option value="24.79519, 120.99604">工程一館</option>
    <option value="24.79629, 120.99507">化工館</option>
    <option value="24.79538, 120.99457">學習資源中心(旺宏館)</option>
    <option value="24.79625, 120.99431">醫輔大樓</option>
    <option value="24.79634, 120.99256">工程三館</option>
    <option value="24.798056, 120.990027">水源街西校門</option>
    <option value="24.79641, 120.99171">材料科技館</option>
    <option value="24.79591, 120.99211">台達館</option>
    <option value="24.795557, 120.993703">教育館</option>
    <option value="24.79434, 120.99240">物理館</option>
    <option value="24.79508, 120.99213">資訊電機館</option>
    <option value="24.79507, 120.99358">第三綜合大樓</option>
    <option value="24.794660, 120.994548">第一綜合大樓(行政大樓、合勤演藝廳)</option>
    <option value="24.79438, 120.99325">第二綜合大樓(藝術中心、計算機與通訊中心)</option>
    <option value="24.793916, 120.993137">蘇格貓底咖啡屋</option>
    <option value="24.793896, 120.992822">清華名人堂</option>
    <option value="24.79322, 120.99294">小吃部</option>
    <option value="24.79250, 120.99394">水木生活中心</option>
    <option value="24.792235, 120.994594">風雲樓</option>
    <option value="24.79357, 120.99388">大禮堂</option> 
    <option value="24.79507, 120.99128">游泳池</option> 
    <option value="24.79434, 120.99131">舊體育館(桌球館)</option> 
    <option value="24.79361, 120.99148">體育館</option> 
    <option value="24.79360, 120.99193">蒙民偉樓(學生活動中心)</option> 
    <option value="24.795087, 120.989845">校友體育館</option>  
    <option value="24.79277, 120.99315">明齋</option>
    <option value="24.79260, 120.99319">平齋</option>
    <option value="24.79220, 120.99345">善齋</option>
    <option value="24.79179, 120.99402">華齋</option>
    <option value="24.79161, 120.99509">實齋</option>
    <option value="24.79151, 120.99570">仁齋</option>
    <option value="24.79136, 120.99677">碩齋</option>
    <option value="24.79125, 120.99529">禮齋</option>
    <option value="24.79123, 120.99571">信齋 A</option>
    <option value="24.79065, 120.99447">儒齋</option>
    <option value="24.79147, 120.99393">誠齋</option>
    <option value="24.79102, 120.99391">義齋</option>
    <option value="24.79055, 120.99372">鴻齋</option>
    <option value="24.79012, 120.99301">學齋</option>
    <option value="24.79127, 120.99314">清齋</option>
    <option value="24.79164, 120.99290">新齋</option>
    <option value="24.79287, 120.99185">雅齋</option>
    <option value="24.79258, 120.99129">靜齋</option>
    <option value="24.79217, 120.99125">慧齋</option>
    <option value="24.79201, 120.99078">文齋</option>
    <option value="24.797912, 120.990932">清華會館</option>
    <option value="24.796913, 120.991228">第二招待所</option>
    <option value="24.79457, 120.99535">成功湖</option>
    <option value="24.79355, 120.99243">水圳區</option>
    <option value="24.78853, 120.99125">雞蛋面區</option>
    <option value="24.78938, 120.98876">梅谷區</option>
    <option value="24.79418, 120.99258">昆明湖</option>
    <option value="24.79279, 120.99019">梅亭</option>
    <option value="24.787981, 120.990554">奕亭</option>
    <option value="24.79169, 120.99168">駐警隊</option>
    <option value="24.79111, 120.99085">工科館</option>
    <option value="24.790759, 120.991360">李存敏館</option>
    <option value="24.79079, 120.99133">原科中心</option>
    <option value="24.78987, 120.98970">人文社會學館</option>
    <option value="24.78990, 120.99026">生命科學一館</option>
    <option value="24.78945, 120.98970">生命科學二館</option>
    <option value="24.78928, 120.99140">生醫工程與環境科學館</option> 
    <option value="24.789785, 120.992187">原子爐</option>
    <option value="24.78932, 120.99216">同位素館</option>
    <option value="24.78985, 120.99127">生物科技館</option>
    <option value="24.78876, 120.99168">光電研究中心-高能光電實驗室</option>
    <option value="24.78877, 120.99207">加速器館</option>
    <option value="24.78699, 120.98795">台積館</option>
    <option value="24.786774, 120.988813">寶山路南校門</option>
"""

data_main_en = """
    <option value="24.796538, 120.997015">North gate</option> 
    <option value="24.79557, 120.99748">East gate</option> 
    <option value="24.79570, 120.99652">Research and Development Building</option>
    <option value="24.79534, 120.99649">Center of Innovative Incubator</option>
    <option value="24.796533, 120.995204">Chemistry and Power Mechanical Engineering Building</option> 
    <option value="24.79620, 120.99599">Chemistry Building</option>
    <option value="24.79519, 120.99604">Engineering Building I</option>
    <option value="24.79629, 120.99507">Chemical Engineering Building</option>
    <option value="24.79538, 120.99457">Learning Resource Center(Macronix Building)</option>
    <option value="24.79625, 120.99431">Clinic and Counseling Center</option>
    <option value="24.79634, 120.99256">Engineering Building III</option>
    <option value="24.798056, 120.990027">West gate</option>
    <option value="24.79641, 120.99171">Materials Science and Technology Building</option>
    <option value="24.79591, 120.99211">DeltaHall</option>
    <option value="24.795557, 120.993703">Education Building</option>
    <option value="24.79434, 120.99240">Physics Building</option>
    <option value="24.79508, 120.99213">Electrical Engineering and Computer Science Building</option>
    <option value="24.79507, 120.99358">General Building III</option>
    <option value="24.794660, 120.994548">General Building I</option>
    <option value="24.79438, 120.99325">General Building II</option>
    <option value="24.793916, 120.993137">Casa de Socrates café</option>
    <option value="24.793896, 120.992822">TsingHua Hall of Fame</option>
    <option value="24.79322, 120.99294">Food Court</option>
    <option value="24.79250, 120.99394">Shui Mu Student Center</option>
    <option value="24.792235, 120.994594">Feng Yun Building</option>
    <option value="24.79357, 120.99388">Auditorium</option> 
    <option value="24.79507, 120.99128">Swimming Pool</option> 
    <option value="24.79434, 120.99131">Table Tennis Arena</option> 
    <option value="24.79361, 120.99148"> Gymnasium</option> 
    <option value="24.79360, 120.99193">Mong Man Wai Building (Student Union)</option> 
    <option value="24.795087, 120.989845">Alumni Gymnasium</option>  
    <option value="24.79277, 120.99315">Dormitory Ming</option>
    <option value="24.79260, 120.99319">Dormitory Ping</option>
    <option value="24.79220, 120.99345">Dormitory Shan</option>
    <option value="24.79179, 120.99402">Dormitory Hua</option>
    <option value="24.79161, 120.99509">Dormitory Shyr</option>
    <option value="24.79151, 120.99570">Dormitory Jen</option>
    <option value="24.79136, 120.99677">Dormitory Shuo</option>
    <option value="24.79125, 120.99529">Dormitory Li</option>
    <option value="24.79123, 120.99571">Dormitory Shinn A</option>
    <option value="24.79065, 120.99447">Dormitory Ru</option>
    <option value="24.79147, 120.99393">Dormitory Cheng</option>
    <option value="24.79102, 120.99391">Dormitory Yi</option>
    <option value="24.79055, 120.99372">Dormitory Hung</option>
    <option value="24.79012, 120.99301">Dormitory Shiue</option>
    <option value="24.79127, 120.99314">Dormitory Tsing</option>
    <option value="24.79164, 120.99290">Dormitory Hsin</option>
    <option value="24.79287, 120.99185">Dormitory Ya</option>
    <option value="24.79258, 120.99129">Dormitory Jing</option>
    <option value="24.79217, 120.99125">Dormitory Huei</option>
    <option value="24.79201, 120.99078">Dormitory Wen</option>
    <option value="24.797912, 120.990932">Guest House I</option>
    <option value="24.796913, 120.991228">Guest House II</option>
    <option value="24.79457, 120.99535">Cheng Kung Lake</option>
    <option value="24.79355, 120.99243">The channel</option>
    <option value="24.78853, 120.99125">Ji Dan Mian Area</option>
    <option value="24.78938, 120.98876">Dr. Mei Memorial Garden</option>
    <option value="24.79418, 120.99258">Kum Ming Lake</option>
    <option value="24.79279, 120.99019">Mei Pavilio</option>
    <option value="24.787981, 120.990554">Go Pavilion</option>
    <option value="24.79169, 120.99168">Campus Security Office</option>
    <option value="24.79111, 120.99085">Engineering and System Science Building</option>
    <option value="24.790759, 120.991360">Green Energy Research and Education Building</option>
    <option value="24.79079, 120.99133">Nuclear Science and Technology Development Center</option>
    <option value="24.78987, 120.98970">Humanities and Social Sciences Building</option>
    <option value="24.78990, 120.99026">Life Science Building I</option>
    <option value="24.78945, 120.98970">Life Science Building II</option>
    <option value="24.78928, 120.99140">Biomedical Engineering and Environmental Sciences Building</option> 
    <option value="24.789785, 120.992187">Nuclear Reactor Building</option>
    <option value="24.78932, 120.99216">Radioisotope Laboratory</option>
    <option value="24.78985, 120.99127">Biological Science and Technology Building</option>
    <option value="24.78876, 120.99168">Photonics Research Center-HOPE Laboratory</option>
    <option value="24.78877, 120.99207">Accelerator Building</option>
    <option value="24.78699, 120.98795">TSMC Building</option>
    <option value="24.786774, 120.988813">South gate</option>
"""

data_nanda = """
    <option value="24.794656, 120.965221">校門</option> 
    <option value="24.793199, 120.965696">側門</option> 
    <option value="24.793199, 120.965696">學生機車停車棚</option>
    <option value="24.793999, 120.964890">綜合教學大樓</option> 
    <option value="24.794256, 120.965177">圖書館</option>
    <option value="24.793846, 120.965698">竹師會館</option>
    <option value="24.793812, 120.965185">行政大樓</option>
    <option value="24.793264, 120.965174">教學大樓</option>
    <option value="24.793486, 120.964496">藝設系館</option>
    <option value="24.793277, 120.965837">中文系館</option>
    <option value="24.793467, 120.966250">應科系館</option>
    <option value="24.793647, 120.965858">環文系館</option>
    <option value="24.793199, 120.965696">推廣教育大樓</option>
    <option value="24.793851, 120.964582">迎曦軒</option>
    <option value="24.793671, 120.964577">崇善樓</option>
    <option value="24.793440, 120.963758">鳴鳳樓</option>
    <option value="24.793178, 120.963555">學生活動中心</option>
    <option value="24.792903, 120.963627">綜合體育館</option>
    <option value="24.793169, 120.964035">體育健康教學大樓</option>
    <option value="24.792609, 120.964003">學生第二活動中心</option>
    <option value="24.792609, 120.964003">餐廳</option>
    <option value="24.792346, 120.963971">樹德樓</option>
    <option value="24.792134, 120.963805">飲虹樓</option>
    <option value="24.792127, 120.963971">掬月齋</option>
    <option value="24.792348, 120.964215">音樂系館</option>
    <option value="24.793196, 120.965697">機車停車棚</option>
    <option value="24.792905, 120.965338">運動場</option>
    <option value="24.793182, 120.964030">傻瓜樹</option>
    <option value="24.793131, 120.965204">麵包樹</option>
    <option value="24.793213, 120.965682">築思橋</option>
"""

data_nanda_en = """
    <option value="24.794656, 120.965221">Main Entrance</option> 
    <option value="24.793199, 120.965696">Side Gate</option> 
    <option value="24.793199, 120.965696">Student Motorcycle Parking Shelter</option>
    <option value="24.793999, 120.964890">General Education Building</option> 
    <option value="24.794256, 120.965177">Library</option>
    <option value="24.793846, 120.965698">National Hsinchu University of Education History hall</option>
    <option value="24.793812, 120.965185">Administration Building</option>
    <option value="24.793264, 120.965174">Education Building</option>
    <option value="24.793486, 120.964496">Arts and Design Building</option>
    <option value="24.793277, 120.965837">Chinese Language and Literature Building</option>
    <option value="24.793467, 120.966250">Applied Science Building</option>
    <option value="24.793647, 120.965858">Environmental and Cultural Resources Building</option>
    <option value="24.793199, 120.965696">Continuing and Extension Education Building</option>
    <option value="24.793851, 120.964582">Ying-Shi Pavilion</option>
    <option value="24.793671, 120.964577">Chong-Shan Building</option>
    <option value="24.793440, 120.963758">Ming-Feng Building</option>
    <option value="24.793178, 120.963555">Center of Student Activities</option>
    <option value="24.792903, 120.963627">Sports Complex</option>
    <option value="24.793169, 120.964035">Physical and Health Education Building</option>
    <option value="24.792609, 120.964003">Second Center of Student Activities</option>
    <option value="24.792609, 120.964003">Dining Hall</option>
    <option value="24.792346, 120.963971">Shu-De Building</option>
    <option value="24.792134, 120.963805">Yin-Hong Building</option>
    <option value="24.792127, 120.963971">Ju-Yue House</option>
    <option value="24.792348, 120.964215">Music Building</option>
    <option value="24.793196, 120.965697">Motorcycle Parking Shelter</option>
    <option value="24.792905, 120.965338">Sports Field</option>
    <option value="24.793182, 120.964030">The tree of foolishness</option>
    <option value="24.793131, 120.965204">The tree of bread</option>
    <option value="24.793213, 120.965682">The bridge of memories</option>
"""


def map_data_to_json(data):
    # 把 data_main 和 data_nanda 的資料變成 對應資料名稱的 json
    # 資料格式
    # {
    #     "光復路校門": {
    #         "latitude": 120.997015,
    #         "longitude": 24.796538
    #     },
    data = data.split("\n")

    print(data)

    # 使用 regex 取得資料
    pattern = re.compile(r'<option value="(\d+\.\d+), (\d+\.\d+)">(.*?)</option>')

    map_data = {}

    # 將資料轉換成 json 格式
    for datan in data:
        try:
            matches = pattern.search(datan)
            latitude = matches.group(1)
            longitude = matches.group(2)
            key = matches.group(3)
            map_data[key] = {"latitude": latitude, "longitude": longitude}
        except Exception as e:
            print(f"errordata: {datan}, {e}")

    print(map_data)

    return map_data


if __name__ == "__main__":
    map_data = map_data_to_json(data_main_en)

    with open("map_main_official_en.json", "w", encoding="UTF-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=4)
