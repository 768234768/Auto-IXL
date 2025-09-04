from openai import OpenAI

def get_deepseek_result(text):
    """
    使用 OpenAI SDK 访问 DeepSeek API。
    """
    api_key = "Your API"  # 替换为你的 DeepSeek API Key
    base_url = "https://api.deepseek.com"
    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a english expert and you will extract the question and answer from the following text and only give the answer."},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"DeepSeek API 请求失败: {str(e)}"

from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time

# 输入你要抓取的URL
url = "https://www.ixl.com/ela/grade-10/identify-the-narrative-point-of-view"  # 修改为你想抓取的网址

# 添加http://前缀如果不存在
if not url.startswith(('http://', 'https://')):
    url = 'http://' + url


try:
    # 启动Edge浏览器（可见窗口，非headless）
    service = EdgeService()
    options = webdriver.EdgeOptions()
    options.add_argument('disable-gpu')
    driver = webdriver.Edge(service=service, options=options)
    driver.get(url)
    print(f"浏览器已打开: {url}\n" + "-"*50)
    last_text = None
    while True:
        time.sleep(3)  # 每3秒抓取一次
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        if text != last_text:
            print(f"\n页面内容已更新:\n" + "-"*50)
            result = get_deepseek_result(text)
            print("DeepSeek API 响应:")
            print(result)
            last_text = text
except KeyboardInterrupt:
    print("\n已停止抓取，关闭浏览器。")
    driver.quit()
except Exception as e:
    print(f"发生错误: {str(e)}")

