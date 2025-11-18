# -*- coding:utf-8 -*-
"""
# 1.先进行语音唤醒
# 2.语音助手进行应答反馈
# 3.用户语音咨询，语音需要转为文本
# 4.文本告诉助手，助手调用许飞大模型
# 5.获取讯飞大模型的结果
# 6.文本转为语音反馈
"""
from voice import Run_Voice
import model
import win32com.client
import pyaudio
import wave
from aip import AipSpeech
import os
import datetime
import re

class Wake_Up:

    def __init__(self,APP_ID,API_KEY,SECRET_KEY,file_path):
        self.APP_ID = APP_ID
        self.API_KEY = API_KEY
        self.SECRET_KEY = SECRET_KEY
        self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
        self.file_path = file_path

    def record_sound(self,x):
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS = x
        WAVE_OUTPUT_FILENAME = self.file_path
        pau = pyaudio.PyAudio()
        stream = pau.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK, )
        frames = []

        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pau.terminate()
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pau.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

    def voice2text(self):
        client = AipSpeech(self.APP_ID, self.API_KEY, self.SECRET_KEY)
        ret = client.asr(self.get_data(), 'pcm', 16000, {'dev_pid': 1536}, )
        if ret['err_msg'] == 'recognition error.':
            return ''
        else:
            return ret['result']

    def get_data(self):
        with open(self.file_path, 'rb') as fp:
            return fp.read()

    def del_file(self):
        file_name = self.file_path
        try:
            os.remove(file_name)
            f = open(file_name, mode="w")
            f.close()
        except FileNotFoundError:
            print(f"{file_name} not found")


def delete_ingredient_from_history(ingredient, number=1):
    """按数量删除食材，支持多种量词和中文数字"""
    try:
        with open("history.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        num_map = {
            # 中文数字
            "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "一个": 1, "两个": 2, "三个": 3, "四个": 4, "五个": 5, "六个": 6, "七个": 7, "八个": 8, "九个": 9, "十个": 10,
            "一盒": 1, "二盒": 2, "三盒": 3, "四盒": 4, "五盒": 5, "六盒": 6, "七盒": 7, "八盒": 8, "九盒": 9, "十盒": 10,
            "一包": 1, "二包": 2, "三包": 3, "四包": 4, "五包": 5, "六包": 6, "七包": 7, "八包": 8, "九包": 9, "十包": 10,
            "一捆": 1, "二捆": 2, "三捆": 3, "四捆": 4, "五捆": 5, "六捆": 6, "七捆": 7, "八捆": 8, "九捆": 9, "十捆": 10,
            "一袋": 1, "二袋": 2, "三袋": 3, "四袋": 4, "五袋": 5, "六袋": 6, "七袋": 7, "八袋": 8, "九袋": 9, "十袋": 10,
            "一斤": 1, "二斤": 2, "三斤": 3, "四斤": 4, "五斤": 5, "六斤": 6, "七斤": 7, "八斤": 8, "九斤": 9, "十斤": 10,
            "一块": 1, "二块": 2, "三块": 3, "四块": 4, "五块": 5, "六块": 6, "七块": 7, "八块": 8, "九块": 9,"十块": 10,
            "一棵": 1, "二棵": 2, "三棵": 3, "四棵": 4, "五棵": 5, "六棵": 6, "七棵": 7, "八棵": 8, "九棵": 9,"十棵": 10,
            "一根": 1, "二根": 2, "三根": 3, "四根": 4, "五根": 5, "六根": 6, "七根": 7, "八根": 8, "九根": 9,"十根": 10,
            "一头": 1, "二头": 2, "三头": 3, "四头": 4, "五头": 5, "六头": 6, "七头": 7, "八头": 8, "九头": 9,"十头": 10,
            "一条": 1, "二条": 2, "三条": 3, "四条": 4, "五条": 5, "六条": 6, "七条": 7, "八条": 8, "九条": 9,"十条": 10,
            "一只": 1, "二只": 2, "三只": 3, "四只": 4, "五只": 5, "六只": 6, "七只": 7, "八只": 8, "九只": 9,"十只": 10,
            "一罐": 1, "二罐": 2, "三罐": 3, "四罐": 4, "五罐": 5, "六罐": 6, "七罐": 7, "八罐": 8, "九罐": 9,"十罐": 10,
            "一瓶": 1, "二瓶": 2, "三瓶": 3, "四瓶": 4, "五瓶": 5, "六瓶": 6, "七瓶": 7, "八瓶": 8, "九瓶": 9,"十瓶": 10
        }

        for line in lines:
            line_strip = line.strip()
            if ingredient in line_strip:
                pattern = r"(\d+|{})?\s*(个|盒|包|捆|袋|斤)?\s*{}".format("|".join(num_map.keys()), re.escape(ingredient))
                m = re.search(pattern, line_strip)
                if m:
                    qty_str = m.group(1)
                    current_qty = int(qty_str) if qty_str and qty_str.isdigit() else num_map.get(qty_str, 1)
                    remaining = current_qty - number
                    if remaining > 0:
                        unit = m.group(2) if m.group(2)   else ""
                        new_line = re.sub(pattern, f"{remaining}{unit}{ingredient}", line_strip)
                        new_lines.append(new_line)
                    continue
            new_lines.append(line_strip)

        with open("history.txt", "w", encoding="utf-8") as f:
            for l in new_lines:
                f.write(l + "\n")

    except FileNotFoundError:
        print("history.txt 不存在")


def Run_Talk(APP_ID,API_KEY,SECRET_KEY,file_path):

    output_pcm = './data/demo.pcm'
    output_wav = './data/demo.wav'
    wk = Wake_Up(APP_ID,API_KEY,SECRET_KEY,file_path)
    x = 1
    print("等待唤醒")
    while x:
        wk.record_sound(2)
        chat_message = wk.voice2text()
        print(chat_message)
        if len(chat_message) > 0 and chat_message[0] == '你好':
            wk.del_file()
            print('我在，请问有何吩咐')
            wk.record_sound(4)
            chat_message = wk.voice2text()
            if len(chat_message) > 0:
                text = chat_message[0]

                delete_keywords = ["拿出来", "拿出", "取出", "移除", "没有了", "没了", "拿掉","拿","拿出了","拿出来了", "取出了", "移除了"]
                if any(k in text for k in delete_keywords):
                    pattern = r"(?:我|把|从冰箱)?\s*(?:拿出了|拿出来了|取出了|移除了|没有了|没了|拿掉了|拿了|取了|拿出|拿出来|取出|移除)\s*(?P<number>(\d+|{})?)\s*(?P<ingredient>.+?)\s*(?:[，。！!.]|$)".format(
                        "|".join([
                            # 所有中文数字 + 个/盒/包/捆/袋/斤组合
                            "一","二","三","四","五","六","七","八","九","十",
                            "一个","两个","三个","四个","五个","六个","七个","八个","九个","十个",
                            "一盒","二盒","三盒","四盒","五盒","六盒","七盒","八盒","九盒","十盒",
                            "一包","二包","三包","四包","五包","六包","七包","八包","九包","十包",
                            "一捆","二捆","三捆","四捆","五捆","六捆","七捆","八捆","九捆","十捆",
                            "一袋","二袋","三袋","四袋","五袋","六袋","七袋","八袋","九袋","十袋",
                            "一斤","二斤","三斤","四斤","五斤","六斤","七斤","八斤","九斤","十斤",
                            "一块","二块","三块","四块","五块","六块","七块","八块","九块","十块",
                            "一棵","二棵","三棵","四棵","五棵","六棵","七棵","八棵","九棵","十棵",
                            "一根","二根","三根","四根","五根","六根","七根","八根","九根","十根",
                            "一头","二头","三头","四头","五头","六头","七头","八头","九头","十头",
                            "一条","二条","三条","四条","五条","六条","七条","八条","九条","十条",
                            "一只","二只","三只","四只","五只","六只","七只","八只","九只","十只",
                            "一罐","二罐","三罐","四罐","五罐","六罐","七罐","八罐","九罐","十罐",
                            "一瓶","二瓶","三瓶","四瓶","五瓶","六瓶","七瓶","八瓶","九瓶","十瓶"

                        ])
                    )
                    match = re.search(pattern, text)
                    if match:
                        ingredient = match.group("ingredient").strip()
                        number_str = match.group("number")
                        num_map = {
                            "一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
                            "一个":1,"两个":2,"三个":3,"四个":4,"五个":5,"六个":6,"七个":7,"八个":8,"九个":9,"十个":10,
                            "一盒":1,"二盒":2,"三盒":3,"四盒":4,"五盒":5,"六盒":6,"七盒":7,"八盒":8,"九盒":9,"十盒":10,
                            "一包":1,"二包":2,"三包":3,"四包":4,"五包":5,"六包":6,"七包":7,"八包":8,"九包":9,"十包":10,
                            "一捆":1,"二捆":2,"三捆":3,"四捆":4,"五捆":5,"六捆":6,"七捆":7,"八捆":8,"九捆":9,"十捆":10,
                            "一袋":1,"二袋":2,"三袋":3,"四袋":4,"五袋":5,"六袋":6,"七袋":7,"八袋":8,"九袋":9,"十袋":10,
                            "一斤":1,"二斤":2,"三斤":3,"四斤":4,"五斤":5,"六斤":6,"七斤":7,"八斤":8,"九斤":9,"十斤":10,
                            "一块":1,"二块":2,"三块":3,"四块":4,"五块":5,"六块":6,"七块":7,"八块":8,"九块":9,"十块":10,
                            "一棵":1,"二棵":2,"三棵":3,"四棵":4,"五棵":5,"六棵":6,"七棵":7,"八棵":8,"九棵":9,"十棵":10,
                            "一根":1,"二根":2,"三根":3,"四根":4,"五根":5,"六根":6,"七根":7,"八根":8,"九根":9,"十根":10,
                            "一头":1,"二头":2,"三头":3,"四头":4,"五头":5,"六头":6,"七头":7,"八头":8,"九头":9,"十头":10,
                            "一条":1,"二条":2,"三条":3,"四条":4,"五条":5,"六条":6,"七条":7,"八条":8,"九条":9,"十条":10,
                            "一只":1,"二只":2,"三只":3,"四只":4,"五只":5,"六只":6,"七只":7,"八只":8,"九只":9,"十只":10,
                            "一罐":1,"二罐":2,"三罐":3,"四罐":4,"五罐":5,"六罐":6,"七罐":7,"八罐":8,"九罐":9,"十罐":10,
                            "一瓶":1,"二瓶":2,"三瓶":3,"四瓶":4,"五瓶":5,"六瓶":6,"七瓶":7,"八瓶":8,"九瓶":9,"十瓶":10

                        }
                        number = int(number_str) if number_str and number_str.isdigit() else num_map.get(number_str, 1)
                        delete_ingredient_from_history(ingredient, number)
                        print("已删除食材：", ingredient, number)
                    else:
                        print("未识别具体食材，无法删除")
                    return

                add_keywords = ["放进", "买", "放入", "放", "存","存入","拿进","拿入","放进了", "买了", "放入了", "放了", "存了","存入了","拿进了","拿入了"]
                if any(k in text for k in add_keywords):
                    today = datetime.datetime.now().strftime("%Y.%m.%d")
                    with open("history.txt", "a", encoding="utf-8") as f:
                        f.write(f"{today} {text}\n")
                    print("已写入食材信息：", today, text)

            print(chat_message)
            if len(chat_message) > 0:
                Input = chat_message[0]
                output = model.Api_Run(Input)
                x=0
            break
        else:
            continue


if __name__ == '__main__':
    file_path = "./data/chat-audio.wav"
    APP_ID = '120707525'
    API_KEY = 'rZVAwVCohhATnbVZRhkhr5c5'
    SECRET_KEY = '9uw06M6IgTL5woUE3QuS6Wzqm5EXZeq4'
    Run_Talk(APP_ID,API_KEY,SECRET_KEY,file_path)
