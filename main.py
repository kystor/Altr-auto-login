import time
import os
import re
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

def parse_credits(text):
    """提取文本中的数字，例如 '622.9 credits' -> 622.9"""
    try:
        # 移除 'credits', 逗号和空格
        clean_text = text.lower().replace('credits', '').replace(',', '').strip()
        return float(clean_text)
    except:
        return 0.0

def run_auto_claim():
    print(">>> [启动] Altr自动签到脚本")
    
    if not USER_EMAIL or not USER_PASSWORD:
        print(">>> [错误] 环境变量未设置！")
        return

    # --- 浏览器配置 ---
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
        # --- 1. 登录 (V6 成功逻辑) ---
        print(f">>> [访问] 打开登录页: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        time.sleep(5)

        print(">>> [登录] 定位输入框...")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        if len(inputs) < 2:
            print(">>> [错误] 输入框数量不足，登录页面加载异常。")
            return

        # 填入账号密码
        inputs[0].clear()
        inputs[0].send_keys(USER_EMAIL)
        time.sleep(0.5)
        inputs[1].clear()
        inputs[1].send_keys(USER_PASSWORD)
        time.sleep(0.5)

        # 提交
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except:
            submit_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
        
        driver.execute_script("arguments[0].click();", submit_btn)
        print(">>> [登录] 提交中...")

        # --- 2. 获取初始积分 ---
        print(">>> [验证] 等待登录并获取初始积分...")
        initial_balance = 0.0
        try:
            # 等待积分元素出现
            credits_element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'credits')]"))
            )
            raw_text = credits_element.text
            initial_balance = parse_credits(raw_text)
            print(f">>> [记录] 初始积分: {initial_balance}")
        except:
            print(">>> [警告] 登录可能失败或未找到积分，无法计算增量。")
            # 如果没找到积分，可能没登录成功，但这不影响尝试去点签到
        
        # --- 3. 执行签到 ---
        print(">>> [导航] 前往 Rewards 页面...")
        driver.get("https://console.altr.cc/rewards")
        time.sleep(5)

        try:
            # 【核心修改】不再找 button.w-full，而是找包含 "Claim" 文字的按钮
            # XPath 解释: 找一个 button，它的文本包含 Claim (不区分大小写通常难做，这里匹配标准写法)
            # 同时也匹配 "Claimed"
            print(">>> [搜索] 正在寻找包含 'Claim' 的按钮...")
            claim_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Claim')]")
            
            target_button = None
            # 过滤一下，防止找到页面顶部的导航栏
            for btn in claim_buttons:
                if btn.is_displayed():
                    target_button = btn
                    break
            
            if not target_button:
                # 备用方案：如果按钮叫 "Reward"
                claim_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Reward')]")
                for btn in claim_buttons:
                    if btn.is_displayed():
                        target_button = btn
                        break

            if target_button:
                btn_text = target_button.text
                print(f">>> [状态] 找到按钮，文字内容: [{btn_text}]")

                if "Claimed" in btn_text or target_button.get_attribute("disabled"):
                    print(f">>> [结果] ⚪ 今天已经签到过了 (检测到: {btn_text})。")
                    print(f">>> [统计] 当前总积分: {initial_balance}")
                else:
                    print(">>> [动作] 发现未签到，正在点击...")
                    driver.execute_script("arguments[0].click();", target_button)
                    
                    # 等待动画和请求
                    print(">>> [等待] 正在提交签到请求 (5s)...")
                    time.sleep(5)
                    
                    # --- 4. 核对结果 ---
                    print(">>> [核对] 刷新页面获取最新积分...")
                    driver.refresh()
                    time.sleep(5) # 等待刷新加载
                    
                    try:
                        new_credits_element = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'credits')]"))
                        )
                        final_balance = parse_credits(new_credits_element.text)
                        
                        # 计算差值
                        diff = final_balance - initial_balance
                        
                        # 格式化输出
                        print("-" * 30)
                        if diff > 0:
                            print(f">>> [成功] 🎉 签到成功！")
                            print(f">>> [收益] 获得积分: +{diff:.1f}")
                            print(f">>> [总计] 当前积分: {final_balance:.1f}")
                        elif diff == 0:
                             print(f">>> [结果] ⚠️ 按钮已点击但积分未增加 (可能需要更长时间到账)。")
                             print(f">>> [总计] 当前积分: {final_balance:.1f}")
                        else:
                            # 很少见的情况，积分反而少了
                            print(f">>> [疑惑] 积分发生变动: {diff:.1f}")
                        print("-" * 30)
                        
                    except Exception as e:
                        print(f">>> [警告] 无法读取最新积分，无法验证是否到账。错误: {e}")

            else:
                print(">>> [错误] 页面上没找到任何包含 'Claim' 字样的按钮。")
                print(">>> [调试] 页面包含的按钮文字: ", [b.text for b in driver.find_elements(By.TAG_NAME, "button") if b.text])

        except Exception as e:
            print(f">>> [错误] 签到流程异常: {e}")

    except Exception as e:
        print(f">>> [崩溃] 全局异常: {e}")

    finally:
        print(">>> [结束] 关闭浏览器")
        driver.quit()

if __name__ == "__main__":
    run_auto_claim()
