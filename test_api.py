import os
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

url = "https://openapi.rakuten.co.jp/engine/api/Travel/SimpleHotelSearch/20260731"


# =========================================================
# 3. 設定搜尋參數
# =========================================================
#
# 這裡就是你剛剛在 Rakuten API 測試表填的那些東西。
#
# detailClassCode 請改成你剛剛「測試成功」的那個 code。
#

params = {
    "applicationId": APP_ID,
    "accessKey": ACCESS_KEY,
    "format": "json",

    "largeClassCode": "japan",
    "middleClassCode": "tokyo",
    "smallClassCode": "tokyo",
    "detailClassCode": "A",   # 改成你剛剛測試成功的區域 code

    "hits": 5,                # 這次只抓 5 間
    "page": 1,                # 第一頁
    "responseType": "large",  # 要完整資料
}


# =========================================================
# 4. 向 Rakuten API 發送 GET request
# =========================================================

response = requests.get(
    url,
    params=params,
    timeout=30
)


# =========================================================
# 5. 檢查 HTTP 是否成功
# =========================================================

print("Status:", response.status_code)

# 如果 HTTP status 不是成功狀態，
# raise_for_status() 會直接拋出錯誤，避免程式繼續往下跑。
response.raise_for_status()


# =========================================================
# 6. 把 JSON response 轉成 Python dict
# =========================================================

data = response.json()


# =========================================================
# 7. 先看這組搜尋條件總共有多少筆
# =========================================================

paging_info = data.get("pagingInfo", {})

record_count = paging_info.get("recordCount")
page_count = paging_info.get("pageCount")

print("總飯店數:", record_count)
print("總頁數:", page_count)


# =========================================================
# 8. 建立一個 list，準備存每間飯店整理後的資料
# =========================================================

rows = []


# =========================================================
# 9. 一間一間處理 API 回傳的飯店
# =========================================================

for item in data.get("hotels", []):

    # 每間飯店裡面又包含很多資訊區塊
    hotel_blocks = item.get("hotel", [])

    # 先建立空 dict
    # 等一下找到對應區塊後再把資料放進去
    basic = {}
    rating = {}
    detail = {}
    facilities = {}
    policy = {}
    other = {}

    # -----------------------------------------------------
    # 10. 把不同資料區塊拆出來
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
    # 11. roomFacilities 本身是 list
    #
    # 例如：
    #
    # [
    #   {"item": "テレビ"},
    #   {"item": "冷蔵庫"},
    #   {"item": "Wi-Fi"}
    # ]
    #
    # 我們把它變成：
    #
    # "テレビ | 冷蔵庫 | Wi-Fi"
    #
    # 這樣比較適合存 CSV
    # -----------------------------------------------------

    room_facilities = [
        x.get("item")
        for x in facilities.get("roomFacilities", [])
        if x.get("item")
    ]


    # 飯店公共設施，同樣處理
    hotel_facilities = [
        x.get("item")
        for x in facilities.get("hotelFacilities", [])
        if x.get("item")
    ]


    # 無障礙設施
    handicapped_facilities = [
        x.get("item")
        for x in facilities.get("handicappedFacilities", [])
        if x.get("item")
    ]


    # -----------------------------------------------------
    # 12. 把一間飯店整理成一個 dict
    #
    # 你可以把這個 dict 想成 DataFrame 未來的一列。
    # -----------------------------------------------------

    row = {
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

        "service_rating": rating.get("serviceAverage"),
        "location_rating": rating.get("locationAverage"),
        "room_rating": rating.get("roomAverage"),
        "equipment_rating": rating.get("equipmentAverage"),
        "bath_rating": rating.get("bathAverage"),
        "breakfast_rating": rating.get("breakfastAverage"),
        "dinner_rating": rating.get("dinnerAverage"),
        "cleanliness_rating": rating.get("cleanlinessAverage"),

        "area_name": detail.get("areaName"),
        "hotel_class": detail.get("hotelClassCode"),

        "checkin_time": detail.get("checkinTime"),
        "checkout_time": detail.get("checkoutTime"),
        "last_checkin_time": detail.get("lastCheckinTime"),

        "room_count": facilities.get("hotelRoomNum"),

        "room_facilities": " | ".join(room_facilities),
        "hotel_facilities": " | ".join(hotel_facilities),
        "handicapped_facilities": " | ".join(handicapped_facilities),

        "about_leisure": facilities.get("aboutLeisure"),
        "language_info": facilities.get("linguisticLevel"),

        "parking_information": basic.get("parkingInformation"),

        "cancel_policy": policy.get("cancelPolicy"),

        "hotel_image_url": basic.get("hotelImageUrl"),
        "room_image_url": basic.get("roomImageUrl"),
        "hotel_information_url": basic.get("hotelInformationUrl"),
    }


    # 把這一間飯店加入 rows
    rows.append(row)


# =========================================================
# 13. 把 list of dict 轉成 pandas DataFrame
# =========================================================

df = pd.DataFrame(rows)


# =========================================================
# 14. 顯示我們抓到的資料
# =========================================================

print()
print(df[
    [
        "hotel_name",
        "review_average",
        "review_count",
        "min_price",
        "nearest_station",
    ]
])


# =========================================================
# 15. 存成 CSV
# =========================================================

df.to_csv(
    "tokyo_hotels_sample.csv",
    index=False,
    encoding="utf-8-sig"
)

print()
print("已儲存：tokyo_hotels_sample.csv")