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
# 直接锁定登录页，不绕弯子
LOGIN_URL = "https://console.altr.cc/login" 
# ===========================================

def run_auto_claim():
    print(">>> [启动] 正在初始化 GitHub Actions 环境 (最终修正版 V4)...")
    
    if not USER_EMAIL or not USER_PASSWORD:
        print(">>> [错误] 未检测到账号或密码，请检查 GitHub Secrets 设置！")
        return

    # --- 浏览器配置 ---
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new") # 新版无头模式
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # 伪装成普通浏览器
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # CDP 注入：隐藏自动化特征
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.navigator.chrome = { runtime: {} };
        """
    })

    try:
        # --- 第一步：执行登录 ---
        print(f">>> [访问] 打开登录页: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # 1. 输入账号
        print(">>> [登录] 等待输入框...")
        email_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email']"))
        )
        email_input.clear()
        email_input.send_keys(USER_EMAIL)

        # 2. 输入密码
        password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        password_input.clear()
        password_input.send_keys(USER_PASSWORD)
        
        # 3. 点击登录
        # 你的截图显示按钮是白底黑字，通常可以用 type='submit' 定位
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        print(">>> [登录] 点击登录按钮...")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        # --- 第二步：验证登录结果 (核心修改) ---
        print(">>> [验证] 正在检查是否登录成功...")
        try:
            # 我们寻找右上角的积分元素，截图显示它包含 "credits"
            # 使用 contains 模糊匹配，防止数字变化导致找不到
            credits_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'credits')]"))
            )
            print(f">>> [成功] 登录成功！检测到积分信息: [{credits_element.text}]")
        except:
            # 如果等了20秒还没看到积分，说明登录挂了
            print(">>> [失败] 登录超时或失败：未找到积分显示。")
            print(f">>> [调试] 当前页面标题: {driver.title}")
            # 截图看一眼（在 Actions 里只能看日志，这里打印页面文字辅助）
            try:
                print(f">>> [调试] 页面包含文字: {driver.find_element(By.TAG_NAME, 'body').text[:100].replace(chr(10), ' ')}")
            except: pass
            driver.quit()
            return # 既然登录失败，直接结束，不再往下跑

        # --- 第三步：前往签到 ---
        print(">>> [导航] 前往 Rewards 页面...")
        driver.get("https://console.altr.cc/rewards")
        time.sleep(5) # 等待加载

        # 定位签到区域
        try:
            # 寻找那个大按钮
            claim_button = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button.w-full"))
            )
            
            btn_text = claim_button.text
            print(f">>> [状态] 按钮上的文字是: [{btn_text}]")

            # --- 核心判断逻辑 ---
            if "Login" in btn_text:
                # 如果按钮叫 Login，说明之前的登录验证是假的，或者 Session 丢了
                print(">>> [错误] 异常状态：页面显示为未登录 (Login 按钮)。任务终止。")
            
            elif "Claimed today" in btn_text:
                # 对应你的截图2：灰色按钮
                print(">>> [结果] ✅ 今天已经签到过了 (Claimed today)。")
            
            else:
                # 既不是 Login 也不是 Claimed today，那就是可以签到
                print(">>> [动作] 正在点击签到...")
                driver.execute_script("arguments[0].click();", claim_button)
                time.sleep(5)
                
                # 再次检查确认
                print(">>> [复查] 签到后检查按钮状态...")
                btn_text_new = claim_button.text
                if "Claimed today" in btn_text_new:
                    print(">>> [结果] ✅ 签到成功！")
                else:
                    print(f">>> [结果] ⚠️ 指令已发送，当前按钮文字: {btn_text_new}")

        except Exception as e:
            print(f">>> [错误] 无法找到签到按钮: {e}")

    except Exception as e:
        print(f">>> [崩溃] 脚本运行出错: {e}")

    finally:
        print(">>> [结束] 清理资源...")
        driver.quit()

if __name__ == "__main__":
    run_auto_claim()
