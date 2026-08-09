#!/usr/bin/env python3
"""新闻聚合 v5 公共模块(2026-08-08):多源聚合 → 聚类 → 优中选优 + 分类标签 + 多视角对照 + 演变追踪
v5 新增: 1) 分类标签(军事/政治/经济/气候/科技/社会)
         2) 中文源(Google News 中文 RSS,免费聚合人民网/新华网/观察者等)
         3) 多视角对照卡(焦点事件各家标题并排)
         4) 事件演变追踪(历史文件对比:持续/新增)
         5) 信源构成提示(官方通讯社 vs 独立媒体)
供 tg_bot.py /bbc 与 bbc_daily.py 共用。"""
import html
import json
import os
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

CN = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0"
HIST_FILE = "/root/.bbc_history.json"

# (源名, 视角, 集团, 官方?, 类型, url, 参数)
SOURCES = [
    ("BBC世界", "uk", "bbc", 0, "rss", "https://feeds.bbci.co.uk/news/rss.xml", None),
    ("BBC中东", "uk", "bbc", 0, "rss", "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml", None),
    ("BBC欧洲", "uk", "bbc", 0, "rss", "https://feeds.bbci.co.uk/news/world/europe/rss.xml", None),
    ("BBC美加", "uk", "bbc", 0, "rss", "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml", None),
    ("BBC亚太", "uk", "bbc", 0, "rss", "https://feeds.bbci.co.uk/news/world/asia/rss.xml", None),
    ("半岛台", "qa", "半岛台", 0, "rss", "https://www.aljazeera.com/xml/rss/all.xml", None),
    ("Asharq", "sa", "Asharq", 0, "rss", "https://english.aawsat.com/feed", None),
    ("AMR", "apac", "AMR", 0, "rss", "https://www.asianmilitaryreview.com/feed", None),
    ("TASS", "ru", "TASS", 1, "rss", "https://tass.com/rss/v2.xml", None),
    ("RT", "ru", "RT", 1, "rss", "https://www.rt.com/rss/news/", None),
    ("韩联社", "kr", "韩联社", 1, "rss", "https://en.yna.co.kr/RSS/news.xml", None),
    ("世界报", "fr", "世界报", 0, "rss", "https://www.lemonde.fr/en/rss/une.xml", None),
    ("印度教徒报", "in", "印度教徒报", 0, "rss", "https://www.thehindu.com/feeder/default.rss", None),
    ("晨报", "tr", "晨报", 0, "rss", "https://www.dailysabah.com/rss/home", None),
    ("国土报", "il", "国土报", 0, "rss", "https://www.haaretz.com/srv/haaretz-latest-headlines", None),
    ("黎明报", "pk", "黎明报", 0, "rss", "https://www.dawn.com/feeds/home", None),
    ("DW", "de", "DW", 0, "rdf", "https://rss.dw.com/rdf/rss-en-all", None),
    ("CGTN", "cn", "CGTN", 1, "curl_class", "https://www.cgtn.com/", "headline-item"),
    ("环球时报", "cn", "环球时报", 1, "curl_class", "https://www.globaltimes.cn/", "title"),
    ("NYT", "us", "NYT", 0, "curl_class", "https://www.nytimes.com/", "indicate-hover"),
    ("PressTV", "ir", "PressTV", 1, "curl_h", "http://www.presstv.ir/", "h1,h2,h3,h4"),
    ("海峡时报", "sg", "海峡时报", 0, "rss", "https://www.straitstimes.com/news/world/rss.xml", None),
    ("卫报", "uk", "卫报", 0, "rss", "https://www.theguardian.com/world/rss", None),
    ("中东眼", "me", "中东眼", 0, "rss", "https://www.middleeasteye.net/rss", None),
    ("MarketWatch", "us", "MarketWatch", 0, "rss", "https://feeds.content.dowjones.io/public/rss/mw_topstories", None),
    ("CNN", "us", "CNN", 0, "curl_class", "https://edition.cnn.com/world", "container__link"),
    ("韩国先驱报", "kr", "韩国先驱报", 0, "curl_class", "https://www.koreaherald.com/", "tit"),
    ("观察者网", "cn", "观察者网", 0, "curl_class", "https://www.guancha.cn/", "title"),
    ("CNA", "sg", "CNA", 0, "anysearch", "https://www.channelnewsasia.com/", None),
    ("曼谷邮报", "th", "曼谷邮报", 0, "anysearch", "https://www.bangkokpost.com/", None),
    ("ANSA", "it", "ANSA", 0, "anysearch", "https://www.ansa.it/english/news/news.shtml", None),
    ("联合早报", "sg", "联合早报", 0, "anysearch", "https://www.zaobao.com.sg/", None),
    ("彭博", "us", "彭博", 0, "rss", "https://feeds.bloomberg.com/markets/news.rss", None),
    ("华尔街日报", "us", "华尔街日报", 0, "rss", "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", None),
    ("CNBC", "us", "CNBC", 0, "rss", "https://www.cnbc.com/id/100003114/device/rss/rss.html", None),
]
CN_SOURCES = [
    ("中文视角", "cn", "中文媒体", 0, "rss", "https://news.google.com/rss?hl=zh-CN&gl=CN&ceid=CN:zh-Hans", None),
    ("人民网", "cn", "人民网", 1, "rss", "http://www.people.com.cn/rss/politics.xml", None),
    ("人民网", "cn", "人民网", 1, "rss", "http://www.people.com.cn/rss/world.xml", None),
    ("央视", "cn", "央视", 1, "jsonp", "https://news.cctv.com/2019/07/gaiban/cmsdatainterface/page/news_1.jsonp?cb=t", "data"),
    ("中新网", "cn", "中新网", 1, "rss", "https://www.chinanews.com.cn/rss/scroll-news.xml", None),
]

# 分类关键词
CATS = [
    ("🛡", ["war", "missile", "drone", "strike", "military", "army", "troops", "navy", "nuclear",
              "tank", "fighter", "defense", "weapon", "bomb", "aircraft", "marines", "invasion", "ceasefire",
              "airstrike", "arsenal", "militant", "houthi", "hezbollah", "rebel", "guerrilla", "occupation",
              "counteroffensive", "artillery", "shelling", "clash", "attack", "ambush", "siege", "raid",
              "combat", "casualties", "soldiers", "military"]),
    ("⚖️", ["president", "election", "vote", "parliament", "senate", "minister", "government", "diplomat",
               "sanctions", "treaty", "pact", "agreement", "talks", "summit", "lawmaker", "court", "trump",
               "putin", "zelensky", "chancellor", "referendum", "protest", "policy", "diplomatic", "gaza",
               "peace", "negotiations", "embassy", "ambassador", "candidate", "campaign", "ruling", "israel",
               "ukraine", "russia", "hamas", "party"]),
    ("💰", ["economy", "economic", "market", "stock", "trade", "tariff", "inflation", "jobs", "employment",
               "bank", "central", "oil", "price", "currency", "yen", "dollar", "won", "budget", "debt",
               "investment", "company", "business", "profit", "sales", "fiscal", "deficit", "billion", "million",
               "shares", "fed", "rates", "industry", "factory", "exports"]),
    ("🌍", ["climate", "weather", "typhoon", "storm", "flood", "drought", "heat", "earthquake", "wildfire",
              "temperature", "rain", "hurricane", "quake", "eruption", "heatwave", "landslide", "dolphin"]),
    ("🔬", ["ai", "tech", "technology", "chip", "satellite", "space", "rocket", "quantum", "robot",
              "software", "internet", "data", "nasa", "spacex", "google", "microsoft", "cyber",
              "semiconductor", "vaccine", "scientist", "researchers", "iphone"]),
]
SOFTX = ("award", "prize", "guess", "mystery", "festival", "exhibition", "movie", "album", "concert", "recipe",
         "tips", "interview", "profile", "review", "opinion", "bestseller", "fashion", "celebrity", "wedding")

STOP = set("a an the of to in on for and with by from at as is are was were be been has have had its it s t over under after before amid says say said report reports tells".split())

# 地方台/区域活动特征词(央广、疆超这类)
SOFT_LOCAL = ["央广", "疆超", "地方台", "县融", "融媒体", "文旅", "民俗节", "文化节",
              "旅游节", "美食节", "音乐节", "马拉松", "半马", "健步走", "广场",
              "社区活动", "街道办", "居委会"]

# 软新闻过滤(所有源统一标准,太甲钦定):
# 去娱乐八卦 / 去民间局部 / 去置顶 / 去评论观察无时效 / 多硬新闻
SOFT_CN = ["明星", "演员", "歌手", "爱豆", "偶像", "粉丝", "演唱会", "电影", "电视剧",
           "综艺", "内娱", "韩娱", "日娱", "绯闻", "恋情", "官宣", "离婚", "结婚",
           "出轨", "塌房", "漫展", "网红", "带货", "选秀", "票房", "番剧", "预告片",
           "乐队", "舞台", "圈粉", "唱法", "大结局", "汪峰", "沈腾", "翁虹", "戚薇",
           "玲花", "曾毅", "Mina", "萌宠", "宠物", "美食", "探店", "吃货", "打卡",
           "旅游", "景区", "民宿", "百花奖", "开幕式", "独舞", "歌王", "影帝", "影后",
           "颁奖礼", "真人秀", "直播", "主播", "总决赛", "欧阳娜娜", "窦靖童",
           "养生", "健康", "误区", "护肤", "减肥", "食谱", "助眠", "解暑", "小妙招",
           "小技巧", "科普", "辟谣", "温馨提示", "广告", "优惠", "秒杀", "抽奖",
           "福利", "免费领", "新品上市", "攻略", "合集", "必看", "惊呆", "炸锅",
           "泪目", "上热搜", "走红", "网友", "围观", "热议", "刷屏", "离谱", "无语",
           "震惊", "心疼", "破防", "翻车", "道歉", "哭崩", "降维打击",
           "立秋", "节气", "立春", "清明", "端午", "中秋", "元宵", "腊八", "冬至",
           "夏至", "习俗", "民俗", "老话", "民间", "上四休三", "降薪", "工资", "薪资",
           "加班", "上班", "职场", "求职", "招聘", "考研", "考公", "考编", "高考",
           "考生", "志愿", "录取", "家长", "孩子", "学生", "作业", "房贷", "房价",
           "房租", "彩礼", "相亲", "催婚", "夫妻", "婆媳", "宝妈", "宝宝", "二胎",
           "三胎", "养老", "退休", "社保", "医保", "露营", "大妈", "大爷", "司机",
           "外卖", "快递", "超市", "菜价", "水果", "奶茶", "咖啡", "火锅", "烧烤",
           "夜市", "空调", "西瓜", "冰淇淋", "中奖", "彩票", "摆摊", "钓鱼", "广场舞",
           "失联", "纠纷", "骗局", "差评", "倒闭", "偶遇", "合影", "拼豆", "玩具",
           "盲盒", "手办", "开店", "门店", "商家", "顾客", "投诉", "索赔", "赔偿",
           "起诉", "讨薪", "讨债", "物业", "邻居", "室友", "同事", "家常菜", "菜谱",
           "厨艺", "出殡", "遗产", "继承", "补偿", "稻谷", "抢收", "民警", "消防员",
           "交警", "拾金不昧", "暖新闻", "感动", "凡人善举", "徒手", "极限", "净利润",
           "财报", "营收", "业绩", "回购", "减持", "市值", "个股", "拿走手机", "盗窃",
           "偷手机", "顺手牵羊", "短视频平台", "现象级", "全网模仿", "汉服", "变装",
           "电竞", "英雄联盟", "王者荣耀", "战队", "翻盘", "对决", "夺冠", "比赛",
           "职业联赛", "选手", "教练", "观察", "评论", "述评", "时评", "社评", "纪实",
           "专访", "对话", "故事", "特写", "盘点", "综述", "解读", "展望", "系列报道",
           "微视频", "海报", "图解", "致敬", "手记", "侧记", "沉浸式", "体验", "出圈",
           "暖心", "感人", "励志", "烟火气", "小城", "县城", "非遗", "文艺", "演出",
           "展览", "书法", "戏曲", "手工艺", "艺术节", "博览会", "论坛", "观影", "公益",
           "乡亲", "公会", "潮州", "发出邀约", "昂西", "动漫", "IP齐聚", "参赛名单",
           "体育队", "体操队", "名单出炉", "国风", "疆超联赛", "有线电视平台",
           "座机", "梁文锋", "只想用", "节目", "栏目", "上线", "播出", "开播",
           "纪录片", "宣传片", "预热", "发布会", "路演", "投资人", "融资",
           "创始人", "CEO", "老板", "富豪", "身价", "首富", "明星企业家",
           "访谈录", "面对面", "独家对话", "自述", "心得", "感悟", "分享",
           # 党媒专题栏目(无时效/宣传性)
           "学习卡", "镜观", "天天学习", "中南海月刊", "习语", "美丽中国",
           "足迹", "总书记的人民情怀", "文脉华章", "大道行天下", "铸魂强党",
           "以心相交", "引经据典", "学习新语", "温暖的回响", "第一观察",
           "数说", "一图读懂", "图解", "海报", "微视频",
           # 央视民生琐事/风景/健身软文
           "洞洞鞋", "翡翠湖", "晶莹剔透", "全民健身日", "健身日", "健身“热”",
           "减重", "暴瘦", "火把节", "民宿", "文旅", "打卡", "湿地公园",
           "家门口", "丰富多彩", "多措并举", "全力保障", "保驾护航",
           "民心工程", "办实事", "暖心事"]
SOFT_EN = ["celebrity", "actor", "actress", "singer", "movie", "film", "album", "concert", "festival",
           "fashion", "red carpet", "award show", "netflix", "spotify", "tiktok", "influencer",
           "recipe", "foodie", "restaurant", "travel", "vacation", "holiday", "tourist spot",
           "pet", "puppy", "kitten", "gaming", "esports", "video game", "streamer",
           "interview", "opinion", "editorial", "op-ed", "column", "review", "guide", "tips",
           "how to", "why you should", "best places", "top 10", "listicle", "quiz", "horoscope",
           "watch", "video shows", "photos", "in pictures", "in photos", "gallery", "craft",
           "artisan", "heritage", "tradition", "culture", "musician", "painter", "sculptor",
           "wedding", "divorce", "baby born", "pregnancy", "makeup", "skincare", "workout",
           "yoga", "recipe", "diy", "coupon", "discount", "sale", "giveaway", "sponsored"]

def is_soft_news(title):
    tl = title.lower()
    if any(w in tl for w in SOFT_EN):
        return True
    if re.search(r"[\u4e00-\u9fff]", title):
        for w in SOFT_CN + SOFT_LOCAL:
            if w in title:
                return True
    return False


ALIAS = [
    (("thai", "school", "shoot"), "thai school shooting"),
    (("thai", "student", "open", "fire"), "thai school shooting"),
    (("thai", "teen", "rampage"), "thai school shooting"),
    (("thai", "teacher", "killed"), "thai school shooting"),
    (("trump", "ballroom"), "trump ballroom project"),
    (("white", "house", "ballroom"), "trump ballroom project"),
    (("trump", "birthright"), "trump birthright citizenship"),
    (("birthright", "citizenship"), "trump birthright citizenship"),
    (("saudi", "pakistan", "turk"), "saudi pakistan turkiye pact"),
    (("saudi", "turk", "pakistan"), "saudi pakistan turkiye pact"),
    (("defence", "pact", "mecca"), "saudi pakistan turkiye pact"),
    (("defense", "pact", "makkah"), "saudi pakistan turkiye pact"),
    (("hormuz", "deal"), "hormuz deal"),
    (("hormuz", "agreement"), "hormuz deal"),
    (("strait", "hormuz"), "hormuz deal"),
    (("ceuta", "italy"), "ceuta italy border"),
    (("border", "controls", "italy"), "ceuta italy border"),
    (("german", "airport", "drone"), "german airport drone bomb"),
    (("airport", "drone", "bomb"), "german airport drone bomb"),
    (("venezuela", "earthquake"), "venezuela earthquake"),
    (("earthquake", "death", "toll"), "venezuela earthquake"),
    (("israel", "lebanon", "soldiers"), "israel lebanon strike"),
    (("lebanon", "israel", "troops", "verify"), "lebanon israel troop list"),
    (("hezbollah", "disarmament"), "lebanon israel troop list"),
    (("us", "jobs"), "us jobs report"),
    (("jobs", "july"), "us jobs report"),
    (("trump", "iran", "strike", "cancel"), "trump cancels iran strike"),
    (("trump", "cancels", "iran"), "trump cancels iran strike"),
    (("houthi", "saudi", "forces"), "houthi yemen attack"),
    (("houthi", "yemen", "attack"), "houthi yemen attack"),
]


def norm_title(t):
    tl = t.lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff ]", " ", tl)
    toks = [w for w in s.split() if w and w not in STOP]
    for keys, alias in ALIAS:
        if all(any(w.startswith(k) or k.startswith(w) for w in toks if len(w) >= 4) for k in keys):
            return alias
    return " ".join(toks[:6])


def title_overlap(a, b):
    ta = set(a.split()); tb = set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def cat_of(t):
    tl = t.lower()
    toks = set(re.findall(r"[a-z0-9]+", tl))
    for label, words in CATS:
        if any(w in toks for w in words):
            return label
    return "🎭"


def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return ET.fromstring(urllib.request.urlopen(req, timeout=15).read())


def parse_dt(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    return None


AS_ENDPOINT = "https://api.anysearch.com/mcp"
AS_KEY_FILE = "/root/.anysearch_key"


def fetch_anysearch(url):
    """AnySearch extract:穿透付费墙/cookie 墙抓无 RSS 站首页头条。
    解析 markdown 里的 '### [标题](链接)' + 日期行;过滤短视频/广告/播客区块。"""
    try:
        key = open(AS_KEY_FILE).read().strip()
    except Exception:
        return []
    if not key:
        return []
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
               "params": {"name": "extract", "arguments": {"url": url}}}
    try:
        req = urllib.request.Request(
            AS_ENDPOINT, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
            method="POST")
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        data = json.loads(raw)
    except Exception as e:
        print("  anysearch 请求失败: " + str(e))
        return []
    result = data.get("result", {})
    text = ""
    if isinstance(result, dict) and "content" in result:
        c = result["content"]
        if isinstance(c, list):
            for it in c:
                if isinstance(it, dict):
                    text += it.get("text", "") or ""
        else:
            text = str(c)
    if not text:
        return []
    base = url.rstrip("/")
    out = []
    cur_date = ""
    skip = ("/shorts/", "/watch/", "/listen/", "/podcast", "/advertorial/", "/brand-studio",
            "/games", "/visual-stories", "/newsletters", "/gallery", "/photogallery",
            "javascript:", "/live", "/weather", "/tag/", "/topic/")
    for line in text.splitlines():
        m = re.match(r"^#{2,4} \[([^\]]+)\]\(([^)]+)\)", line.strip())
        if m:
            t = html.unescape(m.group(1)).strip()
            href = m.group(2).strip()
            if href.startswith("//"):
                href = "https:" + href
            elif not href.startswith("http"):
                href = base + "/" + href.lstrip("/")
            if any(s in href for s in skip):
                continue
            if 8 <= len(t) <= 130:
                out.append((t, "", cur_date, href))
        else:
            # 裸链接标题(联合早报): 整行 [标题](含story的路径)
            m2 = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", line.strip())
            if m2 and "story" in m2.group(2):
                t = html.unescape(m2.group(1)).strip()
                href = m2.group(2).strip()
                # 反向链接格式 [url](标题): 文本是 URL 的丢弃
                if t.startswith("/") or t.startswith("http"):
                    t = ""
                if not href.startswith("http"):
                    href = base + "/" + href.lstrip("/")
                if t and any(s in href for s in skip):
                    continue
                if t and 8 <= len(t) <= 130:
                    out.append((t, "", cur_date, href))
            else:
                dm = re.match(r"^\s*(\d{1,2} \w+ \d{4}|\d{1,2}/\d{1,2}/\d{4})", line)
                if dm:
                    s = dm.group(1)
                    try:
                        dt = None
                        for fmt in ("%d %B %Y", "%d %b %Y", "%m/%d/%Y"):
                            try:
                                dt = datetime.strptime(s, fmt)
                                break
                            except Exception:
                                continue
                        if dt is not None:
                            cur_date = dt.replace(tzinfo=timezone.utc).strftime("%a, %d %b %Y 00:00:00 GMT")
                    except Exception:
                        cur_date = ""
    # 去重保序
    seen, dedup = set(), []
    for t, d, p, u in out:
        if t not in seen:
            seen.add(t)
            dedup.append((t, d, p, u))
    return dedup


def fetch_source(src):
    name, view, group, official, typ, url, arg = src
    out = []
    try:
        if typ == "anysearch":
            out = fetch_anysearch(url)
        elif typ == "rss":
            try:
                root = fetch_rss(url)
            except Exception:
                # 容错:截掉尾随垃圾再解析;非 XML 直接放弃该源
                raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15).read().decode("utf-8", "replace")
                cut = raw.find("</rss>")
                if cut > 0:
                    raw = raw[:cut + 6]
                try:
                    root = ET.fromstring(raw)
                except Exception:
                    return out
            for it in root.iter("item"):
                t = it.findtext("title") or ""
                d = it.findtext("description") or ""
                p = it.findtext("pubDate") or ""
                u = it.findtext("link") or ""
                out.append((t, d, p, u))
        elif typ == "jsonp":
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "replace")
            raw = raw[raw.find("(") + 1:raw.rfind(")")]
            d = json.loads(raw)
            for it in (d.get("data", {}).get("list", []) or []):
                t = it.get("title", "") or ""
                b = it.get("brief", "") or ""
                dt = it.get("focus_date", "") or ""
                u = it.get("url", "") or ""
                if t:
                    out.append((t, b, dt, u))
        elif typ == "rdf":
            root = fetch_rss(url)
            cur = {}
            for el in root.iter():
                tag = el.tag.split("}")[-1]
                if tag == "item":
                    if cur and cur.get("t"): out.append((cur["t"], cur.get("d", ""), cur.get("p", ""), cur.get("u", "")))
                    cur = {}
                elif tag == "title": cur["t"] = el.text or ""
                elif tag == "description": cur["d"] = el.text or ""
                elif tag == "date": cur["p"] = el.text or ""
                elif tag == "link": cur["u"] = el.text or ""
            if cur and cur.get("t"): out.append((cur["t"], cur.get("d", ""), cur.get("p", ""), cur.get("u", "")))
        else:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read().decode("utf-8", "replace")
            if typ == "curl_class":
                pat = re.compile(r'class="[^"]*' + re.escape(arg) + r'[^"]*"[^>]*>([^<]{15,90})<')
                for m in pat.finditer(raw):
                    t = html.unescape(m.group(1)).strip()
                    if t: out.append((t, "", "", ""))
            else:
                for tag in arg.split(","):
                    pat = re.compile(r"<" + tag + r"[^>]*>(.*?)</" + tag + r">", re.S)
                    for m in pat.finditer(raw):
                        t = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
                        if 15 <= len(t) <= 90:
                            out.append((t, "", "", ""))
    except Exception as e: print("  源失败 " + name + ": " + str(e))
    return out


def is_no_event(t):
    """无事件性标题: 解释文/视频文/列表文,没头没尾没时效"""
    tl = t.strip().lower()
    if re.match(r"^(what is|what are|why (is|are|do|does|did|can)|how (to|do|does|is|are)|which is|who is|watch|video|photos|in pictures|in photos|explained|explainer|faq|top \d+|best \d+|quiz|gallery)", tl):
        return True
    if re.search(r"\b(explainer|explained|what to know|everything you need|you need to know|here's what|here is what)\b", tl):
        return True
    return False


def collect_all():
    rows = []
    for src in SOURCES:
        for t, d, p, u in fetch_source(src):
            if is_soft_news(t) or is_no_event(t):
                continue
            dt = parse_dt(p)
            nkey = norm_title(t)
            if len(nkey) < 4:
                continue
            rows.append((t, d, dt, src[0], src[1], src[2], src[3], nkey, u))
    return rows


def collect_cn():
    """中文源:返回 [(title, dt, src, official, url), ...] 独立展示(已过滤软新闻)
    标题清洗: 去掉 " - 来源" 尾巴, 去掉来源小括号后缀"""
    out = []
    for src in CN_SOURCES:
        try:
            for t, d, p, u in fetch_source(src):
                if is_soft_news(t):
                    continue
                dt = parse_dt(p)
                t = re.sub(r"\s*-\s*(央视|中新网|人民网|新华网|新京报|观察者网|中青网|河北新闻|新体育网|求是|中国网|同花顺|eastmoney|中证网|21财经)[^|]*$", "", t)
                t = t.strip(" |")
                out.append((t, dt, src[0], src[3], u))
        except Exception as e: print("  中文源失败 " + src[0] + ": " + str(e))
    return out


def fetch_baidu_hot():
    """百度热搜实时榜(跳过置顶,过滤软新闻),返回 [(word, desc), ...]"""
    out = []
    try:
        req = urllib.request.Request("https://top.baidu.com/board?tab=realtime",
                                     headers={"User-Agent": UA})
        data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        m = re.search(r"<!--s-data:(.*?)-->", data, re.S)
        if not m:
            return out
        payload = json.loads(m.group(1))
        for c in payload["data"]["cards"][0]["content"]:
            if str(c.get("isTop", "")).lower() == "true":
                continue
            w = c.get("word", "")
            d = c.get("desc", "")
            if is_soft_news(w):
                continue
            if not w:
                continue
            out.append((w, d))
    except Exception as e: print("  百度热搜失败: " + str(e))
    return out


def cluster(rows):
    groups = []
    used = [False] * len(rows)
    for i in range(len(rows)):
        if used[i]:
            continue
        cl = [i]
        used[i] = True
        for j in range(i + 1, len(rows)):
            if used[j]:
                continue
            if rows[i][7] == rows[j][7] or title_overlap(rows[i][7], rows[j][7]) > 0.45:
                cl.append(j)
                used[j] = True
        groups.append(cl)
    groups.sort(key=len, reverse=True)
    return groups


HARD = set("war attack missile drone strike nuclear sanctions army military troops killed death deadly earthquake typhoon storm flood fire blast explosion hostage invasion border conflict shooting".split())


def window_hours():
    """动态时间窗:早晨跨昨天(48h),越晚越只关心当天(24h)"""
    h = datetime.now(CN).hour
    if h < 8: return 48
    if h < 16: return 36
    return 24


def group_lines(groups, rows, limit=34):
    now = datetime.now(timezone.utc)
    win = window_hours()
    picks = []
    for cl in groups:
        members = [rows[i] for i in cl]
        best = max(members, key=lambda m: m[2] or datetime.min.replace(tzinfo=timezone.utc))
        dt = best[2]
        groupset = sorted(set(m[5] for m in members))
        views = set(m[4] for m in members)
        officials = sum(1 for m in members if m[6])
        t = members[0][0]
        # 摘要:取簇内最完整的 description,且与标题主题一致(防错位)
        desc = ""
        url = ""
        for m in members:
            if m[8]:
                url = m[8]
                break
        tn = set(norm_title(t).split())
        for m in members:
            d = re.sub(r"<[^>]+>", " ", m[1] or "")
            d = " ".join(d.split())
            if len(d) < 30:
                continue
            # 摘要需含标题核心词(取前2个非停用词)或同簇即可信
            if len(d) > len(desc):
                desc = d
        desc = desc[:200]
        age = (now - dt).total_seconds() if dt else 1e9
        fresh = age < win * 3600
        hard = 1 if any(w in t.lower() for w in HARD) else 0
        picks.append((len(groupset), len(views), hard, dt, t, groupset, officials, fresh, members, desc, url))
    def sortkey(p):
        g, hard, dt = p[0], p[2], p[3]
        age = ((now - dt).total_seconds()) if dt else 1e9
        fresh = max(0.0, 1.0 - age / (win * 3600))
        return (g + 0.3 * fresh, hard, dt or datetime.min.replace(tzinfo=timezone.utc))
    picks.sort(key=sortkey, reverse=True)
    picks = [p for p in picks if p[7] or p[2]]
    picks.sort(key=sortkey, reverse=True)
    multi = [p for p in picks if p[0] >= 2][:limit]
    solo = [p for p in picks if p[0] == 1 and p[2] and not any(w in p[4].lower() for w in SOFTX)][:max(5, limit // 2)]
    return (multi + solo)[:limit * 2], win


def load_hist():
    try:
        return json.load(open(HIST_FILE))
    except Exception:
        return {}


def save_hist(hist):
    try:
        json.dump(hist, open(HIST_FILE, "w"))
    except Exception:
        pass


def _google_batch(texts):
    """Google 免费端点批量翻译,返回译文列表;失败抛异常"""
    u = ("https://translate.googleapis.com/translate_a/single"
         "?client=gtx&sl=en&tl=zh-CN&dt=t&q=" + urllib.parse.quote("\n".join(texts)))
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read())
    joined = "".join(seg[0] for seg in data[0])
    parts = joined.split("\n")
    while parts and parts[-1] == "" and len(parts) > len(texts):
        parts.pop()
    if len(parts) != len(texts):
        raise RuntimeError("line mismatch")
    return parts


def _google_single(t):
    """单条翻译"""
    u = ("https://translate.googleapis.com/translate_a/single"
         "?client=gtx&sl=en&tl=zh-CN&dt=t&q=" + urllib.parse.quote(t))
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return "".join(seg[0] for seg in data[0])


def _mymemory_single(t):
    """MyMemory 免费端点(第二兜底)"""
    u = "https://api.mymemory.translated.net/get?q=" + urllib.parse.quote(t) + "&langpair=en|zh-CN"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return d.get("responseData", {}).get("translatedText", "") or t


def gtrans(texts):
    """纯免费翻译: Google批量 → 二分重试 → 单条 → MyMemory → 原文"""
    if not texts:
        return []
    out = [None] * len(texts)
    pending = list(range(len(texts)))

    def resolve(idx_list):
        batch = [texts[i] for i in idx_list]
        try:
            res = _google_batch(batch)
            for i, r in zip(idx_list, res):
                out[i] = r
            return []
        except Exception:
            if len(idx_list) == 1:
                return idx_list  # 单条也失败,交给下一级
            mid = len(idx_list) // 2
            return resolve(idx_list[:mid]) + resolve(idx_list[mid:])

    pending = resolve(pending)
    # 二级: 单条 Google
    still = []
    for i in pending:
        try:
            out[i] = _google_single(texts[i])
        except Exception:
            still.append(i)
    # 三级: MyMemory
    for i in still:
        try:
            out[i] = _mymemory_single(texts[i])
        except Exception:
            out[i] = texts[i]
    return out


def fetch_market():
    """💹 隔夜市场: 美股指数(道指/纳指) + 美元指数 + 黄金 + 原油"""
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            "https://qt.gtimg.cn/q=usDJI,usIXIC,hf_GC,hf_CL",
            headers={"User-Agent": UA}), timeout=10).read().decode("gbk", "replace")
        parts = {}
        for line in raw.strip().split(";"):
            if "=" not in line:
                continue
            key = line.split("=")[0].replace("v_", "").strip()
            val = line.split("=", 1)[1].strip().strip('"')
            if not val:
                continue
            f = val.split("~")
            if key.startswith("us") and len(f) > 33:
                parts[key] = (f[1], f[3], f[31], f[32])
            else:
                g = val.split(",")
                if len(g) > 3 and g[0]:
                    pct = 0.0
                    try:
                        base = float(g[3])
                        if base:
                            pct = round(float(g[1]) / base * 100, 2)
                    except Exception:
                        pass
                    parts[key] = (g[-1] if len(g) > 13 else key, g[0], g[1], str(pct))
        # 美元指数(新浪 DINIW): 现价=字段1, 昨收=字段3
        try:
            req = urllib.request.Request("https://hq.sinajs.cn/list=DINIW",
                                         headers={"User-Agent": UA, "Referer": "https://finance.sina.com.cn"})
            sraw = urllib.request.urlopen(req, timeout=10).read().decode("gbk", "replace")
            sv = sraw.split('"')[1].split(",")
            if len(sv) > 3 and sv[0]:
                px = "%.2f" % float(sv[1])
                base = float(sv[3])
                cur = float(sv[1])
                chg = round(cur - base, 2)
                pct = round(chg / base * 100, 2) if base else 0.0
                parts["DINIW"] = ("美元指数", px, str(chg), str(pct))
        except Exception as e:
            print("  美元指数失败: " + str(e))
        labels = {"usDJI": ("道指", "https://gu.qq.com/usDJI"),
                  "usIXIC": ("纳指", "https://gu.qq.com/usIXIC"),
                  "hf_GC": ("黄金", "https://quote.eastmoney.com/globalfuture/GC00Y.html"),
                  "hf_CL": ("原油", "https://quote.eastmoney.com/globalfuture/CL00Y.html"),
                  "DINIW": ("美元指数", "https://finance.sina.com.cn/money/forex/hq/DINIW.shtml")}
        seg = []
        for k, (lab, url) in labels.items():
            if k in parts:
                nm, px, chg, pct = parts[k]
                try:
                    arrow = "▲" if float(chg or 0) >= 0 else "▼"
                    seg.append('<a href="' + url + '">' + lab + " " + str(px) + " " + arrow + str(pct) + "%</a>")
                except Exception:
                    pass
        return "💹 " + " | ".join(seg) if seg else ""
    except Exception as e:
        print("  行情失败: " + str(e))
        return ""


def build_digest(limit=34, with_cn=True, with_card=True, cat=None, view=None, page=0):
    print("收集源…")
    rows = collect_all()
    print("共 " + str(len(rows)) + " 条原始")
    groups = cluster(rows)
    print("聚类 " + str(len(groups)) + " 簇")
    # 过滤场景(cat/view/page)需要更大的池子
    need = limit if not (cat or view or page) else max(limit * 3, 120)
    picks, win = group_lines(groups, rows, need)

    # /bbc 子命令: 分类/视角过滤 + 翻页
    CAT_MAP = {"军事": "🛡", "政治": "⚖️", "经济": "💰", "气候": "🌍", "科技": "🔬", "社会": "🎭"}
    if view:
        picks = [p for p in picks if any(view in m[4] for m in p[8])]
    if cat:
        cat_e = CAT_MAP.get(cat, cat)
        picks = [p for p in picks if cat_e in cat_of(p[4])]
    if page > 0:
        start = page * limit
        picks = picks[start:start + limit]
    else:
        picks = picks[:limit]

    # 历史对比:前天已报的焦点 → 持续跟进,不占主榜(按日期存,当天多次生成不去重)
    hist = load_hist()
    today = datetime.now(CN).strftime("%Y-%m-%d")
    prev_date = (datetime.now(CN) - timedelta(days=2)).strftime("%Y-%m-%d")  # 前天
    prev = hist.get("prev_by_date", {}).get(prev_date, [])
    keys_now = set(norm_title(p[4]) for p in picks)
    keys_prev = set(prev)
    new_keys = keys_now - keys_prev
    cont_keys = keys_now & keys_prev

    # 翻译主列表标题(按 p[4] 建映射,防错位)
    titles = [p[4] for p in picks]
    try:
        trans = gtrans(titles)
    except Exception:
        trans = titles
    trans_map = {t: (tr if tr else t) for t, tr in zip(titles, trans)}

    nsrc = len(SOURCES) + len(CN_SOURCES)
    lines = ["📰 全球早报 · " + datetime.now(CN).strftime("%m-%d %H:%M"),
             "(" + str(nsrc) + " 源 · 收 " + str(len(rows)) + " 条 · 窗口 " + str(win) + "h)"]
    mkt = fetch_market()
    if mkt:
        lines.insert(1, mkt)
    # 焦点兜底:新焦点少于 5 时,拉最新 cont 焦点回主榜(可能今天有新进展)
    if len(new_keys) < 5:
        for p in picks:
            if norm_title(p[4]) in cont_keys and p[0] >= 3 and norm_title(p[4]) not in new_keys:
                new_keys.add(norm_title(p[4]))
    buckets = {"🔥 今日焦点": [p for p in picks if p[0] >= 4 and norm_title(p[4]) in new_keys],
               "⭐ 多方关注": [p for p in picks if p[0] == 3 and norm_title(p[4]) in new_keys],
               "👀 双源关注": [p for p in picks if p[0] == 2 and norm_title(p[4]) in new_keys],
               "📡 独家观察": [p for p in picks if p[0] == 1 and norm_title(p[4]) in new_keys]}
    ti = 0
    idx = 1
    for label, bucket in buckets.items():
        if not bucket:
            continue
        lines.append("")
        lines.append(label + " (" + str(len(bucket)) + "):")
        for p in bucket:
            t = trans_map.get(p[4], p[4])
            t_esc = html.escape(t)
            nm = len(set(m[3] for m in p[8]))
            if p[10]:
                t_html = '<a href="' + html.escape(p[10], quote=True) + '"><b>' + t_esc + "</b></a>"
            else:
                t_html = "<b>" + t_esc + "</b>"
            lines.append("  " + str(idx) + ". " + cat_of(p[4]) + " " + t_html + " (" + str(nm) + "家)")
            # 摘要(焦点区全部 + 多方区前5)
            if p[9] and (label in ("🔥 今日焦点", "⭐ 多方关注")):
                try:
                    sm = gtrans([p[9]])[0]
                except Exception:
                    sm = p[9]
                sm = sm.replace("<", "&lt;").replace(">", "&gt;")
                lines.append("     📌 " + sm[:110])
            idx += 1
            if with_card and label == "🔥 今日焦点" and bucket.index(p) < 3:
                card = view_card(p[8], p[4])
                if card:
                    card_titles = [ln.split("] ", 1)[1] for ln in card if "] " in ln]
                    try:
                        card_trans = gtrans(card_titles)
                    except Exception:
                        card_trans = card_titles
                    lines.append("     ┄ 视角 ┄")
                    for ci, ln in enumerate(card):
                        if "] " in ln and ci < len(card_trans):
                            ln = ln.split("] ", 1)[0] + "] " + card_trans[ci]
                        lines.append("     · " + ln)

    # 持续跟进(昨天已报,一行带过)
    cont_picks = [p for p in picks if norm_title(p[4]) in cont_keys][:4]
    if cont_picks:
        lines.append("")
        lines.append("📈 持续跟进:")
        for p in cont_picks:
            t = trans_map.get(p[4], p[4])
            t_esc = html.escape(t)
            if p[10]:
                lines.append('  · <a href="' + html.escape(p[10], quote=True) + '"><b>' + t_esc[:60] + "</b></a>")
            else:
                lines.append("  · <b>" + t_esc[:60] + "</b>")

    # 中文视角
    if with_cn:
        cn_items = collect_cn()
        seen = set()
        dedup = []
        for t, dt, srcn, off, u in cn_items:
            k = t[:40]
            if k in seen:
                continue
            seen.add(k)
            dedup.append((t, dt, srcn, off, u))
        dedup.sort(key=lambda x: x[1] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        # 多源中文优先(Google News 聚合:美国之音/东方财富/华尔街见闻等,中文看国际)
        # 官方源(央视/中新网/人民网)硬新闻保底置顶,其余官方源垫底
        official = [x for x in dedup if x[3] and x[2] in ("央视", "中新网", "人民网")]
        rest = [x for x in dedup if x not in official]
        hard_off = [x for x in official if any(w in x[0] for w in ("地震", "台风", "洪水", "防汛", "暴雨", "遇难", "死亡", "伤亡", "军演", "南海", "发射", "爆炸", "火灾", "事故"))]
        other_off = [x for x in official if x not in hard_off]
        ranked = hard_off[:3] + rest + other_off
        # 百度热搜(国内硬新闻优先,置顶)
        hot = fetch_baidu_hot()
        hot_show = []
        if hot:
            for w, d in hot:
                if len(hot_show) >= 5:
                    break
                if any(w in t for t, dt, srcn, off, u in ranked[:10]):
                    continue
                hot_show.append((w, d))
        lines.append("")
        lines.append("🔥 国内热搜(百度):")
        for i, (w, d) in enumerate(hot_show, 1):
            u = "https://www.baidu.com/s?wd=" + urllib.parse.quote(w)
            lines.append('  ' + str(i) + '. <a href="' + u + '"><b>' + html.escape(w)[:60] + "</b></a>")
        lines.append("")
        lines.append("🇨🇳 中文视角(硬新闻):")
        shown = 0
        topic_count = {}
        for t, dt, srcn, off, u in ranked:
            if shown >= 10:
                break
            # 同主题去重: 台风/地震/洪水/洪峰 每主题最多2条
            topic = None
            tl = t
            if "台风" in tl or "白海豚" in tl: topic = "typhoon"
            elif "地震" in tl: topic = "quake"
            elif "洪水" in tl or "洪峰" in tl or "防汛" in tl: topic = "flood"
            if topic:
                topic_count[topic] = topic_count.get(topic, 0) + 1
                if topic_count[topic] > 2:
                    continue
            tag = ("【" + srcn + "】") if srcn in ("央视", "中新网", "人民网") else ""
            t_esc = html.escape(t)[:80]
            if u:
                lines.append('  ' + str(shown + 1) + ". " + tag + '<a href="' + html.escape(u, quote=True) + '"><b>' + t_esc + "</b></a>")
            else:
                lines.append("  " + str(shown + 1) + ". " + tag + "<b>" + t_esc + "</b>")
            shown += 1

    # 存历史(按日期,当天覆盖;只留最近 6 天防膨胀)
    hist.setdefault("prev_by_date", {})[today] = list(keys_now)
    keep = sorted(hist["prev_by_date"].keys())[-6:]
    for k in list(hist["prev_by_date"].keys()):
        if k not in keep:
            del hist["prev_by_date"][k]
    save_hist(hist)
    return "\n".join(lines)


def view_card(members, title):
    """多视角对照:按集团取各家标题(英文原文),返回行列表"""
    by_group = {}
    for m in members:
        g = m[5]  # group
        if g not in by_group or (m[2] or datetime.min.replace(tzinfo=timezone.utc)) > (by_group[g][2] or datetime.min.replace(tzinfo=timezone.utc)):
            by_group[g] = m
    out = []
    for g, m in list(by_group.items())[:5]:
        shown = "BBC" if g == "bbc" else g
        out.append("[" + shown + "] " + m[0][:90])
    return out


if __name__ == "__main__":
    print(build_digest())
