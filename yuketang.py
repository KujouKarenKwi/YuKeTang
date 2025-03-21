import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains as ac

#Forked from hu1hu
#Changjiang Yuketang

def get_user_info(driver):
    """打开浏览器，让用户登录，并获取 URL 和 Cookie"""
    base_url = "https://changjiang.yuketang.cn/"
    print(f"请在弹出的浏览器窗口中登录您的雨课堂账号，并导航到您的课程页面。")
    driver.get(base_url)
    input("登录完成后，请按 Enter 继续...")

    current_url = driver.current_url
    print(f"获取到的课程 URL: {current_url}")

    cookies = driver.get_cookies()
    session_cookie = None
    for cookie in cookies:
        if cookie['name'] == 'sessionid':
            session_cookie = cookie
            break

    if session_cookie:
        print(f"获取到的 sessionid Cookie: {session_cookie}")
        return current_url, session_cookie
    else:
        print("未能找到 sessionid Cookie，请检查是否已成功登录。")
        return current_url, None

def time_string_to_seconds(time_str):
    """将时间字符串 (HH:MM:SS 或 MM:SS 或 SSS) 转换为秒"""
    parts = list(map(int, time_str.split(':')))
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:
        return parts[0]
    return 0

def monitor_playback_status(driver, wait, text):
    """监控视频播放状态，直到播放时间达到总时长 (处理鼠标需要保持移动显示时间的情况)"""
    while True:
        try:
            # 定位视频播放器的容器元素
            video_player = wait.until(EC.presence_of_element_located((By.ID, 'video-box')))

            # 创建 ActionChains 对象
            action = ac(driver)

            # 将鼠标移动到 video-box 的中心
            action.move_to_element(video_player).perform()

            # 循环执行小的鼠标移动，以保持时间显示
            start_time = time.time()
            while time.time() - start_time < 2:  # 持续移动一段时间，例如 2 秒，可以根据需要调整
                action.move_by_offset(10, 0).perform()  # 向右移动 10 像素
                action.move_by_offset(-10, 0).perform() # 向左移动 10 像素
                time.sleep(0.2) # 每次移动之间暂停 0.2 秒

            # 定位播放时间元素
            time_display = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'xt_video_player_current_time_display')))
            time_spans = time_display.find_elements(By.TAG_NAME, 'span')
            if len(time_spans) == 2:
                played_time_str = time_spans[0].text
                total_time_str = time_spans[1].text

                played_seconds = time_string_to_seconds(played_time_str)
                total_seconds = time_string_to_seconds(total_time_str)

                if played_seconds >= total_seconds and total_seconds > 0:
                    print(f"视频 {text} 已播放至总时长")
                    return True  # 返回 True 表示播放时间已到
                else:
                    time.sleep(1)  # 短暂的等待，避免过于频繁地检查
            else:
                print(f"视频 {text}: 无法找到播放时间元素或格式不正确，等待重试")
                time.sleep(5)
        except:
            print(f"视频 {text}: 获取播放时间元素失败，尝试重试")
            time.sleep(5)
    return False # 如果循环意外结束，返回 False

# 选择浏览器类型
driver = webdriver.Edge()
# 设置等待时间为10秒
wait = WebDriverWait(driver, 10)

# 获取用户 URL 和 Cookie
url, cookie = get_user_info(driver)

if cookie is None:
    print("无法获取 Cookie，脚本将退出。")
    driver.quit()
    exit()

driver.get(url)  # 打开用户指定的课程页面
driver.add_cookie(cookie)  # 添加用户的 Cookie
driver.refresh()  # 首次加载后刷新

while True:  # 添加一个外层循环，直到所有视频都完成
    # 等待直到元素出现(成绩单）
    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="tab-student_school_report"]/span'))).click()

    # 等待直到元素出现(视频）
    videos_container = wait.until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="pane-student_school_report"]/div/div[2]/section[2]/div[2]/ul')))
    # 获取所有视频
    video_list = videos_container.find_elements(By.TAG_NAME, 'li')

    # 获取当前窗口句柄
    main_window = driver.current_window_handle
    videos_played_in_this_round = False  # 标记在当前轮询中是否有视频被播放

    # 遍历所有视频
    for video in video_list[:-1]:
        # 切换回主窗口 (理论上应该已经在主窗口)
        driver.switch_to.window(main_window)

        # 判断是否已完成
        try:
            status_element = video.find_elements(By.TAG_NAME, 'div')[2]
            if status_element.text == '已完成 详情':
                continue
        except IndexError:
            print(f"警告: 无法找到视频完成状态元素，跳过。")
            continue

        # 获取视频名称
        try:
            text = video.find_elements(By.TAG_NAME, 'div')[0].text
            print("播放：" + text)
        except IndexError:
            print(f"警告: 无法找到视频名称元素，跳过。")
            continue

        current = len(driver.window_handles)
        # 点击播放
        if video.is_enabled() and videos_container.is_displayed():
            try:
                video.find_elements(By.TAG_NAME, 'div')[0].click()
                videos_played_in_this_round = True
            except Exception as e:
                print(f"点击视频播放按钮失败: {e}")
                continue
        else:
            continue
        # 等待新窗口打开
        wait.until(EC.number_of_windows_to_be(current + 1))

        # 获取所有窗口句柄
        all_handles = driver.window_handles
        # 切换到新窗口
        driver.switch_to.window(all_handles[-1])

        # 等待一段时间，确保页面加载完成
        time.sleep(3)  # 你可以根据实际情况调整等待时间

        # 尝试删除class为 left__menu 的元素
        try:
            left_menu = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'left__menu')))
            driver.execute_script("arguments[0].remove();", left_menu)
            print("已删除左侧边栏")
        except:
            print("未找到左侧边栏对应元素")

        # 将已播放时长修改为0
        try:
            video_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, 'video')))
            driver.execute_script("arguments[0].currentTime = 0;", video_element)
            print("成功将已播放时长修改为0")
        except:
            print("无法找到视频元素，无法修改已播放时长")

        # 等待视频加载，按静音键
        try:
            wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="video-box"]/div/xt-wrap/xt-controls/xt-inner/xt-volumebutton/xt-icon'))).click()
        except:
            print("无法点击静音按钮")

        # 倍速播放
        try:
            speed = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="video-box"]/div/xt-wrap/xt-controls/xt-inner/xt-speedbutton/xt-speedvalue')))
            # 播放
            play = wait.until(EC.presence_of_element_located(
                (By.XPATH, '//*[@id="video-box"]/div/xt-wrap/xt-controls/xt-inner/xt-playbutton')))
            # 点击2倍速
            acs = ac(driver)
            acs.move_to_element(speed).perform()
            acs.move_by_offset(0, -180).move_by_offset(5, 0).click().perform()
            # 点击播放
            play.click()
        except:
            print("无法设置播放速度或点击播放")

        # 监控视频播放状态
        if monitor_playback_status(driver, wait, text):
            # 播放时间达到总时长，关闭当前视频播放窗口
            driver.close()
            print(f"视频 {text} 播放完毕，准备返回视频列表页面")
        else:
            print(f"视频 {text} 播放可能出现问题，关闭窗口")
            driver.close()

    # 在所有视频遍历完成后刷新页面并重新获取视频列表
    if videos_played_in_this_round:
        driver.switch_to.window(main_window)
        driver.refresh()
        print("本轮视频播放完成，刷新视频列表页面")
        time.sleep(5)  # 等待页面刷新完成
    else:
        print("本轮没有播放任何新视频，可能所有视频都已完成。")
        break  # 如果没有播放任何新视频，可以认为所有视频都已完成，退出循环

while len(driver.window_handles) > 1:
    time.sleep(10)
    print("等待窗口关闭")

print("所有视频处理完毕，程序结束。")
