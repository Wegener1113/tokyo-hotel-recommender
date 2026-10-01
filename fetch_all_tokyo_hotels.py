import os
import time

import requests
import pandas as pd

from dotenv import load_dotenv


# =========================================================
# 1. 讀取 .env 裡的 Rakuten API 憑證
# =========================================================

load_dotenv()

APP_ID = os.getenv("RAKUTEN_APPLICATION_ID")
ACCESS_KEY = os.getenv("RAKUTEN_ACCESS_KEY")


# =========================================================
# 2. Rakuten Simple Hotel Search API endpoint
# =========================================================

URL = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20260731"


# =========================================================
# 3. 設定搜尋參數
# =========================================================
#
# 目前只抓 detailClassCode = "A"
#
# hits = 30：
# 每頁最多抓 30 間飯店，減少 API request 次數。
#

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


# =========================================================
# 4. 建立抓取單一頁面的函式
# =========================================================
#
# 功能：
# - 指定 page
# - 發送 API request
# - 遇到 429 時等待並重試
# - 最多重試 3 次
#

def fetch_page(page, max_retries=3):

    params["page"] = page

    for attempt in range(1, max_retries + 1):

        print(f"Fetching page {page}... attempt {attempt}")

        response = requests.get(
            URL,
            params=params,
            timeout=30
        )

        # 成功
        if response.status_code == 200:
            return response.json()

        # 遇到 Too Many Requests
        if response.status_code == 429:

            wait_seconds = 10 * attempt

            print("Rate limit reached.")
            print(f"Waiting {wait_seconds} seconds before retrying...")

            time.sleep(wait_seconds)

            continue

        # 其他 HTTP error
        response.raise_for_status()

    # 如果重試多次仍然失敗
    raise Exception(
        f"Failed to fetch page {page} "
        f"after {max_retries} attempts."
    )


# =========================================================
# 5. 抓第 1 頁
# =========================================================
#
# 第 1 頁同時拿來：
# 1. 取得 pagingInfo
# 2. 保存第 1 頁飯店資料
#

data = fetch_page(1)


# =========================================================
# 6. 取得 pagination 資訊
# =========================================================

paging_info = data.get("pagingInfo", {})

record_count = paging_info.get("recordCount")
page_count = paging_info.get("pageCount")


print()
print("==============================")
print("Pagination info")
print("==============================")

print("detailClassCode: A")
print("recordCount:", record_count)
print("pageCount:", page_count)


# =========================================================
# 7. 保存第 1 頁的飯店
# =========================================================

all_hotels = list(data.get("hotels", []))

print()
print(f"Fetched page 1/{page_count}")
print("Hotels collected so far:", len(all_hotels))


# =========================================================
# 8. 從第 2 頁抓到最後一頁
# =========================================================

for page in range(2, page_count + 1):

    page_data = fetch_page(page)

    hotels = page_data.get("hotels", [])

    all_hotels.extend(hotels)

    print(
        f"Finished page {page}/{page_count} "
        f"| Total hotels: {len(all_hotels)}"
    )

    # 每次正常 request 之間暫停 1 秒
    # 降低觸發 API rate limit 的機率
    time.sleep(1)


# =========================================================
# 9. 驗證實際抓到的飯店數
# =========================================================

print()
print("==============================")
print("Hotel count check")
print("==============================")

print("Expected hotel count:", record_count)
print("Actual hotel count:", len(all_hotels))


if len(all_hotels) == record_count:
    print("Hotel count check: PASS")
else:
    print("Hotel count check: WARNING")


# =========================================================
# 10. 檢查 hotelNo 是否重複
# =========================================================

hotel_nos = []

for item in all_hotels:

    hotel_blocks = item.get("hotel", [])

    for block in hotel_blocks:

        if "hotelBasicInfo" in block:

            hotel_no = block["hotelBasicInfo"].get("hotelNo")

            if hotel_no is not None:
                hotel_nos.append(hotel_no)

            break


unique_hotel_nos = set(hotel_nos)

duplicate_count = (
    len(hotel_nos)
    - len(unique_hotel_nos)
)


print()
print("==============================")
print("Duplicate check")
print("==============================")

print("Total hotelNo:", len(hotel_nos))
print("Unique hotelNo:", len(unique_hotel_nos))
print("Duplicate count:", duplicate_count)


if duplicate_count == 0:
    print("hotelNo duplicate check: PASS")
else:
    print("hotelNo duplicate check: WARNING")


# =========================================================
# 11. 解析所有飯店資料
# =========================================================

rows = []


for item in all_hotels:

    # 每間飯店內包含多個資訊 block
    hotel_blocks = item.get("hotel", [])

    basic = {}
    rating = {}
    detail = {}
    facilities = {}
    policy = {}
    other = {}


    # -----------------------------------------------------
    # 找出各資訊 block
    # -----------------------------------------------------

    for block in hotel_blocks:

        if "hotelBasicInfo" in block:
            basic = block["hotelBasicInfo"]

        elif "hotelRatingInfo" in block:
            rating = block["hotelRatingInfo"]

        elif "hotelDetailInfo" in block:
            detail = block["hotelDetailInfo"]

        elif "hotelFacilitiesInfo" in block:
            facilities = block["hotelFacilitiesInfo"]

        elif "hotelPolicyInfo" in block:
            policy = block["hotelPolicyInfo"]

        elif "hotelOtherInfo" in block:
            other = block["hotelOtherInfo"]


    # -----------------------------------------------------
    # roomFacilities
    #
    # API 格式例如：
    #
    # [
    #     {"item": "テレビ"},
    #     {"item": "冷蔵庫"}
    # ]
    #
    # 轉成：
    #
    # テレビ | 冷蔵庫
    # -----------------------------------------------------

    room_facilities = [
        x.get("item")
        for x in facilities.get("roomFacilities", [])
        if isinstance(x, dict) and x.get("item")
    ]


    # -----------------------------------------------------
    # hotelFacilities
    # -----------------------------------------------------

    hotel_facilities = [
        x.get("item")
        for x in facilities.get("hotelFacilities", [])
        if isinstance(x, dict) and x.get("item")
    ]


    # -----------------------------------------------------
    # handicappedFacilities
    # -----------------------------------------------------

    handicapped_facilities = [
        x.get("item")
        for x in facilities.get(
            "handicappedFacilities",
            []
        )
        if isinstance(x, dict) and x.get("item")
    ]


    # -----------------------------------------------------
    # 把一間飯店整理成 DataFrame 的一列
    # -----------------------------------------------------

    row = {

        # Basic info
        "hotel_no": basic.get("hotelNo"),
        "hotel_name": basic.get("hotelName"),
        "hotel_kana_name": basic.get("hotelKanaName"),

        "hotel_special": basic.get("hotelSpecial"),

        "min_price": basic.get("hotelMinCharge"),

        "postal_code": basic.get("postalCode"),

        "address1": basic.get("address1"),
        "address2": basic.get("address2"),

        "nearest_station": basic.get("nearestStation"),
        "access": basic.get("access"),

        "latitude": basic.get("latitude"),
        "longitude": basic.get("longitude"),

        "review_count": basic.get("reviewCount"),
        "review_average": basic.get("reviewAverage"),

        # Rating info
        "service_rating": rating.get("serviceAverage"),
        "location_rating": rating.get("locationAverage"),
        "room_rating": rating.get("roomAverage"),
        "equipment_rating": rating.get("equipmentAverage"),
        "bath_rating": rating.get("bathAverage"),
        "breakfast_rating": rating.get("breakfastAverage"),
        "dinner_rating": rating.get("dinnerAverage"),
        "cleanliness_rating": rating.get(
            "cleanlinessAverage"
        ),

        # Detail info
        "area_name": detail.get("areaName"),
        "hotel_class": detail.get("hotelClassCode"),

        "checkin_time": detail.get("checkinTime"),
        "checkout_time": detail.get("checkoutTime"),
        "last_checkin_time": detail.get(
            "lastCheckinTime"
        ),

        # Facilities info
        "room_count": facilities.get("hotelRoomNum"),

        "room_facilities": " | ".join(
            room_facilities
        ),

        "hotel_facilities": " | ".join(
            hotel_facilities
        ),

        "handicapped_facilities": " | ".join(
            handicapped_facilities
        ),

        "about_leisure": facilities.get(
            "aboutLeisure"
        ),

        "language_info": facilities.get(
            "linguisticLevel"
        ),

        # Basic info
        "parking_information": basic.get(
            "parkingInformation"
        ),

        # Policy info
        "cancel_policy": policy.get(
            "cancelPolicy"
        ),

        # Image / URL
        "hotel_image_url": basic.get(
            "hotelImageUrl"
        ),

        "room_image_url": basic.get(
            "roomImageUrl"
        ),

        "hotel_information_url": basic.get(
            "hotelInformationUrl"
        ),
    }


    rows.append(row)


# =========================================================
# 12. 轉成 pandas DataFrame
# =========================================================

df = pd.DataFrame(rows)


# =========================================================
# 13. DataFrame 驗證
# =========================================================

print()
print("==============================")
print("DataFrame check")
print("==============================")

print("Rows:", len(df))
print("Columns:", len(df.columns))

print(
    "Duplicate hotel_no:",
    df["hotel_no"].duplicated().sum()
)


# =========================================================
# 14. 顯示前 5 筆重要欄位
# =========================================================

print()

print(
    df[
        [
            "hotel_name",
            "review_average",
            "review_count",
            "min_price",
            "nearest_station",
            "room_count",
            "checkin_time",
            "parking_information",
        ]
    ].head()
)


# =========================================================
# 15. 額外檢查每個欄位有多少空值
#
# 這可以幫助我們區分：
# - 少數飯店本來就沒有資料
# - 某個欄位幾乎全部空白，可能 parser 有問題
# =========================================================

print()
print("==============================")
print("Missing value check")
print("==============================")

print(
    df.isna().sum()
)


# =========================================================
# 16. 輸出 CSV
# =========================================================

output_file = "tokyo_hotels_A.csv"


df.to_csv(
    output_file,
    index=False,
    encoding="utf-8-sig"
)


print()
print("==============================")
print("CSV export")
print("==============================")

print("Saved:", output_file)
print("Rows written:", len(df))