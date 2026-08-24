import yfinance as yf
import pandas as pd
import os
import subprocess
import shutil  # 💡 新增：用來在資料夾之間複製檔案
from datetime import datetime

# ==========================================
# 1. 路徑與環境設定
# ==========================================
# 🎯 給 XQ 讀取的專用資料夾 (也是我們主要儲存、更新 CSV 的地方)
xq_save_folder = r"C:\XQ_Data\美債相關報價資料夾"

# 🎯 你的 GitHub 本機端專案資料夾 (請依實際狀況微調)
github_project_dir = r"C:\Users\User\OneDrive\文件\VS_Python\長天期美債殖利率_程式"
# 🎯 GitHub 專案裡存放資料的子資料夾
github_data_folder = os.path.join(github_project_dir, "data") 

# 確保兩個資料夾都存在
os.makedirs(xq_save_folder, exist_ok=True)
os.makedirs(github_data_folder, exist_ok=True)

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

# ==========================================
# 2. 抓取報價與增量更新邏輯
# ==========================================
print("啟動每日報價更新程式...\n")
has_updated_files = False

for ticker, file_name in tickers_map.items():
    # 💡 注意：所有的讀寫都在 XQ 的資料夾進行
    file_path = os.path.join(xq_save_folder, f"{file_name}.csv")
    
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path, index_col='Date', parse_dates=True)
        last_date = existing_df.index[-1]
        print(f"🔄 [{file_name}] 找到既有檔案，最後日期為 {last_date.date()}。正在抓取新資料...")
        
        new_data = yf.Ticker(ticker).history(start=last_date)['Close']
        
        if not new_data.empty:
            new_data.index = new_data.index.tz_localize(None).normalize()
            new_df = pd.DataFrame(new_data)
            new_df.columns = ['Close']
            
            combined_df = pd.concat([existing_df, new_df])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            has_updated_files = True
        else:
            combined_df = existing_df
    else:
        print(f"🆕 [{file_name}] 找不到檔案。準備抓取完整 20 年歷史資料...")
        new_data = yf.Ticker(ticker).history(period="20y")['Close']
        
        if new_data.empty:
            print(f"⚠️ 無法取得 {ticker} 資料。跳過。")
            continue
            
        new_data.index = new_data.index.tz_localize(None).normalize()
        combined_df = pd.DataFrame(new_data)
        combined_df.columns = ['Close']
        has_updated_files = True

    # 重新對齊日曆並補齊空值
    start_date = combined_df.index.min()
    end_date = combined_df.index.max()
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    combined_df = combined_df.reindex(full_date_range).ffill()
    
    combined_df.index.name = 'Date'
    # 存檔回 XQ 的資料夾
    combined_df.to_csv(file_path, date_format='%Y-%m-%d')
    print(f"  ✔️ [{file_name}] 處理完成！")

# ==========================================
# 3. 自動同步至 GitHub 專案與上傳
# ==========================================
print("\n" + "="*50)
if has_updated_files:
    print("🚀 檢測到 CSV 資料有更新，準備自動同步至 GitHub...")
    try:
        # 💡 新增步驟：將 XQ 資料夾裡更新好的 CSV，全部複製到 GitHub 專案資料夾中
        for file_name in tickers_map.values():
            src_file = os.path.join(xq_save_folder, f"{file_name}.csv")
            dst_file = os.path.join(github_data_folder, f"{file_name}.csv")
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
        print("📁 已將最新 CSV 複製到 GitHub 專案資料夾。")

        # 切換工作目錄到你的 Git 專案資料夾
        os.chdir(github_project_dir)

        subprocess.run(["git", "add", "."], check=True)
        
        # 捕捉 commit 訊息，避免「沒有實質變動」導致程式報錯中斷
        commit_result = subprocess.run(
            ["git", "commit", "-m", "自動更新美債與ETF報價資料"], 
            capture_output=True, text=True, encoding='utf-8'
        )
        
        if "nothing to commit" not in commit_result.stdout:
            print("🔄 正在與遠端倉庫同步 (Pull)...")
            subprocess.run(["git", "pull", "--rebase"], check=True)
            
            print("⬆️ 正在推送到 GitHub (Push)...")
            subprocess.run(["git", "push"], check=True)
            print("🎉 成功同步上傳至 GitHub！網頁資料將在 1~2 分鐘後更新。")
        else:
            print("⚡ 雖然檢測到檔案覆寫，但 Git 判定資料內容無實質差異，略過上傳。")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 執行失敗！錯誤代碼: {e}")
    except Exception as e:
        print(f"❌ 上傳發生未知錯誤: {e}")
else:
    print("⚡ 沒有檔案變動，略過上傳 GitHub。")
print("="*50 + "\n")