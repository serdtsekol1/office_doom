import os

import dotenv
import requests
from requests_html import HTMLSession
from selenium.webdriver.common.by import By

from time import sleep
import undetected_chromedriver as uc

class DiadocApi():
    LIST_DOCUMENTS = []
    USER_BOX_ID = "09cbea0c-f483-4fa2-801a-bb4bd31c5e41"
    LOGIN_URL = "https://auth.kontur.ru/?back=https%3A%2F%2Fcabinet.kontur.ru%2F%3Fp%3D1210%26utm_referer%3Dauth.kontur.ru%26utm_startpage%3Dkontur.ru%26utm_orderpage%3Dkontur.ru"
    session = None
    LOGIN = None
    PASSWORD = None

    def __init__(self, login, password):
        print(login, password)
        self.session = HTMLSession()
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": "\"Not)A;Brand\";v=\"99\", \"Google Chrome\";v=\"127\", \"Chromium\";v=\"127\",",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Site": "none",
            # "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "en,ru;q=0.9,en-US;q=0.8,uk;q=0.7",
            # "Referer": "https://auth.kontur.ru/?customize=diadoc&back=https%3A%2F%2Fdiadoc.kontur.ru%2F"
        }

        self.LOGIN = login
        self.PASSWORD = password
        self.login_http()

    def login_http(self):
        """
        Можливо колись понадобиться стандартний логін через https
        :return:
        """

        from selenium import webdriver

        # get BaseProjectPath
        BASE_PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

        # Path to the chromedriver executable
        CHROME_DRIVER_PATH = f'{BASE_PROJECT_PATH}/chromedriver.exe'

        options = uc.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        driver = uc.Chrome(options=options)

        # Navigate to the desired URL
        driver.get("https://auth.kontur.ru/?customize=diadoc&back=https%3A%2F%2Fdiadoc.kontur.ru%2F")

        # Find element with data-tid="tab_login"
        login_tab = driver.find_element(By.XPATH, "//*[contains(@data-tid, 'tab_login')]")
        login_tab.click()

        # Find element with name="login"
        login_field = driver.find_element(By.NAME, "login")
        login_field.send_keys(self.LOGIN)

        # Find element with type="password"
        password_field = driver.find_element(By.CSS_SELECTOR, "*[type='password']")
        password_field.send_keys(self.PASSWORD)

        # Find element with data-tid="Button__root"
        login_button = driver.find_element(By.XPATH, "//*[contains(@data-tid, 'Button__root')]")
        login_button.click()
        sleep(3)
        # Fetch cookies
        cookies = driver.get_cookies()

        for cookie in cookies:
            self.session.cookies.set(cookie['name'], cookie['value'])
        # ddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd
        page_list_documents = self.session.get(f"https://diadoc.kontur.ru/{self.USER_BOX_ID}/Folder/Inbox")
        list_elements_with_document = page_list_documents.html.find("#letterList > li")
        print(list_elements_with_document)
        # Close the browser
        # driver.quit()


        #
        # get_forgy = self.session.get("https://auth.kontur.ru/", verify=False, proxies=self.proxies, allow_redirects=True, )
        # # run js  script
        # script = """"""
        # cockies = get_forgy.html.render(reload=True, keep_page=True, script=script, wait=3, sleep=4)
        #
        # print(cockies)
        # ngtoken = get_forgy.cookies.get('ngtoken')
        # # self.session.cookies.set('ngtoken', ngtoken)
        # get_forgy = self.session.get("https://auth.kontur.ru/", headers={'Referer': 'https://auth.kontur.ru/'}, verify=False, proxies=self.proxies)
        # print(get_forgy)
        # authpage = self.session.get(self.LOGIN_URL, verify=False, proxies=self.proxies)
        #
        # self.session.headers.update({
        #     'X-CSRF-Token': authpage.cookies.get('AntiForgery'),
        #     'Referer': self.LOGIN_URL
        # })
        # self.session.headers.pop('Upgrade-Insecure-Requests')
        #
        # diadoc = self.session.post(
        #     "https://auth.kontur.ru/api/authentication/password/auth-by-password?customize=diadoc",
        #     allow_redirects=True,
        #     json=
        #     {
        #         "Login": self.LOGIN, "Password": self.PASSWORD, "Remember": True
        #     }
        # )
        # print(diadoc)


dotenv.load_dotenv(override=True)
DIADOC_LOGIN = os.environ.get('DIADOC_LOGIN')
DIADOC_PASSWORD = os.environ.get('DIADOC_PASSWORD')
DIADOC_API = DiadocApi(DIADOC_LOGIN, DIADOC_PASSWORD)
