import os
import re
import sys
import csv
import math
import time
import json
import traceback
import configparser
from decimal import Decimal
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait

class ParamInfo:

    def __init__(self, start, end, step):
        self.start = Decimal(start)
        self.step = Decimal(step)
        self.count = (int)((Decimal(end) - self.start) / self.step) + 1

    def calclate_value(self, index):
        return self.start + self.step * index

def find_element_from_text(browser, xpath, text):
    for element in browser.find_elements_by_xpath(xpath):
        if text in element.text:
            return element
    return None

def contains_element(browser, src, xpath):
    for element in browser.find_elements_by_xpath(xpath):
        if element == src:
            return True
    return False

def wait_element(browser, xpath, sec = 10):
    wait = WebDriverWait(browser, sec)
    wait.until(expected_conditions.presence_of_element_located((By.XPATH, xpath)))

def convert_time(second):
    hour = second // 3600
    second %= 3600
    minute = second // 60
    second %= 60
    return '{}:{:02d}:{:02d}'.format(hour, minute, second)

if __name__ == '__main__':

    file_path = sys.argv[1]
    entry_time = datetime.now()

    config = configparser.ConfigParser()
    config.read('common.ini', 'utf_8_sig')
    driver_path = config.get('settings', 'DRIVER_PATH')
    chart_url = config.get('settings', 'CHART_URL')
    account = config.get('settings', 'ACCOUNT')
    password = config.get('settings', 'PASSWORD')

    config.read(file_path, 'utf_8_sig')
    param_start = config.get('settings', 'PARAM_START').split()
    param_end = config.get('settings', 'PARAM_END').split()
    param_step = config.get('settings', 'PARAM_STEP').split()

    # ログファイル作成
    log_dir = 'log'
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    prefix, _ = os.path.splitext(os.path.basename(file_path))
    file = open(os.path.join(log_dir, '{}_{}.csv'.format(prefix, entry_time.strftime('%Y%m%d_%H%M%S'))), 'w', encoding='utf-8')
    writer = csv.writer(file, lineterminator='\n')

    # パラメーター初期化
    param_list = []
    pattern_count = 1
    param_count = len(param_start)
    for i in range(param_count):
        param_info = ParamInfo(param_start[i], param_end[i], param_step[i])
        pattern_count *= param_info.count
        param_list.append(param_info)

    # 開始
    print('-----------------------------------------')
    print('pattern : {}'.format(pattern_count))
    print('necessary time : {}'.format(convert_time(int(pattern_count * 4.5))))
    print('-----------------------------------------')

    # ブラウザ起動
    browser = webdriver.Chrome(driver_path)
    browser.get(chart_url)
    wait_element(browser, '//A[@class="js-login-link"]')

    # ログイン画面ボタン押下
    browser.find_element_by_xpath('//A[@class="js-login-link"]').click();
    wait_element(browser, '//BUTTON[@class="tv-button tv-button--no-border-radius tv-button--size_large tv-button--primary_ghost tv-button--loader"]')

    # ログインボタン押下
    browser.find_element_by_xpath('//INPUT[@name="username"]').send_keys(account)
    browser.find_element_by_xpath('//INPUT[@name="password"]').send_keys(password)
    browser.find_element_by_xpath('//BUTTON[@class="tv-button tv-button--no-border-radius tv-button--size_large tv-button--primary_ghost tv-button--loader"]').click()
    wait_element(browser, '//DIV[@class="icon-button backtesting-open-format-dialog apply-common-tooltip"]')

    for i in range(pattern_count):

        # 設定ボタン押下
        browser.find_element_by_xpath('//DIV[@class="icon-button backtesting-open-format-dialog apply-common-tooltip"]').click()
        wait_element(browser, '//INPUT[@class="innerInput-29Ku0bwF-"]')

        # パラメータ入力
        div = i
        param_line = ''
        inputs = browser.find_elements_by_xpath('//INPUT[@class="innerInput-29Ku0bwF-"]')
        for j in range(param_count):
            if j > 0:
                param_line += ':'
            div, mod = divmod(div, param_list[j].count)
            value = str(param_list[j].calclate_value(mod))
            inputs[j].send_keys(Keys.CONTROL,'a')
            inputs[j].send_keys(Keys.DELETE)
            inputs[j].send_keys(value)
            param_line += value

        # OKボタン押下
        find_element_from_text(browser, '//BUTTON[@class="button-1iktpaT1- size-m-2G7L7Qat- intent-primary-1-IOYcbg- appearance-default-dMjF_2Hu-"]', 'OK').click()
        time.sleep(3)

        # 結果取得
        while True:
            try:
                profit = browser.find_element_by_xpath('//DIV[@class="report-data"]/DIV[1]/STRONG[1]')
                win_rate = browser.find_element_by_xpath('//DIV[@class="report-data"]/DIV[3]/STRONG[1]')
                profit_factor = browser.find_element_by_xpath('//DIV[@class="report-data"]/DIV[4]/STRONG[1]')
                drawdown = browser.find_element_by_xpath('//DIV[@class="report-data"]/DIV[5]/P[1]/SPAN[1]')
                write_line = [profit.text, win_rate.text, profit_factor.text, drawdown.text]
            except KeyboardInterrupt:
                raise
            except:
                ex, ms, tb = sys.exc_info()
                info = traceback.format_exception(ex, ms, tb)
                print(info)
                time.sleep(3)
            else:
                break
                
        # 書き込み
        for j in range(len(write_line)):
            match = re.match(r'([0-9]+\.?[0-9]*)', write_line[j])
            write_line[j] = match.group()
        if contains_element(browser, profit, '//SPAN[@class="neg"]/..'):
            write_line[0] = '-' + write_line[0]
        write_line[1] += '%'
        write_line[3] += '%'
        write_line.append(param_line)
        writer.writerow(write_line)

        progress = i + 1
        print('write_data:{}/{} ({:.1%})'.format(progress, pattern_count, progress / pattern_count))

    file.close()
    browser.close()
    browser.quit()