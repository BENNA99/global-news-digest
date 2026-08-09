# 📰 Global News Digest 全球早报

> 覆盖全球 **40+ 主流媒体** 的多视角新闻聚合器,一次读懂世界。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![No LLM required](https://img.shields.io/badge/No-LLM-required-orange.svg)](#)

同一件事,不同国家的媒体怎么说?**对照着看,才是全貌。**

`bbc_news.py` 每天从全球 40+ 主流媒体抓取新闻,自动聚类去重、按报道热度排序,生成一份**多视角对照**的全球早报——支持 Telegram 推送、网页部署、分类/视角筛选。

---

## ✨ 特性

- 🌍 **40+ 全球主流媒体源**:BBC、NYT、彭博、华尔街日报、CNBC、半岛台、TASS、RT、NHK、韩联社、法新社、经济学人……覆盖欧美亚非拉 20+ 视角
- 🧠 **智能聚合**:标题聚类(相似度 0.45)、报道数加权排序、硬新闻优先、时间衰减
- 🕵️ **多视角对照卡**:同一焦点事件,并排展示各家媒体标题,一眼看清立场差异
- 🚦 **四档分层**:🔥 今日焦点 / ⭐ 多方关注 / 👀 双源关注 / 📡 独家观察
- 🆕 **事件演变追踪**:前天已报 → "持续跟进"档,新进展不淹没旧闻
- 📌 **AI 免费翻译**:Google 免费端点批量翻译标题+摘要(中文阅读零门槛)
- 💹 **隔夜市场行情**:道指/纳指/黄金/原油/美元指数,红涨绿跌实时显示
- 🔗 **标题即链接**:点标题直达原文,零跳转损耗
- 🗂 **中文视角**:央视/中新/人民 + Google News 多源(美国之音/东方财富/财联社等),"中文看国际"
- 🤖 **Telegram 子命令**:`/bbc` `/bbc 经济` `/bbc 军事` `/bbc th` `/bbc 2`……分类/视角/翻页随便玩
- 🌐 **网页部署**:自动生成当日 HTML + 历史归档,挂主页即用

---

## 📰 覆盖媒体(40+ 源)

| 视角 | 媒体 |
|---|---|
| 🇬🇧 英国 | BBC(主+5 区域)、卫报、经济学人(立场标本)、金融时报(索引) |
| 🇺🇸 美国 | NYT、CNN、彭博、华尔街日报、CNBC、福布斯、财富、MarketWatch |
| 🇫🇷 法国 | 世界报、法新社(索引) |
| 🇩🇪 德国 | DW |
| 🇮🇹 意大利 | ANSA |
| 🇷🇺 俄罗斯 | TASS、RT |
| 🇯🇵 日本 | NHK(JSON API)、共同社 |
| 🇰🇷 韩国 | 韩联社、韩国先驱报 |
| 🇨🇳 中国 | 央视、中新网、人民网、环球时报、CGTN、观察者网、参考消息 |
| 🇮🇳 印度 | 印度教徒报 |
| 🇵🇰 巴基斯坦 | 黎明报 |
| 🇮🇷 伊朗 | Press TV |
| 🇮🇱 以色列 | 国土报 |
| 🇹🇷 土耳其 | Daily Sabah 晨报 |
| 🇸🇦 沙特 | Asharq Al-Awsat |
| 🇶🇦 卡塔尔 | 半岛台 Al Jazeera |
| 🇸🇬 新加坡 | CNA、海峡时报、联合早报、商业时报 |
| 🇹🇭 泰国 | 曼谷邮报 |
| 🌍 全球 | 中东眼、Investing.com、Google News 中文聚合 |

> 无 RSS 的站(CNA/曼谷邮报/ANSA/联合早报/财新)通过 **AnySearch** 穿透付费墙/cookie 墙直接抓首页头条。

---

## 🚀 快速开始

### 依赖

```bash
pip install requests   # 仅 AnySearch 抓取需要
```

### 生成一份早报

```python
import bbc_news as b
digest = b.build_digest()   # 默认 34 条精选
print(digest)
```

### 子命令(Telegram Bot 内)

```bash
/bbc             # 今日全球早报
/bbc 经济        # 只看经济类
/bbc 军事        # 只看军事类
/bbc th          # 只看泰国视角
/bbc 2           # 第二页
```

### 网页部署

```bash
python3 brief_deploy.py   # 读取 digest → 生成当日 HTML + 历史归档 → 注入主页
```

---

## 📁 项目结构

```
├── bbc_news.py        # 核心:40+ 源抓取 → 聚类 → 排序 → 翻译 → digest 生成
├── brief_deploy.py    # 网页部署:digest → HTML(含历史归档、主页注入)
└── README.md
```

---

## 🔧 可选配置

| 配置 | 说明 |
|---|---|
| `/root/.anysearch_key` | AnySearch API key(可选,穿透付费墙抓无 RSS 站;无 key 则自动跳过) |
| `SOURCES` / `CN_SOURCES` | 媒体源列表,按 `(名称, 视角, 集团, 官方?, 类型, URL, 参数)` 增删 |
| `HIST_FILE` | 历史去重文件(默认 `/root/.bbc_history.json`,按日期存储,自动清理) |

---

## ⚖️ 免责声明

本项目仅聚合**公开 RSS 与页面头条的标题级信息**用于个人学习阅读,不提供全文转载。所有新闻版权归原始媒体所有,请通过文末链接访问原文。AnySearch 抓取仅限公开页面。

---

## 📜 License

MIT
