#!/usr/bin/env python3
"""全球早报 → 主页部署器(2026-08-08 太甲钦定)
流程: bbc_daily.py 推送后存 /root/.bbc_digest.txt → 本脚本转 HTML:
  1. 写 /zye/brief/YYYY-MM-DD.html(当日完整早报)
  2. 重建 /zye/brief/index.html(历史归档,按日期倒序)
  3. 更新 /zye/index.html 左栏(替换诗词鉴赏为当日早报)
  4. 5G 上限: /zye/brief 超 5G 删最早
"""
import os, re, glob, shutil, subprocess
from datetime import datetime, timedelta, timezone

BRIEF_DIR = "/zye/brief"
DIGEST = "/root/.bbc_digest.txt"
INDEX = "/zye/index.html"
MAX_BYTES = 5 * 1024 * 1024 * 1024  # 5G

CN = timedelta(hours=8)

def now_str():
    return (datetime.now(timezone.utc) + CN).strftime("%Y-%m-%d %H:%M")

def today_str():
    return (datetime.now(timezone.utc) + CN).strftime("%Y-%m-%d")

def parse_digest(text):
    """解析 digest 为 ([(区块名, [(编号, 标题html, 摘要, 视角行s)])], 市场行html)"""
    sections = []
    cur_name = None
    cur_items = []
    market = ""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            i += 1
            continue
        m0 = re.match(r"^💹\s+(.*)$", ln)
        if m0:
            # 红涨绿跌着色: ▲涨→红, ▼跌→绿
            market = re.sub(r"(▲)([-\d.]+%)",
                            r'<span class="m-up">\1\2</span>', m0.group(1))
            market = re.sub(r"(▼)([-\d.]+%)",
                            r'<span class="m-down">\1\2</span>', market)
            i += 1
            continue
        m = re.match(r"^(🔥 今日焦点|⭐ 多方关注|👀 双源关注|📡 独家观察|📈 持续跟进|🔥 国内热搜\(百度\)|🇨🇳 中文视角)\s*(\(\d+\))?:?\s*$", ln)
        if m:
            if cur_name:
                sections.append((cur_name, cur_items))
            cur_name = m.group(1)
            cur_items = []
            i += 1
            continue
        m2 = re.match(r"^\s*(\d+)\.\s+(.*)$", ln)
        if m2 and cur_name:
            cur_items.append([m2.group(1), m2.group(2), "", []])
            i += 1
            continue
        m3 = re.match(r"^📌\s+(.*)$", ln)
        if m3 and cur_name and cur_items:
            cur_items[-1][2] = m3.group(1)
            i += 1
            continue
        m4 = re.match(r"^·\s+(.*)$", ln)
        if m4 and cur_name and cur_items:
            cur_items[-1][3].append(m4.group(1))
            i += 1
            continue
        # 视角分隔线等杂行忽略
        i += 1
    if cur_name:
        sections.append((cur_name, cur_items))
    return sections, market

def _add_target(html_str):
    """主页链接新标签: 所有 <a href> 加 target=_blank(仅主页,不影响 TG digest)"""
    return re.sub(r'<a\s+href=', '<a target="_blank" href=', html_str)


def brief_html(sections, main_title=None, market=""):
    """左栏/当天页共用: 区块列表 HTML。main_title 时第一区块头替换为早报标题+历史链接"""
    h = []
    if market:
        h.append('<div class="bmarket">💹 %s</div>' % _add_target(market))
    first = True
    for name, items in sections:
        if not items:
            continue
        h.append('<div class="bsect">')
        if main_title and first and name.startswith('\U0001F525'):
            h.append('<div class="bsect-h" style="display:flex;justify-content:space-between;align-items:center;">'
                     '<span class="bt-title">\U0001F4F0 全球早报 \u00b7 %s</span>'
                     '<a href="/brief/" style="font-size:14px;color:#7e7eff;text-decoration:none;border:1px solid #7e7eff55;border-radius:6px;padding:3px 10px;">\U0001F5C2 历史早报</a>'
                     '</div>' % main_title)
        else:
            h.append('<div class="bsect-h">%s <span class="bcount">%d</span></div>' % (name, len(items)))
        first = False
        for num, title, summ, views in items:
            h.append('<div class="bitem">')
            h.append('<div class="btitle"><span class="bnum">%s</span> %s</div>' % (num, _add_target(title)))
            if summ:
                h.append('<div class="bsum">📌 %s</div>' % summ)
            if views:
                for v in views[:5]:
                    h.append('<div class="bview">%s</div>' % _add_target(v))
            h.append('</div>')
        h.append('</div>')
    return "\n".join(h)

STYLE = """
<style>
body{background:#121212;background-image:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f0f23 100%);color:#e0e0e0;font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;padding:20px;}
.wrap{max-width:880px;margin:0 auto;}
.head{display:flex;align-items:baseline;gap:14px;border-bottom:1px solid rgba(255,255,255,.12);padding-bottom:14px;margin-bottom:22px;flex-wrap:wrap;}
.head h1{font-size:23px;color:#f0f0ff;margin:0;letter-spacing:.5px;}
.head .date{color:#999;font-size:14px;}
.head a{color:#7e7eff;text-decoration:none;font-size:14px;}
.head a:hover{text-decoration:underline;}
.bsect{background:rgba(20,20,35,.72);border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:16px 18px 14px;margin-bottom:18px;backdrop-filter:blur(10px);}
.bsect-h{color:#cdb5ff;font-weight:bold;font-size:15px;margin-bottom:12px;padding-bottom:9px;border-bottom:1px solid rgba(126,126,255,.25);letter-spacing:.5px;}
.bt-title{font-size:18px;color:#a78bfa;font-weight:bold;letter-spacing:.5px;display:inline-flex;align-items:center;gap:6px;padding-left:6px;}
.bcount{color:#777;font-weight:normal;font-size:12px;margin-left:2px;}
.bitem{padding:11px 2px;border-bottom:1px solid rgba(255,255,255,.055);}
.bitem:last-child{border-bottom:none;padding-bottom:4px;}
.btitle{font-size:15px;line-height:1.65;color:#f0f0f8;}
.btitle a{color:#f0f0f8;text-decoration:none;}
.btitle a:hover{color:#a0b4e8;text-decoration:underline;}
.bnum{color:#7e7eff;font-weight:bold;margin-right:5px;}
.bsum{color:#a0b4e8;font-size:12.5px;line-height:1.65;margin:6px 0 0 26px;}
.bview{color:#8585a8;font-size:12px;line-height:1.6;margin:4px 0 0 26px;opacity:.85;}
.bview::before{content:"· ";color:#6a6a90;}
.bmarket{font-size:13px;color:#b0b0cc;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:8px 12px;margin-bottom:14px;line-height:1.6;}
.bmarket a{color:inherit;text-decoration:none;}
.bmarket a:hover{color:inherit;text-decoration:none;}
.m-up{color:#ff6b6b;font-weight:bold;}
.m-down{color:#51cf66;font-weight:bold;}
.foot{color:#555;font-size:12px;text-align:center;margin-top:28px;letter-spacing:.3px;}
.arch-item{display:flex;justify-content:space-between;align-items:center;background:rgba(20,20,35,.72);border:1px solid rgba(255,255,255,.09);border-radius:12px;padding:13px 18px;margin-bottom:11px;text-decoration:none;color:#e0e0e0;transition:.2s;}
.arch-item:hover{border-color:#7e7eff;background:rgba(30,30,50,.85);}
.arch-item .d{font-weight:bold;color:#cdb5ff;font-size:15.5px;letter-spacing:.5px;}
.arch-item .t{color:#999;font-size:12.5px;}
</style>
"""

def page_head(title, date_str, back_link=False):
    bl = '<a href="/brief/">🗂 历史早报</a>' if back_link else '<a href="/">&larr; 回主页</a>'
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/><title>%s</title>%s</head><body>'
            '<div class="wrap"><div class="head"><h1>%s</h1><span class="date">%s</span>%s</div>'
            % (title, STYLE, title, date_str, bl))

def page_foot():
    return '<div class="foot">否极轩 · 全球早报 · 每日一更 · 自动归档</div></div></body></html>'

def write_daily(sections, date_str, market=""):
    """写 /zye/brief/YYYY-MM-DD.html"""
    os.makedirs(BRIEF_DIR, exist_ok=True)
    body = page_head("全球早报 · %s" % date_str, date_str, back_link=True)
    body += brief_html(sections, market=market)
    body += page_foot()
    path = os.path.join(BRIEF_DIR, date_str + ".html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path

def write_archive():
    """重建 /zye/brief/index.html 归档索引"""
    files = sorted(glob.glob(os.path.join(BRIEF_DIR, "*.html")), reverse=True)
    files = [f for f in files if os.path.basename(f) != "index.html"]
    body = page_head("🗂 历史早报", "共 %d 期" % len(files), back_link=False)
    if not files:
        body += '<div class="bsect">还没有历史早报,今天将是创刊号 📰</div>'
    for f in files:
        d = os.path.basename(f)[:10]
        # 预览:取当天焦点数
        preview = ""
        try:
            txt = open(f, encoding="utf-8").read()
            m = re.search(r'今日焦点[^<]*<span class="bcount">(\d+)</span>', txt)
            if m:
                preview = "焦点 %s 条" % m.group(1)
        except Exception:
            pass
        body += '<a class="arch-item" href="/brief/%s"><span class="d">📰 %s</span><span class="t">%s</span></a>' % (os.path.basename(f), d, preview)
    body += page_foot()
    with open(os.path.join(BRIEF_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(body)

BRIEF_CSS = """/* brief-css */
.bsect{background:rgba(20,20,35,.72);border:1px solid rgba(255,255,255,.09);border-radius:12px;padding:13px 15px 11px;margin-bottom:14px;backdrop-filter:blur(10px);}
.bsect-h{color:#cdb5ff;font-weight:bold;font-size:14.5px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid rgba(126,126,255,.25);letter-spacing:.5px;}
.bt-title{font-size:18px;color:#a78bfa;font-weight:bold;letter-spacing:.5px;display:inline-flex;align-items:center;gap:6px;padding-left:6px;}
.bcount{color:#777;font-weight:normal;font-size:12px;margin-left:2px;}
.bitem{padding:9px 2px;border-bottom:1px solid rgba(255,255,255,.055);}
.bitem:last-child{border-bottom:none;padding-bottom:3px;}
.btitle{font-size:15px;line-height:1.6;color:#f0f0f8;}
.btitle a{color:#f0f0f8;text-decoration:none;}
.btitle a:hover{color:#a0b4e8;text-decoration:underline;}
.bnum{color:#7e7eff;font-weight:bold;margin-right:5px;}
.bsum{color:#a0b4e8;font-size:12.5px;line-height:1.6;margin:5px 0 0 24px;}
.bview{color:#8585a8;font-size:12px;line-height:1.55;margin:4px 0 0 24px;opacity:.85;}
.bview::before{content:"· ";color:#6a6a90;}
.bmarket{font-size:13px;color:#b0b0cc;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:8px 12px;margin-bottom:14px;line-height:1.6;}
.bmarket a{color:inherit;text-decoration:none;}
.bmarket a:hover{color:inherit;text-decoration:none;}
.m-up{color:#ff6b6b;font-weight:bold;}
.m-down{color:#51cf66;font-weight:bold;}
"""


def inject_css(html):
    """注入早报样式到 <head>。已存在则整块替换(保证样式更新生效)"""
    import re
    pat = re.compile(r"<style>\s*/\* brief-css \*/.*?<\/style>", re.S)
    css = "<style>" + BRIEF_CSS + "</style>"
    if pat.search(html):
        return pat.sub(css, html, count=1)
    return html.replace("</head>", css + "\n</head>", 1)


def update_index(sections, date_str, market=""):
    """替换早报面板(现位于中间栏)。定位 poem-panel 自身,层级计数找闭合,
    后验三宝(留言/视频/水滴)必须完好,任何缺失拒绝写文件。"""
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    html = inject_css(html)
    panel = brief_html(sections, main_title=date_str, market=market)
    new_panel = ('<div class="poem-panel">%s</div>') % panel
    # 定位早报面板自身
    cls = html.find('class="poem-panel"')
    if cls < 0:
        raise RuntimeError("poem-panel 未找到,拒绝替换")
    pstart = html.rfind('<div', 0, cls)
    # 层级计数找面板闭合
    i = pstart
    depth = 0
    while i < len(html):
        if html.startswith('<div', i):
            depth += 1
            i += 4
        elif html.startswith('</div>', i):
            depth -= 1
            i += 6
            if depth == 0:
                break
        else:
            i += 1
    new_html = html[:pstart] + new_panel + html[i:]
    # 后验三宝
    for m in ('<div class="chat"', 'id="videos"', 'href="/dida"',
              '<div class="video-panel"'):
        assert m in new_html, "后验失败: " + m
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)
def enforce_5g():
    """超 5G 删最早(保留 index.html)"""
    files = sorted(glob.glob(os.path.join(BRIEF_DIR, "*.html")))
    total = sum(os.path.getsize(f) for f in files if os.path.basename(f) != "index.html")
    if total <= MAX_BYTES:
        return total
    # 从最早开始删
    for f in files:
        if os.path.basename(f) == "index.html":
            continue
        os.remove(f)
        total -= os.path.getsize(f)
        if total <= MAX_BYTES:
            break
    write_archive()
    return total

def main():
    if not os.path.exists(DIGEST):
        print("no digest, skip")
        return
    # 日期校验:digest 必须是今天生成的,防止昨天失败残留覆盖今天
    try:
        d = open("/root/.bbc_digest_date").read().strip()
        if d != today_str():
            print("stale digest (%s != %s), skip" % (d, today_str()))
            return
    except Exception:
        pass
    text = open(DIGEST, encoding="utf-8").read()
    sections, market = parse_digest(text)
    if not sections:
        print("digest empty, skip")
        return
    date_str = today_str()
    dpath = write_daily(sections, date_str, market)
    write_archive()
    update_index(sections, date_str, market)
    total = enforce_5g()
    print("OK %s -> %s (%d sections, brief dir %.1fMB)" % (date_str, dpath, len(sections), total / 1048576))

if __name__ == "__main__":
    main()
