import api
import os
from datetime import datetime

appid = "317626fb"
api_secret = "YmZkYTkzY2ViZWY0MTc2ZDZjNWQzNWRl"
api_key = "834afce2724eec249e4dc21d0ca3e8dc"
domain = "4.0Ultra"
Spark_url = "wss://spark-api.xf-yun.com/v4.0/chat"

text = []


def getText(role, content):
    return {"role": role, "content": content}


def getlength(text_list):
    return sum(len(t["content"]) for t in text_list)


def checklen(text_list):
    while getlength(text_list) > 8000:
        del text_list[0]
    return text_list


def Api_Run(input_text):
    try:
        # 获取当前日期
        current_date = datetime.now().strftime("%Y-%m-%d")  # 例如 "2025-11-11"

        # 从 history.txt 读取历史语音识别内容
        history_context = ""
        if os.path.exists("history.txt"):
            with open("history.txt", "r", encoding="utf-8") as f:
                history_context = f.read().strip()

        # 将历史语音识别记录作为提示词，并加上当前日期
        if history_context:
            prompt = (
                f"你是一个冰箱智能助手，能够根据用户的历史数据判断冰箱里有什么，"
                f"并根据当前日期 {current_date} 及存入时间大概分析剩余保质期（存入的时候时默认最新鲜）并根据剩余保质期最短的食材进行简要食谱推荐（不需要告诉做菜步骤，只告诉菜谱名字和需要食材就好）：\n"
                f"{history_context}\n用户现在说：{input_text}"
            )
        else:
            prompt = f"你是一个冰箱智能助手，今天是 {current_date}，请根据用户问题简要回答，但要涵盖所有要求：{input_text}"

        question = checklen([getText("user", prompt)])
        # print(question)

        api.answer = ""
        print("星火:", end="")
        api.main(appid, api_key, api_secret, Spark_url, domain, question)

        output_text = api.answer.strip()
        return output_text

    except Exception as e:
        print(e)
        return "抱歉，我出错了。"
