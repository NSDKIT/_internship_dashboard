import streamlit as st
import pandas as pd
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
import markdown

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
            spreadsheet_id = "1SsUwD9XoDR5i1IzqSA_B4oxW0Mu49lQ72iQrhA7KzvM"
            sheet_name = "info"
            st.info("シークレット設定が見つからないため、ハードコード値を使用します")
        
        # データ範囲を指定してスプレッドシートからデータを取得
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:U"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            st.warning("スプレッドシートにデータがありません")
            return pd.DataFrame()
            
        # 1行目を列名として使用し、2行目以降をデータとして使用
        column_names = values[0]
        data = values[1:]
        
        # データをDataFrameに変換
        df = pd.DataFrame(data, columns=column_names)
        
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
        return pd.DataFrame()

# 説明整形（Markdown→HTML変換）
def format_description(text):
    if pd.isna(text) or (isinstance(text, str) and text.strip() == ""):
        return "<i>説明なし</i>"

    # 本格的にMarkdownパース
    html = markdown.markdown(text)
    return html

def create_internship_card(internship):
    """インターンシップ情報をカード形式で表示するHTMLを生成"""
    title = internship.get('インターン名', '')
    company = internship.get('企業名', '')
    industry = internship.get('業界', '')
    work_type = internship.get('形式', '')
    location = internship.get('勤務地', '')
    station = internship.get('最寄り駅', '')
    period = internship.get('期間', '')
    position = internship.get('職種', '')
    salary = internship.get('報酬', '')
    deadline = internship.get('応募締切', '')
    description = internship.get('説明', '')

    # 日付の整形
    if isinstance(deadline, pd.Timestamp):
        deadline = deadline.strftime('%Y-%m-%d')

    card_html = f"""
            {format_description(description)}
    """
    return card_html

# メインアプリ
def main():
    st.title("📄 インターンシップ 説明ダッシュボード")

    with st.spinner("データ読み込み中..."):
        df = fetch_internship_data()

    if df.empty:
        st.warning("説明データが存在しません。")
        return

    st.write(f"**{len(df)}件** のインターン説明が見つかりました。")

    # フィルター設定
    st.sidebar.header("フィルター設定")
    
    # 業界フィルター
    if '業界' in df.columns:
        industries = ["すべて"] + sorted(df['業界'].dropna().unique().tolist())
        selected_industry = st.sidebar.selectbox("業界", industries)
        if selected_industry != "すべて":
            df = df[df['業界'] == selected_industry]
    
    # 職種フィルター
    if '職種' in df.columns:
        positions = ["すべて"] + sorted(df['職種'].dropna().unique().tolist())
        selected_position = st.sidebar.selectbox("職種", positions)
        if selected_position != "すべて":
            df = df[df['職種'] == selected_position]
    
    # 形式フィルター
    if '形式' in df.columns:
        work_types = ["すべて"] + sorted(df['形式'].dropna().unique().tolist())
        selected_work_type = st.sidebar.selectbox("勤務形態", work_types)
        if selected_work_type != "すべて":
            df = df[df['形式'] == selected_work_type]

    # 掲示板カード形式で表示
    for idx, internship in df.iterrows():
        with st.container():
            cols = st.columns([1, 5])
            with cols[0]:
                # 企業ロゴやイメージのプレースホルダー
                st.image("https://placehold.jp/80x80.png", width=80)
            with cols[1]:
                st.markdown(f"**{internship['インターン名']}**")
                st.markdown(f"{internship['企業名']} | {internship['業界']} | {internship['勤務地']} | {internship['職種']}")
                st.markdown(f"💰 {internship.get('報酬', '未設定')} | 🕒 {internship.get('勤務日数', '未設定')}日/{internship.get('勤務時間', '未設定')}時間")
                if pd.notna(internship.get('応募締切')):
                    st.markdown(f"〆切: {internship['応募締切']:%Y-%m-%d}")
                with st.expander("詳細を見る"):
                    # 詳細情報を表形式で表示
                    st.markdown(create_internship_card(internship), unsafe_allow_html=True)
        st.markdown("---")  # 区切り線

if __name__ == "__main__":
    main()