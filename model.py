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
        data_context = ""
        if os.path.exists("data.txt"):
            with open("data.txt", "r", encoding="utf-8") as f:
                data_context = f.read().strip()

        # 将历史语音识别记录作为提示词，并加上当前日期
        if history_context:
            prompt = (
                f"（不要输出所有带括号里面的内容）你是一个冰箱智能助手，能够根据读取到的history数据并严格按照以下模板回复，模板中的括号为提示你要说什么内容，千万不要生成\n"
                f"history里面的每一行是食材放入冰箱日期+数量+食材名称，放入日期默认是最新鲜的状态，你可以根据当前日期{current_date}，我冰箱里食材的存入日期{history_context}和常见食材保质期{data_context}判断食材剩余保质期以及是否过期\n"
                f"用户现在说：{input_text}"
                f"模板：根据现有食材，aaa还有b天过期（按照剩余保质期正序排序，aaa内容为剩余保质期不足3天的食材，b是对应的剩余保质期天数，需要把所有剩余保质期小于等于3天的都列出来，不要输出所有带括号里面的内容）\n，ccc已过期（如果有过期的才说这句话，没有过期的就不说，ccc为食材名称，不要输出所有带括号里面的内容）\n，根据临期食材推荐的菜品有xxx（根据剩余保质期最短的几个食材生成推荐中餐菜谱，给出菜品名称就行，不用给出做法，xxx的内容为推荐的菜谱名，不要输出所有带括号里面的内容）\n祝您生活愉快\n"
            )
        else:
            prompt = f"你是一个冰箱智能助手，今天是 {current_date}，请根据用户问题简要回答（几句话就好），但要涵盖所有要求：{input_text}"

        question = checklen([getText("user", prompt)])
        # print(question)

        api.answer = ""
        print("小冰:", end="")
        api.main(appid, api_key, api_secret, Spark_url, domain, question)

        output_text = api.answer.strip()
        return output_text

    except Exception as e:
        print(e)
        return "抱歉，我出错了。"
