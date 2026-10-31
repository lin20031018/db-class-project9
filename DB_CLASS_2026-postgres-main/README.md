# 中山網路書店

[![GitHub release](https://img.shields.io/github/release/Text-Analytics-and-Retrieval/db_class2023)](https://github.com/Text-Analytics-and-Retrieval/db_class2023/releases/latest)
[![GitHub license](https://img.shields.io/github/license/Text-Analytics-and-Retrieval/db_class2023)](https://github.com/Text-Analytics-and-Retrieval/db_class2023/main/LICENSE)

一套使用Flask開發的網路書店系統，後端使用Postgres資料庫

## 功能

- 提供CRUD範例，並搭配資料分析功能。
- 以MVC架構開發。
- 一般消費者可以瀏覽、搜尋、購買商品，並查看訂單狀態。
- 後台管理者可以編輯商品，並檢視每筆訂單以及商品銷售圖表。

## 安裝

### 0. 進入終端機

### 1. 取得原始碼

```bash
# 從 Github 拉取原始碼
git clone https://github.com/Text-Analytics-and-Retrieval/DB_CLASS_2026-postgres.git
cd DB_CLASS_2026-postgres/
```

### 2. 建立環境
注意：請先安裝 [anaconda](https://www.anaconda.com/download) 再進行後續的步驟
```bash!
# 1. `db-2026` 可改為自訂的環境名稱
# 2. 同學也可以自訂 `python=...` 的版本，但要注意3.11版會有版本衝突的問題，不建議使用
conda create -n db-2026 python=3.10

# 3. 啟動 conda 環境
conda activate db-2026

# 4. 這時候可以在終端機看到類似 
# (db-2026) user@userMacBook-Pro directory %
```

### 3. 安裝環境

##### 安裝python套件

```bash
# 1. 請確認已啟動 conda 環境
# 2. 請確認 `requirements.txt` 檔案位於當前目錄
pip install -r requirements.txt
```

##### 修改連線資訊
首先，把 .env.example 這個檔案複製一份，並取名叫 .env

接著，在 .env 檔案內填入 PostgreSQL 連線資訊。
> 各組的連線資訊存放在網路大學的， 分組學習 ➔專案分組 ➔進入小組 ➔討論 ➔組內討論 ➔資料庫連線資訊
```bash
# .env 檔案中對應的環境參數範例
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=...
DB_NAME=...
```


### 4. 匯入SQL
> 參考資料: [Link](https://learningsky.io/use-postgresql-databases-with-the-pgadmin/)
- 打開 ebook.sql
- 將 SQL 檔裡面的程式碼 貼到 自己組別的資料庫內執行(在自己組別的資料庫點右鍵選Query Tool)並執行

### 5. 啟動程式

```bash
python app.py
倘若遇到 OSError: [Errno 98] Address already in use  像這樣的錯誤代表有重複執行的問題
請輸入 lsof -i :5000 查看是哪個PID使用中，並再輸入kill -9 <該執行中的PID> 刪除
```

## 使用

- 輸入點選running on後面的網址，進入首頁。![2024-10-12 13-30-04 的螢幕擷圖](https://github.com/user-attachments/assets/da1cb799-b40d-4604-8035-10294bf8867c)
- 首次使用請點選註冊按鈕，並註冊帳號。
- 註冊後，點選登入即可進入頁面。

## 校園場館管理者後台

管理者沿用 `app_user.identity = 'manager'`，從一般登入頁登入後進入 `/admin/dashboard`。學生、教師及匿名使用者均無管理後台操作權限，公開註冊只建立學生帳號。

### 程式分層

沿用原有 MVC 目錄。登入、註冊、管理者建立指令、CSRF 驗證及共用權限檢查在 `api/api.py`；後台控制器只處理表單與導頁，SQL、交易、單次審核與時段衝突規則集中於 `api/sql.py`。

```text
api/
  api.py                     # 登入、註冊、管理者指令、權限與 CSRF
  sql.py                     # 預約、場地、器材、使用紀錄與分析查詢
backstage/
  views/
    manager.py               # 預約／場地／使用紀錄 CRUD 與審核
    analysis.py              # 預約儀表板
  templates/
    backstage.html           # 共用頂部導覽與版面
    dashboard.html           # 預約分析
    reservationManager.html  # 預約列表
    reservationForm.html     # 新增／修改預約
    reservationDetail.html   # 詳情、審核、取消、使用紀錄
    _reservationTable.html   # 共用預約表格
    venueManager.html        # 場地列表
    venueForm.html           # 場地及器材新增／修改
    venueDetail.html         # 場地及器材詳情
static/css/
  backstage.css              # 延用原首頁的深藍、淺藍與青綠配色
```

後台延用原管理員首頁的 Arial 字體、深藍頂部導覽、淺藍背景、青綠按鈕與白色圓角卡片，不再使用獨立側邊欄。`app.py` 註冊 `manager` 與 `analysis` Blueprint，既有 `/admin/...` 網址維持可用。

### 安裝與建立管理者

在本 README 所在的應用程式目錄執行，先設定 PostgreSQL 的 `DB_USER`、`DB_PASSWORD`、`DB_HOST`、`DB_PORT`、`DB_NAME`。正式部署必須設定私密隨機的 `FLASK_SECRET_KEY`；未設定時使用本次程序的隨機金鑰，重啟後需重新登入。

```bash
# 依序執行 migrations/ 下的 SQL；可重複執行，不清空既有資料
python -m flask init-reservations

# 互動輸入編號、姓名、信箱、密碼（至少12字元）及密碼確認
python -m flask create-manager

python -m flask run --host 127.0.0.1 --port 5000
```

沒有預設管理者或公開密碼。帳號建立命令不會覆寫或提升既有帳號權限。初始化加入「校園共同單位」供註冊選擇；每位使用者必須有所屬單位。舊 `ebook.sql` 只含書店資料，無法取代校園資料表初始化。

此雲端環境可先啟用已安裝的工具與開發資料庫連線：

```bash
source /workspace/.venvs/db-project9/bin/activate
source /workspace/.db-project9/env.sh
cd /workspace/db-class-project9/DB_CLASS_2026-postgres-main
python -m flask init-reservations
python -m flask create-manager
```

### 操作流程與規則

1. 在「場地與器材」新增場地，填寫類型、容量、開放／暫停／維修狀態及說明。器材每行填寫 `器材名稱 | 狀態 | 數量`，可新增、查看、修改及刪除配置。場地採軟刪除，歷史預約仍保留；尚有未結束的待審核／核准預約時不能刪除。容量縮減或關閉不能影響未結束的核准預約。
2. 在「預約管理」替已註冊的申請人建立預約，選擇開放場地、起訖時間、用途與人數。人數不能超過場地容量。預約時間皆為台北時間（UTC+8）。
3. 只有尚未審核的待審核申請可以修改。每筆預約只能審核一次；核准或駁回後不可修改、重新送審或重新審核。駁回必填意見，保留審核者、時間與意見，需重送時必須建立新預約。
4. 同一場地與核准預約時段重疊時不能新增或核准；首尾相接可以使用。待審核申請可互相重疊，但交易鎖確保同時審核也不能重複核准。場地以外鍵識別，改名不影響衝突檢查。
5. 待審核及已核准、尚無使用紀錄的預約可以取消；取消後不可再審核。刪除為軟刪除，保留原始預約及稽核資料，有使用紀錄時須先處理紀錄。
6. 已核准預約的詳情頁可建立、查看、修改、刪除實際使用紀錄，記錄到場、離開時間與回饋。可先記錄到場，再補離開時間。`usage_record` 依附預約，以 `(rid, urid)` 為複合主鍵，`rid` 同時具有唯一限制，確保一筆預約最多一筆使用紀錄。

儀表板包含總數、待審核／核准數、累計核准時數、今日核准使用數、實際使用中／完成／回饋統計、近六個月預約趨勢、熱門場地與待處理申請。統計排除已刪除預約，月趨勢依開始月份，今日使用數包含跨日預約。列表支援場地、姓名、帳號搜尋、狀態／開始日期區間篩選及每頁20筆分頁。

所有寫入均驗證 CSRF；刪除、取消、審核及使用紀錄寫入只接受 POST。預約以版本檢查阻擋過期操作（HTTP 409），操作歷程保留建立、修改、審核、取消與使用紀錄變更。

### 資料模型對照

為相容既有登入程式，校園使用者存放於 `app_user`，密碼以 `password_hash` 儲存，不儲存明文。預約 `rid` 對應 `reservation.id`、`applicant_count` 對應 `attendees`、預計起訖時間對應 `starts_at`／`ends_at`；審核關係的時間與意見為 `reviewed_at`／`review_note`，審核者為 `reviewed_by`。場地以 `reservation.venue_id → venue.vid` 關聯，器材拆為多筆 `venue_equipment`。`reservation.venue` 為相容顯示欄位，場地改名時同步更新。

### 整合測試

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

使用目前 `DB_*` 連線，帳號須能建立 schema。測試建立隨機獨立 schema 並在完成後移除，不清空正常資料。涵蓋 CRUD、權限、CSRF、單次審核、駁回不可修改、查詢分頁、HTML 轉義、時段衝突、並行核准、過期操作、場地器材、容量與開放狀態、取消及使用紀錄。
