import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import re

# ページ設定
st.set_page_config(
    page_title="インターン説明ダッシュボード",
    page_icon="📄",
    layout="wide"
)

# Google Sheets API 接続
@st.cache_resource
def get_google_sheets_service():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    return build('sheets', 'v4', credentials=credentials)

# データ取得（U列だけ）
@st.cache_data(ttl=300)
def fetch_description_data():
    service = get_google_sheets_service()
    spreadsheet_id = st.secrets["gcp_service_account"]["SPREADSHEET_ID"]
    sheet_name = st.secrets["gcp_service_account"].get("SHEET_NAME", "info")

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!U:U"  # ← U列だけ取得！
    ).execute()

    values = result.get('values', [])
    if not values or len(values) < 2:
        return pd.DataFrame()

    headers = values[0]   # 通常 "説明"
    rows = values[1:]     # データ

    df = pd.DataFrame(rows, columns=[headers])
    return df

# 説明を整形する
def format_description(text):
    if not text or pd.isna(text):
        return "説明なし"
    
    # 軽いHTML整形
    text = re.sub(r'###\s*(.+)', r'<h3>\1</h3>', text)
    text = text.replace('\n', '<br>')  # 改行を保持
    return text

# メインアプリ
def main():
    st.title("📄 インターンシップ説明一覧")

    with st.spinner("データ読み込み中..."):
        df = fetch_description_data()

    if df.empty:
        st.warning("説明データが存在しません")
        return

    st.write(f"**{len(df)}件** の説明が見つかりました")

    for idx, row in df.iterrows():
        description = row.iloc[0]
        formatted = format_description(description)
        
        # それぞれカード風に表示
        st.markdown(f"""
        <div style="background: white; padding: 20px; margin-bottom: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            {formatted}
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
