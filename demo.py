# -*- coding:utf-8 -*-
"""
冰箱智能助手（最终版 — 本地严格计算天数，AI 仅负责润色）
说明:
- history.txt 每行格式: YYYY.MM.DD 数量 名称  （第一列为到期日）
- data.txt 用于优先推断保质期天数（示例格式见你的 data）
- 添加/删除/查询均已实现，查询时本地计算 days_left 并把结构化 JSON 发给模型由模型生成自然语言
- 若 Spark 无法响应，将使用本地模板生成最终文本
"""
import os
import re
import time
import wave
import pyaudio
from datetime import datetime, timedelta
from aip import AipSpeech
import websocket
import json
import base64
import hashlib
import hmac
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time
import ssl

# -------------------- 配置 --------------------
APP_ID = '120707525'
API_KEY = 'rZVAwVCohhATnbVZRhkhr5c5'
SECRET_KEY = '9uw06M6IgTL5woUE3QuS6Wzqm5EXZeq4'

# Spark 模型配置
SPARK_APPID = "317626fb"
SPARK_API_KEY = "834afce2724eec249e4dc21d0ca3e8dc"
SPARK_API_SECRET = "YmZkYTkzY2ViZWY0MTc2ZDZjNWQzNWRl"
SPARK_DOMAIN = "4.0Ultra"
SPARK_URL = "wss://spark-api.xf-yun.com/v4.0/chat"

# 文件
AUDIO_FILE = "./data/chat-audio.wav"
HISTORY_FILE = "history.txt"
DATA_FILE = "data.txt"

# -------------------- 录音 --------------------
def record_sound(file_path, seconds):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    pau = pyaudio.PyAudio()
    stream = pau.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    for _ in range(0, int(RATE / CHUNK * seconds)):
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    pau.terminate()
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(pau.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# -------------------- 语音识别 --------------------
def speech_to_text(file_path):
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
    data = open(file_path, 'rb').read()
    ret = client.asr(data, 'pcm', 16000, {'dev_pid': 1536})
    if not ret:
        return ""
    if ret.get('err_msg') == 'recognition error.':
        return ""
    return ret.get('result', [""])[0]

# -------------------- 文本处理 --------------------
num_map = {
    "一个":1,"两个":2,"三个":3,"四个":4,"五个":5,"六个":6,"七个":7,"八个":8,"九个":9,"十个":10,
    "一瓶":1,"二瓶":2,"三瓶":3,"四瓶":4,"五瓶":5,"六瓶":6,"七瓶":7,"八瓶":8,"九瓶":9,"十瓶":10,
    "一盒":1,"二盒":2,"三盒":3,"四盒":4,"五盒":5,"六盒":6,"七盒":7,"八盒":8,"九盒":9,"十盒":10,
    "一包":1,"二包":2,"三包":3,"四包":4,"五包":5,"六包":6,"七包":7,"八包":8,"九包":9,"十包":10,
    "一捆":1,"二捆":2,"三捆":3,"四捆":4,"五捆":5,"六捆":6,"七捆":7,"八捆":8,"九捆":9,"十捆":10,
    "一袋":1,"二袋":2,"三袋":3,"四袋":4,"五袋":5,"六袋":6,"七袋":7,"八袋":8,"九袋":9,"十袋":10,
    "一斤":1,"二斤":2,"三斤":3,"四斤":4,"五斤":5,"六斤":6,"七斤":7,"八斤":8,"九斤":9,"十斤":10,
    "一块":1,"二块":2,"三块":3,"四块":4,"五块":5,"六块":6,"七块":7,"八块":8,"九块":9,"十块":10,
    "一根":1,"二根":2,"三根":3,"四根":4,"五根":5,"六根":6,"七根":7,"八根":8,"九根":9,"十根":10,
    "一棵":1,"二棵":2,"三棵":3,"四棵":4,"五棵":5,"六棵":6,"七棵":7,"八棵":8,"九棵":9,"十棵":10,
    "一只":1,"二只":2,"三只":3,"四只":4,"五只":5,"六只":6,"七只":7,"八只":8,"九只":9,"十只":10,
    "一罐":1,"二罐":2,"三罐":3,"四罐":4,"五罐":5,"六罐":6,"七罐":7,"八罐":8,"九罐":9,"十罐":10,
    "一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10
}

VERB_PATTERN = r"(我|把|将|已|刚|刚刚)?(放入|放进|放了|买了|存入|存了|加入|添了|拿出|拿出来|拿出了|拿走|拿走了|取出|取走|移除|移除了|吃掉|吃了|吃完了|用掉|用掉了|用完了|用了|扔掉了|倒掉了|扔了|放进去|放入了|放进了|加入了|取出来|取出来了)"

def extract_number_and_name(text):
    text = text.strip()
    # 检查是否包含“全部”“所有”“一部分”等，标记 qty = 'ALL'
    if any(w in text for w in ["全部","所有"]):
        name = re.sub(VERB_PATTERN, "", text)
        name = name.replace("了","").replace("全部","").replace("所有","").strip()
        return 'ALL', name.strip()
    for k in sorted(num_map.keys(), key=lambda x: -len(x)):
        if k in text:
            qty = num_map[k]
            name = text.replace(k, "")
            name = re.sub(VERB_PATTERN, "", name)
            name = name.replace("了", "").strip()
            return qty, name.strip()
    name = re.sub(VERB_PATTERN, "", text)
    name = name.replace("了", "").strip()
    return 1, name.strip()

# -------------------- data.txt 解析（程序启动时） --------------------
def load_datafile_mapping(data_file=DATA_FILE):
    mapping = {}
    if not os.path.exists(data_file):
        return mapping, []
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.search(r"^(.+?)[\s:：\-]+.*?(\d{1,4})\b", line)
            if m:
                raw_name = m.group(1).strip()
                try:
                    days = int(m.group(2))
                except:
                    continue
                mapping[raw_name.lower()] = days
                continue
            m2 = re.search(r"(.+?)(\d{1,4})\s*$", line)
            if m2:
                raw_name = m2.group(1).strip()
                days = int(m2.group(2))
                mapping[raw_name.lower()] = days
                continue
            m3 = re.search(r"(\d{1,4})", line)
            if m3:
                days = int(m3.group(1))
                raw_name = re.sub(r"(\d+)", "", line).strip()
                if raw_name:
                    mapping[raw_name.lower()] = days
    keys_sorted = sorted(mapping.keys(), key=lambda x: -len(x))
    return mapping, keys_sorted

DATA_MAPPING, DATA_KEYS_SORTED = load_datafile_mapping()

# -------------------- Spark 模型调用（保持不变） --------------------
answer = ""
def call_spark_model(messages_or_text):
    global answer
    answer = ""

    def on_message(ws, message):
        global answer
        try:
            data = json.loads(message)
        except Exception as e:
            print("解析 spark 消息失败:", e)
            return
        header = data.get("header", {})
        code = header.get("code", -1)
        if code != 0:
            print("Spark 请求错误:", data)
            ws.close()
            return
        payload = data.get("payload", {})
        choices = payload.get("choices", {})
        part = ""
        try:
            part = choices["text"][0].get("content", "")
        except Exception:
            try:
                part = choices.get("text", "")
            except:
                part = ""
        answer += part
        status = choices.get("status", None)
        if status == 2:
            ws.close()

    def on_error(ws, error):
        print("### Spark error:", error)

    def on_close(ws, *args):
        pass

    def on_open(ws):
        if isinstance(messages_or_text, list):
            payload = {"message": {"text": messages_or_text}}
        else:
            payload = {"message": {"text": [{"role":"user","content": messages_or_text}]}}
        data = {
            "header": {"app_id": SPARK_APPID, "uid": "1234"},
            "parameter": {"chat": {"domain": SPARK_DOMAIN, "temperature": 0.0, "max_tokens": 1024, "top_k": 1}},
            "payload": payload
        }
        ws.send(json.dumps(data))

    host = urlparse(SPARK_URL).netloc
    path = urlparse(SPARK_URL).path
    now = datetime.now()
    date = format_date_time(time.mktime(now.timetuple()))
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    signature_sha = base64.b64encode(
        hmac.new(SPARK_API_SECRET.encode('utf-8'), signature_origin.encode('utf-8'), digestmod=hashlib.sha256).digest()
    ).decode()
    authorization_origin = (
        f'api_key="{SPARK_API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
    )
    authorization = base64.b64encode(authorization_origin.encode()).decode()
    v = {"authorization": authorization, "date": date, "host": host}
    wsUrl = SPARK_URL + "?" + urlencode(v)

    ws = websocket.WebSocketApp(wsUrl, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    return answer.strip()

# -------------------- 日期解析与策略 --------------------
def parse_date_string(s):
    if not s:
        return None
    s = s.strip()
    m = re.match(r"^(\d{4})[.\-](\d{1,2})[.\-](\d{1,2})$", s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime(year=y, month=mo, day=d).date()
    except:
        return None

def compute_due_from_data_only(today, name):
    lower_name = name.lower()
    for key in DATA_KEYS_SORTED:
        if key in lower_name or lower_name in key:
            days = DATA_MAPPING.get(key)
            if isinstance(days, int):
                due = today + timedelta(days=days)
                return due.strftime("%Y.%m.%d")
    return None

def heuristic_default_days(name):
    name_l = name.lower()
    heuristics = {
        "面包": 3, "吐司":3, "牛奶":7, "鸡蛋":14, "蔬菜":5, "水果":7, "肉":3, "鱼":1,
    }
    for k, v in heuristics.items():
        if k in name_l:
            return v
    return 7

def compute_fallback_due_date(today, name):
    due = compute_due_from_data_only(today, name)
    if due:
        return due
    days = heuristic_default_days(name)
    due = today + timedelta(days=days)
    print(f"[WARN] 未在 data.txt 中找到 '{name}' 的保质期，使用启发式天数 {days} 天作为回退。建议将该项加入 data.txt。")
    return due.strftime("%Y.%m.%d")

# -------------------- 本地生成回复 --------------------
def local_format_reply(expired, near_expired, recommend_list):
    lines = []
    for name in expired:
        lines.append(f"{name}已过期")
    for item in near_expired:
        lines.append(f"{item['name']}还有{item['days_left']}天过期")
    if recommend_list:
        lines.append("根据临期食材推荐的菜品有：" + ",".join(recommend_list))
    else:
        lines.append("根据临期食材推荐的菜品有：番茄炒蛋, 红烧肉, 清炒时蔬")
    lines.append("祝您生活愉快")
    return "\n".join(lines)

def recommend_dishes_from_items(items, max_n=3):
    mapping = {
        "鸡蛋": ["番茄炒蛋", "煎蛋", "蛋炒饭"],
        "面包": ["法式吐司", "面包布丁", "烤面包"],
        "西红柿": ["番茄炒蛋", "西红柿炒牛腩", "西红柿汤"],
        "牛肉": ["红烧牛肉", "牛肉炒面", "黑椒牛排"],
        "豆腐": ["麻婆豆腐", "家常豆腐", "鱼香豆腐"],
        "鱼": ["清蒸鱼", "糖醋鱼", "鱼香茄子"],
        "蔬菜": ["清炒时蔬", "蒜蓉油麦菜", "蚝油生菜"]
    }
    res = []
    for it in items:
        name = it.get("name","")
        for k, dishes in mapping.items():
            if k in name and len(res) < max_n:
                for d in dishes:
                    if d not in res:
                        res.append(d)
                    if len(res) >= max_n:
                        break
        if len(res) >= max_n:
            break
    common = ["番茄炒蛋", "红烧肉", "清炒时蔬", "鱼香肉丝", "宫保鸡丁"]
    i = 0
    while len(res) < max_n and i < len(common):
        if common[i] not in res:
            res.append(common[i])
        i += 1
    return res[:max_n]

# -------------------- 解析 history 并计算 days_left --------------------
def compute_status_from_history():
    today = datetime.now().date()
    expired = []
    near_expired = []
    all_items = []
    if not os.path.exists(HISTORY_FILE):
        return expired, near_expired, all_items
    lines = [l.strip() for l in open(HISTORY_FILE, "r", encoding="utf-8") if l.strip()]
    for l in lines:
        parts = l.split()
        if len(parts) < 3:
            continue
        due_str = parts[0]
        try:
            qty = int(parts[1])
        except:
            qty = 1
        name = " ".join(parts[2:])
        due_date = parse_date_string(due_str)
        if not due_date:
            continue
        days_left = (due_date - today).days
        if days_left < 0:
            expired.append(name)
        else:
            all_items.append({"name": name, "days_left": days_left, "qty": qty})
            if 0 < days_left <= 3:
                near_expired.append({"name": name, "days_left": days_left, "qty": qty})
    return expired, near_expired, all_items

# -------------------- 操作与回复（继续） --------------------
SYSTEM_PROMPT = (
    "你将收到结构化 JSON 数据，其中所有剩余天数均由程序正确计算。\n"
    "⚠️ 你禁止进行任何与日期、天数、保质期相关的计算。\n"
    "⚠️ 不得修改提供的天数，也不得自行推断时间。\n\n"
    "你只需根据 JSON 内容执行三件事：\n"
    "1) 输出所有已过期项，每行格式：xx已过期\n"
    "2) 输出所有保质期小于4天的项（JSON 中给出 days_left），如果没有就说食材都很新鲜，输出格式：xx还有X天过期（X 为 JSON 的 days_left）\n"
    "3) 根据“未过期的食材名称”（JSON 中的 near_expired 列表）推荐 3 道美味知名的中餐，（逗号分隔即可）\n\n"
    "禁止输出未提供的天数。禁止修改食品名称。禁止补全未提供的数据。最后以一句祝福结尾。"
)

def operate_and_reply(text, action_type):
    today_date = datetime.now().date()

    # ------------------ ADD ------------------
    if action_type == "add":
        qty, name = extract_number_and_name(text)
        if qty == 'ALL':
            qty = 1  # 放入时无法理解全部，默认 1
        due_from_data = compute_due_from_data_only(today_date, name)
        model_due = None

        if not due_from_data:
            try:
                prompt = (
                    f"CURRENT_DATE_IS: {today_date.strftime('%Y.%m.%d')}\n"
                    f"仅使用该当前日期作为参考，不要引用或假设其他任何日期。\n"
                    f"用户放入的食材为：\"{name}\"，数量：{qty}\n"
                    "请根据常识和 data.txt（如果有）推断该食材的到期日。\n"
                    "严格要求输出：只输出一行，且内容必须是 YYYY.MM.DD 或 UNKNOWN。\n"
                    "如果推断出的日期早于当前日期，必须输出 UNKNOWN。\n"
                    "不要输出任何解释、标点或多余文本，只输出 YYYY.MM.DD 或 UNKNOWN。\n"
                )
                model_out = call_spark_model(prompt).strip()
                parsed = parse_date_string(model_out)
                if parsed and parsed >= today_date:
                    model_due = parsed.strftime("%Y.%m.%d")
            except Exception as e:
                model_due = None

        if due_from_data:
            due_date = due_from_data
        elif model_due:
            due_date = model_due
        else:
            due_date = compute_fallback_due_date(today_date, name)

        # 写入 history
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{due_date} {qty} {name}\n")
        print(f"记录：{due_date} {qty} {name} （来源：{'data.txt' if due_from_data else 'model' if model_due else 'fallback'}）")

    # ------------------ DELETE ------------------
    if action_type == "delete":
        qty, name = extract_number_and_name(text)
        if not os.path.exists(HISTORY_FILE):
            print("历史文件不存在，无法删除。")
            return

        lines = [l.strip() for l in open(HISTORY_FILE, "r", encoding="utf-8") if l.strip()]
        items = []
        for l in lines:
            parts = l.split()
            if len(parts) < 3:
                continue
            due_str = parts[0]
            try:
                count = int(parts[1])
            except:
                count = 1
            item_name = " ".join(parts[2:])
            items.append([due_str, count, item_name])

        new_items = []
        remaining = qty
        delete_all = qty == 'ALL'

        # 遍历 items
        for item in items:
            if (name in item[2] or item[2] in name):
                if delete_all:
                    # 删除所有匹配的
                    continue
                if remaining > 0:
                    if item[1] > remaining:
                        item[1] -= remaining
                        remaining = 0
                        new_items.append(item)
                    else:
                        remaining -= item[1]
                        continue
                else:
                    new_items.append(item)
            else:
                new_items.append(item)

        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for item in new_items:
                f.write(f"{item[0]} {item[1]} {item[2]}\n")
        if delete_all:
            print(f"已删除所有 '{name}'")
        else:
            print(f"尝试扣除 {qty} 个/份 '{name}'，未扣除数量：{remaining}")

    # ------------------ QUERY ------------------
    expired, near_expired, all_items = compute_status_from_history()
    payload = {
        "current_date": today_date.strftime("%Y.%m.%d"),
        "expired": expired,
        "near_expired": [{"name": it["name"], "days_left": it["days_left"]} for it in near_expired],
        "all_items": [{"name": it["name"], "days_left": it["days_left"], "qty": it.get("qty", 1)} for it in all_items]
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
    ]

    try:
        model_reply = call_spark_model(messages)
        if not model_reply.strip():
            raise ValueError("模型返回空，使用本地生成")
        print("小冰：")
        print(model_reply)
    except Exception as e:
        print("[WARN] 模型生成失败或返回空，使用本地格式化输出。原因：", e)
        recommend = recommend_dishes_from_items(near_expired, max_n=3)
        local_reply = local_format_reply(expired, near_expired, recommend)
        print("")
        print(local_reply)

# -------------------- 主循环 --------------------
def run_talk():
    print("等待唤醒")
    delete_triggers = [
        "拿出来", "拿出", "拿出来了", "拿出了", "拿走", "拿走了", "拿掉了",
        "取走", "取走了", "取出", "取出来", "取出来了",
        "移除", "移除了",
        "吃了", "吃掉", "吃完了",
        "用掉了", "用掉", "用完了", "用了",
        "扔掉了", "倒掉了", "扔了"
    ]
    add_triggers = [
        "放入", "放进", "放了", "买了", "存入", "存了",
        "加入", "添了", "放进去", "放入了", "放进了", "加入了"
    ]

    while True:
        try:
            record_sound(AUDIO_FILE, 2)
            msg = speech_to_text(AUDIO_FILE) or ""
        except Exception as e:
            print("录音/识别错误：", e)
            msg = ""

        if "你好" in msg:
            print("我在，请问有何吩咐？")
            try:
                record_sound(AUDIO_FILE, 4)
                text = speech_to_text(AUDIO_FILE) or ""
            except Exception as e:
                print("识别失败：", e)
                text = ""
            print("识别结果：", text)

            if any(w in text for w in add_triggers):
                operate_and_reply(text, "add")
            elif any(w in text for w in delete_triggers):
                operate_and_reply(text, "delete")
            else:
                operate_and_reply(text, "query")
            print("---------------------------------------------------")
if __name__ == '__main__':
    DATA_MAPPING, DATA_KEYS_SORTED = load_datafile_mapping()
    run_talk()

