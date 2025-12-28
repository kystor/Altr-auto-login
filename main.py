import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ================= 配置区域 =================
USER_EMAIL = os.environ.get("ALTR_EMAIL")
USER_PASSWORD = os.environ.get("ALTR_PASSWORD")
LOGIN_URL = "https://console.altr.cc/login" 
# ===========================================

def run_auto_claim():
    print(">>> [启动] V6 通用适配版启动...")
    
    if not USER_EMAIL or not USER_PASSWORD:
        print(">>> [错误] 环境变量未设置！")
        return

    # --- 浏览器配置 (保持之前的成功配置) ---
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 注入防检测 JS
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
        """
    })

    try:
        # --- 1. 登录阶段 ---
        print(f">>> [访问] 打开登录页: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(5) # 等待页面元素加载

        print(">>> [登录] 正在定位输入框...")
        
        # 核心修改：获取所有 input 标签，按顺序填入
        # 因为日志显示页面只有2个输入框，第1个是账号(text)，第2个是密码(password)
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        if len(inputs) < 2:
            print(f">>> [错误] 页面输入框数量不足 (找到 {len(inputs)} 个)，可能被拦截。")
            print(f">>> [调试] 页面内容: {driver.find_element(By.TAG_NAME, 'body').text[:200]}")
            return

        # 第一个框填账号 (无论它是 type='text' 还是 'email')
        email_field = inputs[0]
        # 第二个框填密码
        password_field = inputs[1]

        print(f">>> [登录] 找到输入框 (Type: {email_field.get_attribute('type')})，正在输入账号...")
        email_field.clear()
        email_field.send_keys(USER_EMAIL)
        time.sleep(0.5)

        print(">>> [登录] 正在输入密码...")
        password_field.clear()
        password_field.send_keys(USER_PASSWORD)
        time.sleep(0.5)

        # 点击登录按钮
        # 寻找 type='submit' 或者包含 'Login' 文字的按钮
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except:
            # 备选方案：通过文字找按钮
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            
        print(">>> [登录] 点击提交按钮...")
        driver.execute_script("arguments[0].click();", submit_btn)

        # --- 2. 验证登录 ---
        print(">>> [验证] 等待跳转和积分显示...")
        try:
            # 等待 URL 变化 (不再包含 login) 或者出现积分
            WebDriverWait(driver, 15).until(
                lambda d: "login" not in d.current_url or len(d.find_elements(By.XPATH, "//*[contains(text(), 'credits')]")) > 0
            )
            
            # 再次确认积分是否存在
            credits = driver.find_elements(By.XPATH, "//*[contains(text(), 'credits')]")
            if credits:
                print(f">>> [成功] 登录成功！检测到积分: {credits[0].text}")
            else:
                print(">>> [警告] 未检测到积分，但 URL 已跳转，尝试继续...")

        except Exception as e:
            print(">>> [警告] 登录验证超时，可能已登录但未检测到元素，强制继续...")

        # --- 3. 签到阶段 ---
        print(">>> [导航] 前往 Rewards 页面...")
        driver.get("https://console.altr.cc/rewards")
        time.sleep(5)

        try:
            # 寻找主要按钮
            claim_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.w-full"))
            )
            btn_text = claim_button.text
            print(f">>> [状态] Rewards 按钮文字: [{btn_text}]")

            if "Login" in btn_text:
                print(">>> [失败] 严重错误：页面仍显示 Login，说明登录失败。")
            elif "Claimed today" in btn_text or claim_button.get_attribute("disabled"):
                print(">>> [结果] ✅ 今天已签到，任务完成。")
            else:
                print(">>> [动作] 点击签到...")
                driver.execute_script("arguments[0].click();", claim_button)
                time.sleep(3)
                print(">>> [结果] ✅ 签到指令已发送。")

        except Exception as e:
            print(f">>> [错误] 未能找到签到按钮: {e}")

    except Exception as e:
        print(f">>> [崩溃] 程序异常: {e}")
        # 如果出错，打印最后一点源码辅助
        try:
            print(f">>> [调试] 异常时页面内容: {driver.find_element(By.TAG_NAME, 'body').text[:500]}")
        except: pass

    finally:
        print(">>> [结束] 关闭浏览器")
        driver.quit()

if __name__ == "__main__":
    run_auto_claim()
