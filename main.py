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
LOGIN_URL = "https://console.altr.cc/sign-in"
# ===========================================

def run_auto_claim():
    print(">>> [启动] 正在初始化 GitHub Actions 环境...")
    
    if not USER_EMAIL or not USER_PASSWORD:
        print(">>> [错误] 未检测到账号或密码，请检查 GitHub Secrets 设置！")
        return

    # --- 浏览器配置 (关键修改) ---
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    
    # 1. 伪造 User-Agent (伪装成普通 Windows 电脑)
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 2. 移除 "自动化控制" 标记 (防止被网站 JS 检测到)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 执行 CDP 命令，彻底隐藏 webdriver 属性
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    try:
        print(f">>> [登录] 访问页面: {LOGIN_URL}")
        driver.get(LOGIN_URL)

        # --- 智能判断逻辑 ---
        # 我们不直接死等邮箱输入框，因为可能已经进去了
        print(">>> [检测] 正在判断页面状态...")
        
        try:
            # 尝试 1: 寻找邮箱输入框 (正常流程)
            email_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
            )
            print(">>> [登录] 发现登录表单，开始登录...")
            email_input.clear()
            email_input.send_keys(USER_EMAIL)

            password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
            password_input.send_keys(USER_PASSWORD)

            # 寻找提交按钮
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            driver.execute_script("arguments[0].click();", submit_btn) # 强制点击
            print(">>> [登录] 提交完成，等待跳转...")
            time.sleep(5) # 给一点反应时间

        except Exception:
            # 如果找不到输入框，检查是否已经登录成功 (比如因为 Cookie 或者网站允许 Guest 访问)
            print(">>> [跳过] 未找到登录框 (可能已登录或页面结构改变)，尝试直接寻找 Rewards 链接...")
            # 这里不抛出错误，继续往下走，看看能不能找到 Rewards

        # --- 跳转与签到 ---
        # 无论刚才是否登录成功，我们都尝试去找 Rewards 链接
        print(">>> [导航] 寻找 Rewards 入口...")
        
        # 使用更宽松的等待时间
        rewards_link = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//a[@href='/rewards']"))
        )
        print(">>> [导航] 找到链接，进入 Rewards 页面...")
        driver.execute_script("arguments[0].click();", rewards_link)

        print(">>> [签到] 检查按钮状态...")
        # 等待签到按钮
        claim_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.w-full"))
        )

        btn_text = claim_button.text
        is_disabled = claim_button.get_attribute("disabled")
        print(f">>> [状态] 按钮文字: '{btn_text}'")

        if "Claimed today" in btn_text or is_disabled:
            print(">>> [结果] ✅ 今天已经签到过了。")
        else:
            print(">>> [动作] 点击签到...")
            driver.execute_script("arguments[0].click();", claim_button)
            time.sleep(5)
            print(">>> [结果] ✅ 签到动作完成。")

    except Exception as e:
        print(f">>> [错误] 依然失败: {e}")
        # 如果再次失败，打印当前页面 body 的文本，看看显示了什么文字
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text[:500]
            print(f">>> [调试] 页面当前文字内容: {body_text}")
        except:
            pass

    finally:
        print(">>> [结束] 清理资源...")
        driver.quit()

if __name__ == "__main__":
    run_auto_claim()
