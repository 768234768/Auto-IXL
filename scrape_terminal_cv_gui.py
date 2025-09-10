import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox
import threading
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import time
from selenium.common.exceptions import ElementNotInteractableException, StaleElementReferenceException

class ScrapeTerminalCVGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Auto IXL Scraper GUI")
        self.root.geometry("800x600")
        self.api_key = tk.StringVar()
        self.start_url = tk.StringVar()
        self.auto_click = tk.BooleanVar(value=True)
        self.text_widget = None
        self.driver = None
        self.last_text = None
        self.setup_gui()

    def setup_gui(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10, fill='x')
        # First row: API key and URL
        tk.Label(frame, text="DeepSeek API Key:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.api_key, width=40, show='*').grid(row=0, column=1, padx=5)
        tk.Label(frame, text="Start URL:").grid(row=0, column=2, padx=(20,0), sticky='w')
        tk.Entry(frame, textvariable=self.start_url, width=40).grid(row=0, column=3, padx=5)
        # Second row: Auto-click checkbox, Stop button, Start button
        tk.Checkbutton(frame, text="Enable Auto-Clicking", variable=self.auto_click, onvalue=True, offvalue=False).grid(row=1, column=0, columnspan=1, sticky='w', pady=10)
        tk.Button(frame, text="Stop", command=self.stop_browser, width=10, height=2, bg='#F44336', fg='white', font=('Arial', 12, 'bold')).grid(row=1, column=1, pady=10, padx=(0, 10))
        tk.Button(frame, text="Start", command=self.start_all, width=15, height=2, bg='#4CAF50', fg='white', font=('Arial', 12, 'bold')).grid(row=1, column=2, columnspan=2, pady=10)
        # Expand columns for better layout
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)
        self.text_widget = ScrolledText(self.root, state='disabled', font=('Consolas', 10), height=25)
        self.text_widget.pack(expand=True, fill='both', padx=10, pady=10)
    def stop_browser(self):
        """Stops the current browser session properly."""
        if self.driver:
            try:
                self.driver.quit()
                self.update_terminal("[INFO] Browser session stopped.")
            except Exception as e:
                self.update_terminal(f"[ERROR] Failed to stop browser: {e}")
            self.driver = None
        else:
            self.update_terminal("[INFO] No browser session to stop.")

    def start_all(self):
        url = self.start_url.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a start URL.")
            return
        threading.Thread(target=self._start_all_thread, args=(url,), daemon=True).start()

    def _start_all_thread(self, url):
        self.update_terminal(f"[INFO] Starting browser for: {url}")
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
        try:
            service = EdgeService()
            options = webdriver.EdgeOptions()
            options.add_argument('disable-gpu')
            self.driver = webdriver.Edge(service=service, options=options)
            self.driver.get(url)
            self.update_terminal(f"浏览器已打开: {url}\n" + "-"*50)
            self.last_text = None
            while True:
                time.sleep(3)
                html = self.driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                if text != self.last_text:
                    self.update_terminal(f"\n页面内容已更新:\n" + "-"*50)
                    feedback_h2 = soup.find('h2', class_='feedback-header correct')
                    if feedback_h2 and 'sorry, incorrect' in feedback_h2.get_text(strip=True).lower():
                        result = 'got it'
                        self.update_terminal("检测到<h2 class='feedback-header correct'>Sorry, incorrect...</h2>，自动输出 got it")
                    elif 'sorry, incorrect' in text.lower():
                        result = 'got it'
                        self.update_terminal("检测到'Sorry, incorrect'，自动输出 got it")
                    else:
                        result = self.get_deepseek_result(text)
                    self.update_terminal("DeepSeek API 响应:")
                    self.update_terminal(result)
                    if self.auto_click.get():
                        self.find_and_click_option(result)
                    self.last_text = text
        except KeyboardInterrupt:
            self.update_terminal("\n已停止抓取，关闭浏览器。")
            if self.driver:
                self.driver.quit()
        except Exception as e:
            self.update_terminal(f"发生错误: {str(e)}")
            if self.driver:
                self.driver.quit()

    def update_terminal(self, message):
        self.text_widget.config(state='normal')
        self.text_widget.insert('end', message + '\n')
        self.text_widget.see('end')
        self.text_widget.config(state='disabled')

    def get_deepseek_result(self, text):
        api_key = self.api_key.get().strip()
        if not api_key:
            self.update_terminal("[ERROR] DeepSeek API Key is required!")
            return ""
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
            self.update_terminal(f"DeepSeek API 请求失败: {str(e)}")
            return ""



    def find_and_click_option(self, option_text, max_retries=5, retry_delay=1):
        # If DeepSeek returns 'got it', search for and click the 'Got it' button
        if option_text.strip().lower() == 'got it':
            for attempt in range(max_retries):
                time.sleep(retry_delay)
                try:
                    gotit_xpath = "//button[contains(@class, 'crisp-button') and normalize-space(text())='Got it']"
                    gotit_buttons = self.driver.find_elements(By.XPATH, gotit_xpath)
                    for el in gotit_buttons:
                        try:
                            el.click()
                            self.update_terminal("已通过Selenium点击Got it按钮")
                            return True
                        except (ElementNotInteractableException, StaleElementReferenceException):
                            continue
                    self.update_terminal(f"未找到Got it按钮，重试 {attempt+1}/{max_retries}")
                except Exception as e:
                    self.update_terminal(f"查找Got it按钮时发生错误: {e}")
            self.update_terminal("多次重试后仍未找到Got it按钮。")
            return True
        # Specifically search for SelectableTile options and match the answer text inside their .rich-text span
        html = self.driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        for attempt in range(max_retries):
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            tiles = soup.find_all('div', class_='SelectableTile')
            clicked = False
            for tile in tiles:
                span = tile.find('span', class_='rich-text')
                if span and option_text.strip().lower() in span.get_text(strip=True).lower():
                    # Find the same tile in Selenium and click it
                    cts_id = tile.get('cts_id')
                    if cts_id:
                        xpath = f"//div[@class='SelectableTile TEXT centerAlignTileContent MULTIPLE_CHOICE natural' and @cts_id='{cts_id}']"
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for el in elements:
                            try:
                                el.click()
                                self.update_terminal(f"已通过HTML点击选项: {option_text}")
                                clicked = True
                                break
                            except (ElementNotInteractableException, StaleElementReferenceException):
                                continue
                    if clicked:
                        break
            if clicked:
                break
            else:
                self.update_terminal(f"未找到选项按钮，重试 {attempt+1}/{max_retries}")
                time.sleep(retry_delay)
        if not clicked:
            self.update_terminal("多次重试后仍未找到选项按钮。")
            return False

        # After clicking the option, directly use Selenium to find and click the submit button
        for attempt in range(max_retries):
            time.sleep(retry_delay)
            try:
                submit_xpath = "//button[contains(@class, 'crisp-button') and normalize-space(text())='Submit']"
                submit_buttons = self.driver.find_elements(By.XPATH, submit_xpath)
                for el in submit_buttons:
                    try:
                        el.click()
                        self.update_terminal("已通过Selenium点击Submit按钮")
                        return True
                    except (ElementNotInteractableException, StaleElementReferenceException):
                        continue
                self.update_terminal(f"未找到Submit按钮，重试 {attempt+1}/{max_retries}")
            except Exception as e:
                self.update_terminal(f"查找Submit按钮时发生错误: {e}")
        self.update_terminal("多次重试后仍未找到Submit按钮。")
        return True

if __name__ == "__main__":
    app = ScrapeTerminalCVGUI()
    app.root.mainloop()
