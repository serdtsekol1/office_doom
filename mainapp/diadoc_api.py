import errno
import os
import json
import pickle
from time import sleep

from requests_html import HTMLSession




class DiadocApi():
    LIST_DOCUMENTS = []
    #USER_BOX_ID = "09cbea0c-f483-4fa2-801a-bb4bd31c5e41"
    LOGIN_URL = "https://auth.kontur.ru/?back=https%3A%2F%2Fcabinet.kontur.ru%2F%3Fp%3D1210%26utm_referer%3Dauth.kontur.ru%26utm_startpage%3Dkontur.ru%26utm_orderpage%3Dkontur.ru"
    session = None
    LOGIN = None
    PASSWORD = None

    def __init__(self, login, password,userid):
        print(login, password)
        self.session = HTMLSession()
        print("HTML Session - OK")
        self.session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
            "Accept-Encoding": "gzip, deflate, br",
            "Upgrade-Insecure-Requests": "1",
            "Connection": "keep-alive",
            "sec-ch-ua": "\"Chromium\";v=\"106\", \"Google Chrome\";v=\"106\", \"Not;A=Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Language": "ru-RU,ru;q=0.9",

        }
        print("Headers - OK")
        self.USER_BOX_ID = userid
        self.LOGIN = login
        self.PASSWORD = password
        print("Login and Password to self - OK")
        self.login_http()
    def login_check(self):
        login_check = self.session.get("https://diadoc.kontur.ru/Box/Selection", allow_redirects=False)
        status_code = login_check.status_code
        return True if status_code == 200 else False
        #return False if 'AccessDenied' in str(login_check.content) else True
    def login_http(self):
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from dremkas.settings import BASE_DIR

        """
        Можливо колись понадобиться стандартний логін через https
        :return:
        """
        BASE_PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))

        # Path to the chromedriver executable

        CHROME_DRIVER_PATH = f'{BASE_DIR}/chromedriver.exe'
        if os.path.exists("session_data.pkl"):
            with open("session_data.pkl", "rb") as file:
                self.session = pickle.load(file)
        if not self.login_check() :
            options = uc.ChromeOptions()
            #options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            #driver = uc.Chrome(options=options, executable_path=CHROME_DRIVER_PATH)
            driver = uc.Chrome(options=options,driver_executable_path=CHROME_DRIVER_PATH)
            print("Driver - OK")
            # Navigate to the desired URL
            driver.get("https://auth.kontur.ru/?customize=diadoc&back=https%3A%2F%2Fdiadoc.kontur.ru%2F")
            print("Auth contur Get - OK")

            # Find element with data-tid="tab_login"
            sleep(2)
            login_tab = driver.find_element(By.XPATH, "//*[contains(@data-tid, 'tab_login')]")
            login_tab.click()
            sleep(3)
            print("Login Tab Click - OK")

            # Find element with name="login"
            login_field = driver.find_element(By.NAME, "login")
            login_field.send_keys(self.LOGIN)
            print("Login Field Send - OK")

            # Find element with type="password"
            password_field = driver.find_element(By.CSS_SELECTOR, "*[type='password']")
            password_field.send_keys(self.PASSWORD)
            print("Password Field Send - OK")
            # Find element with data-tid="Button__root"
            login_button = driver.find_element(By.XPATH, "//*[contains(@data-tid, 'Button__root')]")
            login_button.click()
            print("Login Button Click - OK")
            sleep(3)
            # Fetch cookies
            cookies = driver.get_cookies()
            print("Cookies - OK")

            for cookie in cookies:
                self.session.cookies.set(cookie['name'], cookie['value'])
            #login_check = driver.find_element(By.CSS_SELECTOR, 'div[tid="profile"]')
            if self.login_check():
                with open("session_data.pkl", "wb") as file:
                    pickle.dump(self.session, file)




        # authpage = self.session.get(self.LOGIN_URL)
        #
        # self.session.headers.update({
            # 'X-CSRF-Token': authpage.cookies.get('AntiForgery'),
            # 'Referer': self.LOGIN_URL
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

    def get_documents(self):
        self.LIST_DOCUMENTS = []
        page_list_documents = self.session.get(f"https://diadoc.kontur.ru/{self.USER_BOX_ID}/Folder/Inbox")
        list_elements_with_document = page_list_documents.html.find("#letterList > li")

        for element_with_document in list_elements_with_document:
            list_elements_with_document_attach = element_with_document.find("ul[ft-name='attachments-list'] > li")
            for element_with_document_attach in list_elements_with_document_attach:
                try:
                    status = element_with_document_attach.find('span[ft-name="statusName"]', first=True).text
                    self.LIST_DOCUMENTS.append({

                        'id': element_with_document_attach.attrs.get("id"),
                        'date': element_with_document_attach.find("a[ft-name=\"documentLink\"]", first=True).attrs.get("documentdate").strip(),
                        'num': element_with_document_attach.find("a[ft-name=\"documentLink\"]", first=True).attrs.get("documentnumber").strip(),
                        'sum': element_with_document_attach.find("span[locstr=\"Sum_with_currency\"]", first=True).text.encode("utf-8").decode('ascii', 'ignore'),
                        'kontragent': element_with_document.find("span[ft-name=\"documentCounteragentName\"]", first=True).text,
                        'documentid': element_with_document_attach.attrs.get("documentid"),
                        'letterid': element_with_document_attach.attrs.get("letterid"),
                        'ft-name': element_with_document_attach.attrs.get("ft-name"),
                        'link_document': list(element_with_document_attach.absolute_links)[0],
                        'link_document_attachment': f'https://diadoc.kontur.ru/{self.USER_BOX_ID}/Download/Attachment?letterId={element_with_document_attach.attrs.get("letterid")}&attachmentId={element_with_document_attach.attrs.get("documentid")}',
                        'status': status,
                    })
                except Exception as e:
                    print("diadoc_api get_documents Exception [000]" + str(e))
        return self.LIST_DOCUMENTS

    def download(self, url, file_name):
        if not os.path.exists(os.path.dirname(file_name)):
            try:
                os.makedirs(os.path.dirname(file_name))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        try:
            with open(file_name, "wb") as file:
                response = self.session.get(url, timeout=4, allow_redirects=True)
                print(response.status_code, url)
                file.write(response.content)
        except Exception as ex:
            print(ex)

    def download_invoices(self):
        for dock in self.LIST_DOCUMENTS:
            print(dock)
            self.download(dock.get('link_document_attachment'), f'media/diadoc_files/{dock.get("documentid")}.xml')

# session.headers.update({
#     'Referer': "https://auth.kontur.ru/"
# })
# authpage = session.get("https://cabinet.kontur.ru/?p=1210&utm_referer=auth.kontur.ru&utm_startpage=kontur.ru&utm_orderpage=kontur.ru")
# authpage = session.get("https://diadoc.kontur.ru/Box/Selection?back=/?using=switcher&from=cabinet.kontur.ru")
