#!/usr/bin/env python3
"""AI News Telegraph - Multi-source real-time AI news aggregator with HK stock tracking"""

import http.server
import json
import urllib.request
import urllib.parse
import ssl
import hashlib
import time
import re
import difflib
import os
import socketserver
from datetime import datetime, timezone, timedelta
from pathlib import Path

PORT = int(os.environ.get('PORT', 3000))
STATIC_DIR = Path(__file__).parent / 'static'

# ── SSL context (bypass cert verification for some APIs) ──
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# ── Stock configuration ──
STOCKS = [
    {'code': '00506', 'name': '中国食品', 'en': 'COFCO'},
    {'code': '00696', 'name': '民航信息', 'en': 'TravelSky'},
    {'code': '00960', 'name': '龙湖集团', 'en': 'Longfor'},
    {'code': '02498', 'name': '速腾聚创', 'en': 'RoboSense'},
    {'code': '02669', 'name': '中海物业', 'en': 'ChinaOverseasProp'},
    {'code': '06862', 'name': '海底捞', 'en': 'Haidilao'},
    {'code': '00700', 'name': '腾讯控股', 'en': 'Tencent'},
    {'code': '09988', 'name': '阿里巴巴', 'en': 'Alibaba'},
]

# ── AI keyword categories ──
AI_CATEGORIES = {
    '大模型': [
        '大模型', 'LLM', 'GPT', 'Claude', 'Gemini', 'Llama', '通义', '文心', '星火',
        '豆包', 'Kimi', '智谱', 'ChatGLM', 'DeepSeek', 'Qwen', '百川', 'MiniMax',
        '语言模型', '基础模型', '预训练', '微调', 'RLHF', '蒸馏', '量化', '推理',
        'Transformer', '注意力', 'MoE', '参数', '开源模型', '闭源', 'Benchmark',
        'Sora', '多模态', '世界模型', 'AGI', '通用人工智能', 'MaaS', '模型服务',
        'Token', '上下文窗口', '长文本', 'RAG', '检索增强', 'R1', 'o1', 'o3',
        'Claude 4', 'GPT-5', 'GPT5', 'o4', 'DeepSeek', '大语言模型',
    ],
    '芯片算力': [
        '芯片', 'GPU', 'CPU', 'NPU', 'TPU', 'AI芯片', '算力', '英伟达', 'NVIDIA',
        'AMD', '华为昇腾', '寒武纪', '光模块', 'HBM', '封装', '制程', '台积电',
        '三星', '中芯国际', 'ASML', '光刻', '晶圆', '半导体', '存储芯片',
        '数据中心', '服务器', '交换机', '液冷', '超算', '智算', '互联芯片',
        'DPU', 'FPGA', 'SoC', 'ASIC', 'RISC-V', '先进封装', 'CoWoS', 'Chiplet',
        'CUDA', '算卡', '加速卡', 'AI服务器', 'GB200', 'GB300', 'B100', 'B200',
        'H100', 'H200', 'A100', '昇腾', '昆仑芯',
    ],
    'AI应用': [
        'AI应用', 'AI Agent', '智能体', 'AI搜索', 'AI办公', 'AI教育', 'AI医疗',
        'AI金融', 'AI法律', 'AI客服', 'AI写作', 'AI绘画', 'AI音乐', 'AI视频',
        'AIGC', '生成式', 'Copilot', 'AI编程', '代码助手', 'AI设计', 'AI营销',
        '数字人', '虚拟人', '具身智能', '人形机器人', '自动驾驶', 'AI手机',
        'AI PC', 'AI眼镜', 'AI硬件', 'AI玩具', 'AI伴侣', 'AI社交',
        'AI翻译', 'AI摘要', 'AI助手', '智能助手', 'Sora', '可灵', 'Vidu',
        '文生图', '文生视频', '图生视频', 'AI换脸', 'AI配音', 'TTS', 'ASR',
        'AI制药', 'AI诊断', 'AI投顾', 'AI风控', '机器人产业', '无人机产业',
    ],
    '政策产业': [
        'AI政策', 'AI监管', 'AI治理', 'AI安全法', '人工智能法', 'AI标准',
        'AI伦理', '数据安全', '算法备案', '深度伪造', '生成式AI管理',
        'WAIC', '世界人工智能大会', 'AI峰会', 'AI投资', 'AI融资', 'AI独角兽',
        'AI上市', 'AI公司', 'AI创业', 'AI赛道', 'AI产业', 'AI生态',
        'AI人才', 'AI开源', 'AI联盟', 'AI合作', 'AI战略', 'AI规划',
        '新基建', '东数西算', '人工智能+', 'AI+', '智算中心', 'AI产业园',
    ],
}

# ── Global state ──
news_data = {'all': [], 'by_category': {}, 'sources': {}, 'last_update': 0, 'update_time': ''}
stock_data = {'stocks': [], 'last_update': 0, 'update_time': ''}


# ═══════════════════════════════════════════════════════════
# HTTP Utilities
# ═══════════════════════════════════════════════════════════

def http_get_json(url, headers=None, timeout=15):
    h = {'User-Agent': UA, 'Accept': 'application/json'}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
    return json.loads(resp.read().decode('utf-8'))


def http_get_text(url, headers=None, encoding='utf-8', timeout=15):
    h = {'User-Agent': UA}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    resp = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
    return resp.read().decode(encoding, errors='replace')


def clean_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()


def make_item(source, title, content, ts, url, extra=None):
    item = {
        'source': source,
        'title': title,
        'content': content,
        'timestamp': ts,
        'url': url,
        'time_str': '',
    }
    if extra:
        item.update(extra)
    if ts:
        try:
            dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
            item['time_str'] = dt.strftime('%H:%M:%S')
        except:
            pass
    return item


# ═══════════════════════════════════════════════════════════
# News Source Fetchers
# ═══════════════════════════════════════════════════════════

def fetch_cls():
    """财联社电报"""
    try:
        params = {
            'app': 'CailianpressWeb', 'os': 'web', 'sv': '8.7.9',
            'rn': '40', 'refresh_type': '1',
        }
        sorted_keys = sorted(params.keys())
        sign_str = '&'.join(f"{k}={params[k]}" for k in sorted_keys)
        sha1 = hashlib.sha1(sign_str.encode()).hexdigest()
        sign = hashlib.md5(sha1.encode()).hexdigest()

        params['sign'] = sign
        qs = '&'.join(f"{k}={v}" for k, v in params.items())
        url = f"https://www.cls.cn/v1/roll/get_roll_list?{qs}"

        data = http_get_json(url, headers={'Referer': 'https://www.cls.cn/telegraph'})
        items = []
        for item in data.get('data', {}).get('roll_data', []):
            title = item.get('title', '') or ''
            content = clean_html(item.get('content', '') or '')
            ts = item.get('ctime')
            link = f"https://www.cls.cn/detail/{item.get('id', '')}"
            if title or content:
                items.append(make_item('财联社', title or content[:60], content, ts, link))
        return items
    except Exception as e:
        print(f"[CLS Error] {e}")
        return []


def fetch_tencent():
    """腾讯新闻"""
    try:
        url = "https://r.inews.qq.com/gw/event/hot_ranking_list?page_size=80"
        data = http_get_json(url)
        items = []
        for group in data.get('idlist', []):
            for item in group.get('newslist', []):
                title = item.get('title', '')
                if not title or len(title) < 6:
                    continue
                # Skip placeholder items
                if '最关注的热点' in title:
                    continue
                ts = item.get('timestamp')
                link = item.get('url') or item.get('surl') or ''
                abstract = item.get('abstract') or item.get('intro') or ''
                items.append(make_item('腾讯新闻', title, abstract or title, ts, link))
        return items
    except Exception as e:
        print(f"[Tencent Error] {e}")
        return []


def fetch_sina():
    """新浪财经"""
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num=80&page=1"
        data = http_get_json(url)
        items = []
        for item in data.get('result', {}).get('data', []):
            title = item.get('title', '')
            if not title:
                continue
            summary = item.get('summary') or item.get('intro') or ''
            summary = clean_html(summary)
            ts = int(item.get('ctime', 0)) or None
            link = item.get('url', '')
            items.append(make_item('新浪财经', title, summary or title, ts, link))
        return items
    except Exception as e:
        print(f"[Sina Error] {e}")
        return []


def fetch_wallstreetcn():
    """华尔街见闻"""
    try:
        url = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=50"
        data = http_get_json(url)
        items = []
        for item in data.get('data', {}).get('items', []):
            title = item.get('title') or ''
            content = clean_html(item.get('content_text') or item.get('content') or '')
            ts = item.get('display_time')
            link = item.get('uri', '')
            if title or content:
                items.append(make_item('华尔街见闻', title or content[:60], content, ts, link))
        return items
    except Exception as e:
        print(f"[WSJ CN Error] {e}")
        return []


def fetch_36kr():
    """36氪"""
    try:
        url = "https://36kr.com/api/newsflash?per_page=50"
        data = http_get_json(url)
        items = []
        for item in data.get('data', {}).get('items', []):
            title = item.get('title', '')
            desc = item.get('description', '')
            ts_str = item.get('updated_at') or item.get('created_at') or ''
            ts = None
            if ts_str:
                try:
                    dt = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                    ts = int(dt.timestamp())
                except:
                    pass
            link = item.get('news_url') or f"https://36kr.com/newsflashes/{item.get('id', '')}"
            items.append(make_item('36氪', title, desc or title, ts, link))
        return items
    except Exception as e:
        print(f"[36kr Error] {e}")
        return []


def fetch_ithome():
    """IT之家"""
    try:
        url = "https://api.ithome.com/json/newslist/news"
        data = http_get_json(url)
        items = []
        for item in data.get('newslist', []):
            title = item.get('title', '')
            desc = item.get('description', '')
            ts_str = item.get('postdate', '')
            ts = None
            if ts_str:
                try:
                    dt = datetime.fromisoformat(ts_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
                    ts = int(dt.timestamp())
                except:
                    pass
            newsid = item.get('newsid', '')
            link = item.get('url') or f"https://www.ithome.com/0/{newsid}.htm"
            items.append(make_item('IT之家', title, desc or title, ts, link))
        return items
    except Exception as e:
        print(f"[ITHome Error] {e}")
        return []


# ═══════════════════════════════════════════════════════════
# Stock Fetcher
# ═══════════════════════════════════════════════════════════

def fetch_stocks():
    """Fetch HK stock quotes from Sina"""
    try:
        codes = ','.join(f"rt_hk{s['code']}" for s in STOCKS)
        url = f"https://hq.sinajs.cn/list={codes}"
        text = http_get_text(url, headers={'Referer': 'https://finance.sina.com.cn'}, encoding='gbk')
        results = []
        for stock in STOCKS:
            pattern = f'var hq_str_rt_hk{stock["code"]}="([^"]*)"'
            match = re.search(pattern, text)
            if match and match.group(1):
                vals = match.group(1).split(',')
                if len(vals) > 10:
                    results.append({
                        'code': stock['code'],
                        'name': stock['name'],
                        'en_name': stock['en'],
                        'current': float(vals[6]) if vals[6] else 0,
                        'prev_close': float(vals[3]) if vals[3] else 0,
                        'open': float(vals[2]) if vals[2] else 0,
                        'high': float(vals[4]) if vals[4] else 0,
                        'low': float(vals[5]) if vals[5] else 0,
                        'change': float(vals[7]) if vals[7] else 0,
                        'change_pct': float(vals[8]) if vals[8] else 0,
                        'volume': float(vals[12]) if vals[12] else 0,
                        'amount': float(vals[11]) if vals[11] else 0,
                        'date': vals[17] if len(vals) > 17 else '',
                        'time': vals[18] if len(vals) > 18 else '',
                    })
        return results
    except Exception as e:
        print(f"[Stock Error] {e}")
        return []


# ═══════════════════════════════════════════════════════════
# AI Filter & Deduplication
# ═══════════════════════════════════════════════════════════

def is_ai_related(title, content):
    """Check if news is AI-related. Title match = always accepted. Content-only needs 2+ hits."""
    title_upper = title.upper()
    content_upper = content.upper()
    title_match_cat = None

    # Check title first (strong signal)
    for cat, keywords in AI_CATEGORIES.items():
        for kw in keywords:
            if kw.upper() in title_upper:
                return True, cat

    # Content-only: require at least 2 keyword matches
    match_count = 0
    first_cat = None
    for cat, keywords in AI_CATEGORIES.items():
        for kw in keywords:
            if kw.upper() in content_upper:
                match_count += 1
                if first_cat is None:
                    first_cat = cat
                if match_count >= 2:
                    return True, first_cat

    return False, None


def classify_item(title, content):
    cats = []
    text = f"{title} {content}".upper()
    for cat, keywords in AI_CATEGORIES.items():
        for kw in keywords:
            if kw.upper() in text:
                cats.append(cat)
                break
    return cats if cats else ['其他']


def deduplicate(items):
    if not items:
        return []
    unique = []
    seen_titles = []
    for item in items:
        t = item['title'].strip()
        is_dup = False
        for seen in seen_titles:
            if len(t) > 8 and len(seen) > 8:
                ratio = difflib.SequenceMatcher(None, t, seen).ratio()
                if ratio > 0.6:
                    is_dup = True
                    break
        if not is_dup:
            seen_titles.append(t)
            unique.append(item)
    return unique


# ═══════════════════════════════════════════════════════════
# Data Refresh
# ═══════════════════════════════════════════════════════════

def refresh_news():
    global news_data
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing news...")

    fetchers = [
        ('财联社', fetch_cls),
        ('腾讯新闻', fetch_tencent),
        ('新浪财经', fetch_sina),
        ('华尔街见闻', fetch_wallstreetcn),
        ('36氪', fetch_36kr),
        ('IT之家', fetch_ithome),
    ]

    all_items = []
    source_stats = {}

    for name, fn in fetchers:
        try:
            items = fn()
            source_stats[name] = {'total': len(items), 'status': 'ok'}
            all_items.extend(items)
            print(f"  {name}: {len(items)} items")
        except Exception as e:
            source_stats[name] = {'total': 0, 'status': f'error: {e}'}
            print(f"  {name}: ERROR {e}")

    # Filter AI-related
    ai_items = []
    for item in all_items:
        is_ai, primary_cat = is_ai_related(item['title'], item['content'])
        if is_ai:
            item['ai_category'] = primary_cat
            item['categories'] = classify_item(item['title'], item['content'])
            ai_items.append(item)

    # Deduplicate
    unique = deduplicate(ai_items)
    unique.sort(key=lambda x: x.get('timestamp') or 0, reverse=True)

    # Group by category
    by_cat = {}
    for item in unique:
        for cat in item.get('categories', []):
            by_cat.setdefault(cat, []).append(item)

    news_data = {
        'all': unique,
        'by_category': by_cat,
        'sources': source_stats,
        'last_update': time.time(),
        'update_time': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
        'total_fetched': len(all_items),
        'ai_filtered': len(ai_items),
        'after_dedup': len(unique),
    }
    print(f"  => Total: {len(all_items)}, AI: {len(ai_items)}, After dedup: {len(unique)}")


def refresh_stock():
    global stock_data
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Refreshing stocks...")
    stocks = fetch_stocks()
    stock_data = {
        'stocks': stocks,
        'last_update': time.time(),
        'update_time': datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S'),
    }
    print(f"  => {len(stocks)} stocks updated")


# ═══════════════════════════════════════════════════════════
# HTTP Request Handler
# ═══════════════════════════════════════════════════════════

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == '/api/news':
            self.send_json(news_data)
        elif path == '/api/stocks':
            self.send_json(stock_data)
        elif path == '/api/refresh':
            refresh_news()
            refresh_stock()
            self.send_json({'ok': True, 'time': news_data.get('update_time', '')})
        elif path == '/api/status':
            self.send_json({
                'news_update': news_data.get('update_time', ''),
                'stock_update': stock_data.get('update_time', ''),
                'news_count': len(news_data.get('all', [])),
                'stock_count': len(stock_data.get('stocks', [])),
                'sources': news_data.get('sources', {}),
            })
        else:
            super().do_GET()

    def send_json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Suppress request logs


class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    # Ensure static directory exists
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    # Initial data load
    print("Initial data load...")
    refresh_news()
    refresh_stock()

    # Start server
    server = ThreadedServer(('0.0.0.0', PORT), Handler)
    print(f"\n{'='*50}")
    print(f"  AI News Telegraph Server")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*50}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == '__main__':
    main()
