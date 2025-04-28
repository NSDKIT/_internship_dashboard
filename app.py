import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import markdown  # 追加ポイント！

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

<<<<<<< HEAD
@st.cache_data(ttl=300)  # 5分間キャッシュ
def fetch_internship_data():
    """Googleスプレッドシートからインターンシップデータを取得する関数"""
    try:
        service = get_google_sheets_service()
        if not service:
            st.error("Google Sheets APIサービスの取得に失敗しました")
            return pd.DataFrame()
            
        # スプレッドシートIDとシート名を取得 - 柔軟な取得方法
        spreadsheet_id = None
        sheet_name = None
        
        # トップレベルのシークレットを確認
        if "SPREADSHEET_ID" in st.secrets:
            spreadsheet_id = st.secrets["SPREADSHEET_ID"]
            sheet_name = st.secrets.get("SHEET_NAME", "info")
        
        # もしなければgcp_service_account内を確認
        if spreadsheet_id is None and "gcp_service_account" in st.secrets:
            if "SPREADSHEET_ID" in st.secrets["gcp_service_account"]:
                spreadsheet_id = st.secrets["gcp_service_account"]["SPREADSHEET_ID"]
                sheet_name = st.secrets["gcp_service_account"].get("SHEET_NAME", "info")
        
        # それでもなければハードコード値を使用
        if spreadsheet_id is None:
            spreadsheet_id = "1SsUwD9XsadcfaxsefaMu49lx72iQxaefdaefA7KzvM"  # あなたの実際のIDに置き換え
            sheet_name = "info"
            st.info("シークレット設定が見つからないため、ハードコード値を使用します")
        
        # デバッグ情報を表示
        st.write("デバッグ情報:")
        st.write(f"スプレッドシートID: {spreadsheet_id}")
        st.write(f"シート名: {sheet_name}")
        
        # データ範囲を指定してスプレッドシートからデータを取得
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:U"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            st.warning("スプレッドシートにデータがありません")
            return pd.DataFrame()
            
        # デバッグ情報：生データの表示
        st.write("生データの最初の5行:")
        st.write(values[:5])
            
        # ヘッダーと行データを取得
        headers = values[0]
        rows = values[1:]
        
        # DataFrameに変換
        df = pd.DataFrame(rows, columns=headers)
        
        # デバッグ情報：DataFrameの情報を表示
        st.write("DataFrameの情報:")
        st.write(f"行数: {len(df)}")
        st.write(f"列名: {list(df.columns)}")
        st.write("最初の5行のデータ:")
        st.write(df.head())
        
        # 応募締切日と開始予定日を日付形式に変換
        try:
            if '応募締切' in df.columns:
                df['応募締切'] = pd.to_datetime(df['応募締切'], errors='coerce')
            if '開始予定日' in df.columns:
                df['開始予定日'] = pd.to_datetime(df['開始予定日'], errors='coerce')
        except Exception as e:
            st.warning(f"日付変換エラー: {str(e)}")
            
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {str(e)}")
=======
# データ取得（U列のみ）
@st.cache_data(ttl=300)
def fetch_description_data():
    service = get_google_sheets_service()
    spreadsheet_id = st.secrets["gcp_service_account"]["SPREADSHEET_ID"]
    sheet_name = st.secrets["gcp_service_account"].get("SHEET_NAME", "info")

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!U:U"
    ).execute()

    values = result.get('values', [])
    if not values or len(values) < 2:
>>>>>>> ecf6d49fb0f9f9ed9a7ad6a1f3b021408a29add7
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]
    df = pd.DataFrame(rows, columns=[headers])
    return df

# 説明整形（Markdown→HTML変換）
def format_description(text):
    if pd.isna(text) or (isinstance(text, str) and text.strip() == ""):
        return "<i>説明なし</i>"

    # 本格的にMarkdownパース
    html = markdown.markdown(text)
    return html

# メインアプリ
def main():
    st.title("📄 インターンシップ 説明ダッシュボード")

    with st.spinner("データ読み込み中..."):
        df = fetch_description_data()

    if df.empty:
        st.warning("説明データが存在しません。")
        return

    st.write(f"**{len(df)}件** のインターン説明が見つかりました。")

    cols = st.columns(3)

    for i, row in enumerate(df.itertuples(index=False)):
        description = getattr(row, '説明', None)
        formatted = format_description(description)

        card_html = f"""
        <div style="background: white; padding: 20px; margin-bottom: 20px; 
                    border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); 
                    min-height: 250px;">
            <details>
              <summary style="font-weight: bold; color: #3498db; cursor: pointer;">
                説明を読む
              </summary>
              <div style="margin-top: 10px;">{formatted}</div>
            </details>
        </div>
        """

        with cols[i % 3]:
            st.markdown(card_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
