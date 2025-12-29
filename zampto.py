import os
import time
import sys
# 导入 Selenium 相关库
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, WebDriverException

# ================= 配置区域 =================
LOGIN_URL = "https://dash.zampto.net/"
ACCOUNTS_ENV = os.environ.get("ZAMPTO_ACCOUNTS")
# ===========================================

def run_renewal_for_user(username, password):
    print(f"\n>>> [开始] 正在处理账号: {username}")
    
    # --- 1. 防崩溃浏览器配置 ---
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new') 
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 30) # 全局等待时间

        # --- 2. 登录流程 ---
        print(f">>> [登录] 打开页面: {LOGIN_URL}")
        driver.get(LOGIN_URL)
        
        # 寻找账号输入框 (Logto 通常用 identifier)
        print(">>> [登录] 正在输入账号...")
        user_input = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "input[name='identifier'], input[name='email'], input[name='username']")
        ))
        user_input.clear()
        user_input.send_keys(username)
        print(">>> [登录] 账号输入完毕")
        
        # ============================================================
        # 【核心修复】智能处理“两步登录”或“密码框延迟”
        # ============================================================
        pwd_input = None
        try:
            # 方案A：尝试直接等待密码框出现 (只等3秒)
            print(">>> [登录] 尝试查找密码框...")
            pwd_input = WebDriverWait(driver, 3).until(
                EC.visibility_of_element_located((By.NAME, "password"))
            )
        except TimeoutException:
            # 方案B：如果3秒没等到，说明需要点击“下一步”
            print(">>> [登录] 未直接发现密码框，判断为'两步登录'模式，正在点击下一步...")
            
            # 寻找并点击提交按钮 (通常是 Sign In 或 Next)
            next_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            next_btn.click()
            
            # 点击后，必须等待密码框加载出来
            print(">>> [登录] 已点击下一步，正在等待密码框加载...")
            pwd_input = wait.until(
                EC.visibility_of_element_located((By.NAME, "password"))
            )

        # 输入密码
        pwd_input.clear()
        pwd_input.send_keys(password)
        print(">>> [登录] 密码输入完毕")
        time.sleep(1) # 稍微缓冲，防止点击太快

        # 再次点击登录按钮
        # 注意：页面可能有变化，重新查找按钮最稳妥
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        print(">>> [登录] 点击提交，等待跳转...")

        # 验证是否登录成功
        try:
            wait.until(EC.url_matches(r"overview|dashboard"))
            print(">>> [登录] 登录成功！")
        except TimeoutException:
            print(f">>> [错误] 登录超时，当前 URL: {driver.current_url}")
            # 尝试打印页面上的错误信息
            try:
                print(f">>> [页面提示] {driver.find_element(By.CSS_SELECTOR, '.error, [role=alert]').text}")
            except:
                pass
            raise Exception("Login failed")

        # --- 3. 获取服务器列表 ---
        server_links = []
        # 等待页面加载出列表（防止刚跳转还没渲染）
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='server?id=']")))
        except:
            print(">>> [提示] 未找到服务器链接，可能是账户下没有服务器。")

        buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='server?id=']")
        for btn in buttons:
            href = btn.get_attribute("href")
            if href and href not in server_links:
                server_links.append(href)
        
        print(f">>> [检测] 账号 {username} 下发现 {len(server_links)} 个服务器。")

        # --- 4. 逐个续费 ---
        for link in server_links:
            print(f"--- 正在处理服务器: {link} ---")
            driver.get(link)
            try:
                renew_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "a.action-button[onclick*='handleServerRenewal']")
                ))
                driver.execute_script("arguments[0].scrollIntoView();", renew_btn)
                time.sleep(1) 
                renew_btn.click()
                print(">>> [操作] 点击了续费按钮")
                
                try:
                    WebDriverWait(driver, 3).until(EC.alert_is_present())
                    driver.switch_to.alert.accept()
                    print(">>> [弹窗] 已确认")
                except TimeoutException:
                    pass
                
                print(">>> [成功] 续费指令已发送")
                time.sleep(2)
            except TimeoutException:
                print(">>> [跳过] 未找到续费按钮 (可能已续费)")
            except Exception as e:
                print(f">>> [出错] 服务器处理错误: {e}")

    except Exception as e:
        print(f">>> [失败] 账号 {username} 发生错误: {e}")
        # 如果出错，打印一下源码开头，方便看是不是还没进页面
        if driver:
            try:
                print(f">>> [调试] 错误时页面源码前300字: {driver.page_source[:300]}")
            except: pass

    finally:
        if driver:
            driver.quit()
        print(f">>> [结束] 账号 {username} 会话已关闭。\n")

def main():
    if not ACCOUNTS_ENV:
        print(">>> [错误] 环境变量 ZAMPTO_ACCOUNTS 未设置。")
        sys.exit(1)
    
    account_list = ACCOUNTS_ENV.split(',')
    for account_str in account_list:
        if ':' not in account_str: continue
        username, password = account_str.strip().split(':', 1)
        run_renewal_for_user(username.strip(), password.strip())

if __name__ == "__main__":
    main()
