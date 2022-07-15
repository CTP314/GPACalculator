from concurrent.futures import thread
from lib2to3.pgen2 import driver
from os import access
from threading import Thread
from time import sleep
from pyparsing import col
from requests import head, options
from selenium.webdriver.remote.webdriver import WebDriver as wd
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wdw
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains as AC
from selenium.webdriver.chrome.options import Options
import selenium
from bs4 import BeautifulSoup as BS
import getpass

class GPACalculator:
    def __init__(self, opt: dict, headless=False):
        self.root_handle = None
        self.driver: wd = None
        self.passwd = opt["password"]
        self.userid = opt["username"]
        self.options = Options()
        self.options.page_load_strategy = 'eager'
        self.options.headless = headless
        self.options.add_argument('blink-settings=imagesEnabled=false') 
        self.options.add_argument('blink-settings=imagesEnabled=false') 
        self.options.add_argument('--disable-gpu')
        self.options.add_experimental_option('excludeSwitches', ['enable-automation']) 
        self.options.add_experimental_option('excludeSwitches', ['enable-logging']) 

    def login_webvpn(self):
        d = self.driver
        if d is not None:
            d.close()
        d = selenium.webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=self.options)
        d.get("https://webvpn.tsinghua.edu.cn/login")
        username = d.find_elements(By.XPATH,
                                   '//div[@class="login-form-item"]//input'
                                   )[0]
        password = d.find_elements(By.XPATH,
                                   '//div[@class="login-form-item password-field" and not(@id="captcha-wrap")]//input'
                                   )[0]

        username.send_keys(str(self.userid))
        password.send_keys(self.passwd)
        d.find_element(By.ID, "login").click()
        self.root_handle = d.current_window_handle
        self.driver = d
        return d

    def access(self, url_input):
        d = self.driver
        url = By.ID, "quick-access-input"
        btn = By.ID, "go"
        wdw(d, 5).until(EC.visibility_of_element_located(url))
        actions = AC(d)
        actions.move_to_element(d.find_element(*url))
        actions.click()
        actions.\
            key_down(Keys.CONTROL).\
            send_keys("A").\
            key_up(Keys.CONTROL).\
            send_keys(Keys.DELETE).\
            perform()

        d.find_element(*url)
        d.find_element(*url).send_keys(url_input)
        d.find_element(*btn).click()

    def switch_another(self):
        d = self.driver
        assert len(d.window_handles) == 2
        wdw(d, 5).until(EC.number_of_windows_to_be(2))
        for window_handle in d.window_handles:
            if window_handle != d.current_window_handle:
                d.switch_to.window(window_handle)
                return

    def switch_another_skip_root(self):
        d = self.driver
        assert len(d.window_handles) == 3
        wdw(d, 5).until(EC.number_of_windows_to_be(3))
        for window_handle in d.window_handles:
            if window_handle != d.current_window_handle and window_handle != self.root_handle:
                d.switch_to.window(window_handle)
                break      

    def to_root(self):
        self.driver.switch_to.window(self.root_handle)

    def close_all(self):
        while True:
            try:
                l = len(self.driver.window_handles)
                if l == 0:
                    break
            except selenium.common.exceptions.InvalidSessionIdException:
                return
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.driver.close()

    def login_info(self):
        d = self.driver
        self.access('info.tsinghua.edu.cn')
        self.switch_another()
        wdw(d, 60).until(EC.visibility_of_element_located((By.XPATH, '//*[@id="userName"]')))
        username = d.find_element(By.XPATH, '//*[@id="userName"]')
        password = d.find_element(By.XPATH, '/html/body/table[2]/tbody/tr/td[3]/table/tbody/tr/td[5]/input')
        username.send_keys(self.userid)
        password.send_keys(self.passwd)
        d.find_element(By.XPATH, '/html/body/table[2]/tbody/tr/td[3]/table/tbody/tr/td[6]/input').click()

    def get_grades(self):
        """
        print:
            2020-秋: *.**
            2021-春: *.**
            2021-夏: *.**
            2021-秋: *.**
            2022-春: *.**
        attrs = ['id', 'num', 'name', 'credit', 'hours', 'level', 'grade', 'sub', 'attr', 'tag', 'term', 'final']
        """
        d = self.driver
        btn = By.XPATH, '//*[@id="menu"]/li[2]/a[10]'
        wdw(d, 20).until(EC.visibility_of_element_located(btn))
        d.find_element(btn[0], btn[1]).click()
        self.switch_another_skip_root()
        text = d.find_element(By.XPATH, '/html').get_attribute("innerHTML")
        soup = BS(text, 'lxml')
        tbody = soup.find('table', class_="table table-striped table-condensed").find('tbody')
        rows = tbody.find_all('tr')[1:-2]
        res = dict()
        gpas = []
        for row in rows:
            cols = row.find_all('td')
            cols = [ele.text.strip() for ele in cols]
            term = cols[-2]
            if term not in res:
                res[term] = [.0, .0]
            if cols[6] != 'N/A':
                res[term][0] += float(cols[6]) * float(cols[3])
                res[term][1] += float(cols[3])
        res = sorted(res.items(), key=lambda i:i[0])
        for key, val in res:
            if key[-1] == '1':
                term = key[0 : 4]+"-秋"
            elif key[-1] == '2':
                term = key[5 : 9]+"-春"
            else:
                term = key[5 : 9]+"-夏"
            avg = val[0] / val[1] if val[1] != 0 else 4.
            gpas.append((term, avg))
        for key, val in gpas:
            print(key+":", val)
        

if __name__ == "__main__":
    userid = input('用户名：')
    passwd = getpass.getpass('密码：')
    calculator = GPACalculator({"username": userid, "password": passwd})
    calculator.login_webvpn()
    calculator.login_info()
    calculator.get_grades()
    calculator.close_all()