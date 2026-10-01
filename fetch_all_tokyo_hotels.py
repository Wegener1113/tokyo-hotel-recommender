import os
import time

import requests
from dotenv import load_dotenv


# --------------------------------------------------
# 1. 載入 .env 裡的 Rakuten API credentials
# --------------------------------------------------
load_dotenv()

APP_ID = os.getenv("RAKUTEN_APPLICATION_ID")
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY")


# --------------------------------------------------
# 2. Rakuten Travel - Simple Hotel Search API
# --------------------------------------------------
URL = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20260731"


# --------------------------------------------------
# 3. Request parameters
#
# 目前只抓：
# detailClassCode = "A"
#
# hits = 30
# 每頁最多抓 30 間飯店，減少 API request 次數
# --------------------------------------------------
params = {
    "applicationId": APP_ID,
    "accessKey": ACCESS_KEY,
    "format": "json",
    "largeClassCode": "japan",
    "middleClassCode": "tokyo",
    "smallClassCode": "tokyo",
    "detailClassCode": "A",
    "hits": 30,
    "page": 1,
    "responseType": "large",
}


# --------------------------------------------------
# 4. 建立一個 request 函式
#
# 功能：
# - 發送 API request
# - 如果遇到 429，就等待後重試
# - 最多重試 3 次
# --------------------------------------------------
def fetch_page(page, max_retries=3):

    # 指定目前要抓哪一頁
    params["page"] = page

    for attempt in range(1, max_retries + 1):

        print(f"Fetching page {page}... attempt {attempt}")

        response = requests.get(URL, params=params)

        # ------------------------------------------
        # 如果成功
        # ------------------------------------------
        if response.status_code == 200:
            return response.json()

        # ------------------------------------------
        # 如果遇到 429 Too Many Requests
        # ------------------------------------------
        if response.status_code == 429:
            print("Rate limit reached.")

            # 每次 retry 等久一點
            wait_seconds = 10 * attempt

            print(f"Waiting {wait_seconds} seconds before retrying...")

            time.sleep(wait_seconds)

            continue

        # ------------------------------------------
        # 如果是其他 HTTP error
        # 例如 403 / 404 / 500
        # ------------------------------------------
        response.raise_for_status()

    # 如果 3 次都沒有成功
    raise Exception(
        f"Failed to fetch page {page} after {max_retries} attempts."
    )


# --------------------------------------------------
# 5. 先抓第 1 頁
#
# 第 1 頁有兩個用途：
# 1. 取得 pagingInfo
# 2. 保存第 1 頁 hotels
# --------------------------------------------------
data = fetch_page(1)


# --------------------------------------------------
# 6. 讀取 pagination 資訊
# --------------------------------------------------
paging_info = data["pagingInfo"]

record_count = paging_info["recordCount"]
page_count = paging_info["pageCount"]

print()
print("detailClassCode: A")
print("recordCount:", record_count)
print("pageCount:", page_count)
print()


# --------------------------------------------------
# 7. 保存第 1 頁的飯店
# --------------------------------------------------
all_hotels = list(data["hotels"])

print(f"Fetched page 1/{page_count}")
print("Hotels collected so far:", len(all_hotels))
print()


# --------------------------------------------------
# 8. 從第 2 頁抓到最後一頁
#
# 第 1 頁已經抓過，
# 所以從 page = 2 開始。
# --------------------------------------------------
for page in range(2, page_count + 1):

    # 呼叫我們上面寫好的 fetch_page()
    page_data = fetch_page(page)

    # 取得這一頁的 hotels
    hotels = page_data["hotels"]

    # 加進總 list
    all_hotels.extend(hotels)

    print(
        f"Finished page {page}/{page_count} "
        f"| Total hotels: {len(all_hotels)}"
    )

    # 正常 request 之間停 1 秒
    # 避免太密集地呼叫 API
    time.sleep(1)


# --------------------------------------------------
# 9. 最後驗證
# --------------------------------------------------
print()
print("==============================")
print("Finished fetching detailClassCode A")
print("==============================")

print("Expected hotel count:", record_count)
print("Actual hotel count:", len(all_hotels))


# --------------------------------------------------
# 10. 檢查筆數是否一致
# --------------------------------------------------
if len(all_hotels) == record_count:
    print("Hotel count check: PASS")
else:
    print("Hotel count check: WARNING")

# --------------------------------------------------
# 11. 檢查 hotelNo 是否重複
#
# 每間 Rakuten 飯店都有自己的 hotelNo。
# 我們把所有 hotelNo 收集起來，
# 再比較總數與不重複數量。
# --------------------------------------------------
hotel_nos = []

for hotel_item in all_hotels:
    hotel_no = hotel_item["hotel"][0]["hotelBasicInfo"]["hotelNo"]

    hotel_nos.append(hotel_no)


# --------------------------------------------------
# 12. 計算 unique hotelNo
#
# set 會自動移除重複值。
# --------------------------------------------------
unique_hotel_nos = set(hotel_nos)


print()
print("==============================")
print("Duplicate check")
print("==============================")

print("Total hotelNo:", len(hotel_nos))
print("Unique hotelNo:", len(unique_hotel_nos))
print("Duplicate count:", len(hotel_nos) - len(unique_hotel_nos))


# --------------------------------------------------
# 13. 判斷是否有重複
# --------------------------------------------------
if len(hotel_nos) == len(unique_hotel_nos):
    print("hotelNo duplicate check: PASS")
else:
    print("hotelNo duplicate check: WARNING")