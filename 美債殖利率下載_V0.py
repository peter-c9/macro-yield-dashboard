import yfinance as yf
import pandas as pd
import os
from datetime import datetime

# --- 設定存檔路徑 ---
folder_path = r"C:\XQ_Data\美債相關報價資料夾"

# 確保資料夾存在
os.makedirs(folder_path, exist_ok=True)
# --------------------

# 定義要抓取的商品清單，與對應的檔案名稱
tickers_map = {
    "^TNX": "10Y_Yield",
    "^TYX": "30Y_Yield",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "SOXX": "SOXX",
    "GLD": "Gold_GLD",
    "SLV": "Silver_SLV",
    "IBIT": "Bitcoin_IBIT"
}

print("啟動每日報價更新程式...\n")

for ticker, file_name in tickers_map.items():
    file_path = os.path.join(folder_path, f"{file_name}.csv")
    
    # 判斷是「首次抓取」還是「增量更新」
    if os.path.exists(file_path):
        # 讀取既有檔案
        existing_df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
        # 取得舊資料的最後一天
        last_date = existing_df.index[-1]
        print(f"🔄 [{file_name}] 找到既有檔案，最後日期為 {last_date.date()}。正在抓取新資料...")
        
        # 只抓取最後一天之後的新資料 (Yahoo Finance 支援傳入 datetime 物件)
        new_data = yf.Ticker(ticker).history(start=last_date)['Close']
        
        if not new_data.empty:
            new_data.index = new_data.index.tz_localize(None).normalize()
            new_df = pd.DataFrame(new_data)
            new_df.columns = ['Close']
            
            # 合併舊資料與新資料，並移除重複重疊的日期 (保留最新的)
            combined_df = pd.concat([existing_df, new_df])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
        else:
            # 如果沒有新資料 (例如連續假日)，就直接沿用舊資料
            combined_df = existing_df
            
    else:
        print(f"🆕 [{file_name}] 找不到檔案。準備抓取完整 20 年歷史資料...")
        new_data = yf.Ticker(ticker).history(period="20y")['Close']
        
        if new_data.empty:
            print(f"⚠️ 警告：無法取得 {ticker} 的資料。跳過此商品。")
            continue
            
        new_data.index = new_data.index.tz_localize(None).normalize()
        combined_df = pd.DataFrame(new_data)
        combined_df.columns = ['Close']

    # --- 關鍵：重新對齊日曆並補齊空值 ---
    start_date = combined_df.index.min()
    end_date = combined_df.index.max()
    
    # 產生涵蓋每天的連續日曆
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 重新對齊，並用前一天的資料往後填補 (ffill)
    combined_df = combined_df.reindex(full_date_range).ffill()
    
    # --- 格式化與存檔 ---
    combined_df.index.name = 'Date'
    # 將日期格式化為 YYYY-MM-DD 存入 CSV
    combined_df.to_csv(file_path, date_format='%Y-%m-%d')
    print(f"✅ [{file_name}] 處理完成！已儲存至：{file_path}\n")

print("🎉 所有商品更新完畢！")