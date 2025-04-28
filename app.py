import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# ページ設定
st.set_page_config(
    page_title="インターンシップ一覧ダッシュボード",
    page_icon="📊",
    layout="wide"
)

# カスタムCSSの追加
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .headline {
        color: #2c3e50;
        font-weight: bold;
    }
    .subheader {
        color: #7f8c8d;
        font-size: 0.9em;
    }
    .highlight {
        background-color: #ffffcc;
        padding: 2px 5px;
        border-radius: 3px;
    }
    .deadline {
        color: #e74c3c;
        font-weight: bold;
    }
    .tag {
        background-color: #eaeaea;
        color: #333;
        padding: 2px 8px;
        border-radius: 10px;
        margin-right: 5px;
        font-size: 0.8em;
    }
    .tag-it {
        background-color: #3498db;
        color: white;
    }
    .tag-marketing {
        background-color: #2ecc71;
        color: white;
    }
    .tag-design {
        background-color: #9b59b6;
        color: white;
    }
    .tag-finance {
        background-color: #f1c40f;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets APIへの接続
@st.cache_resource
def get_google_sheets_service():
    """Google Sheets APIサービスを取得する関数"""
    try:
        # Streamlit Secretsからサービスアカウントの認証情報を取得
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        st.error(f"認証エラー: {str(e)}")
        return None

@st.cache_data(ttl=300)  # 5分間キャッシュ
def fetch_internship_data():
    """Googleスプレッドシートからインターンシップデータを取得する関数"""
    try:
        service = get_google_sheets_service()
        if not service:
            st.error("Google Sheets APIサービスの取得に失敗しました")
            return pd.DataFrame()
            
        # スプレッドシートIDとシート名を取得
        try:
            spreadsheet_id = st.secrets["SPREADSHEET_ID"]
            sheet_name = st.secrets.get("SHEET_NAME", "info")
        except Exception as e:
            st.error(f"シート情報の取得に失敗しました: {str(e)}")
            return pd.DataFrame()
        
        # データ範囲を指定してスプレッドシートからデータを取得
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:U"
        ).execute()
        
        values = result.get('values', [])
        if not values:
            st.warning("スプレッドシートにデータがありません")
            return pd.DataFrame()
            
        # ヘッダーと行データを取得
        headers = values[0]
        rows = values[1:]
        
        # DataFrameに変換
        df = pd.DataFrame(rows, columns=headers)
        
        # 応募締切日と開始予定日を日付形式に変換
        try:
            df['応募締切'] = pd.to_datetime(df['応募締切'], errors='coerce')
            df['開始予定日'] = pd.to_datetime(df['開始予定日'], errors='coerce')
        except:
            pass
            
        return df
    except Exception as e:
        st.error(f"データ取得エラー: {str(e)}")
        return pd.DataFrame()

def format_deadline(deadline):
    """応募締切日を整形する関数"""
    if pd.isna(deadline):
        return ""
        
    today = datetime.now().date()
    deadline_date = deadline.date()
    days_remaining = (deadline_date - today).days
    
    if days_remaining < 0:
        return f"<span style='color: gray;'>締切済み ({deadline.strftime('%Y-%m-%d')})</span>"
    elif days_remaining == 0:
        return f"<span style='color: red; font-weight: bold;'>本日締切 ({deadline.strftime('%Y-%m-%d')})</span>"
    elif days_remaining <= 7:
        return f"<span style='color: red;'>あと{days_remaining}日 ({deadline.strftime('%Y-%m-%d')})</span>"
    else:
        return f"{deadline.strftime('%Y-%m-%d')}"

def display_internship_card(internship):
    """インターンシップカードを表示する関数"""
    try:
        company = internship.get("企業名", "不明")
        position = internship.get("職種", "不明")
        title = internship.get("インターン名", f"{company} {position}インターンシップ")
        industry = internship.get("業界", "不明")
        location = internship.get("勤務地", "不明")
        work_type = internship.get("形式", "不明")
        salary = internship.get("報酬", "不明")
        deadline = internship.get("応募締切", "")
        deadline_formatted = format_deadline(deadline)
        
        # タグに使用するクラス名を決定
        industry_class = "tag"
        if "IT" in industry or "テクノロジー" in industry:
            industry_class += " tag-it"
        elif "広告" in industry or "マーケティング" in industry:
            industry_class += " tag-marketing"
        elif "デザイナー" in position:
            industry_class += " tag-design"
        elif "金融" in industry:
            industry_class += " tag-finance"
            
        # カードのHTMLを生成
        card_html = f"""
        <div class="card">
            <h3 class="headline">{title}</h3>
            <p class="subheader">{company} | <span class="{industry_class}">{industry}</span> | {work_type}</p>
            <p>勤務地: {location}</p>
            <p>報酬: {salary}</p>
            <p>応募締切: {deadline_formatted}</p>
            <p><a href="#" onclick="showDetails('{title.replace("'", "\\'")}')" style="text-decoration: none;">詳細を見る</a></p>
        </div>
        """
        
        return card_html
    except Exception as e:
        return f"<div class='card'>表示エラー: {str(e)}</div>"

def main():
    # ヘッダー
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #2c3e50;'>インターンシップ一覧ダッシュボード</h1>
        <p style='color: #7f8c8d;'>最新のインターンシップ情報をチェックしよう！</p>
    </div>
    """, unsafe_allow_html=True)
    
    # データ取得
    with st.spinner("データを読み込み中..."):
        df = fetch_internship_data()
    
    if df.empty:
        st.warning("データがありません。インターンシップ情報を先に登録してください。")
        return
        
    # サイドバー - フィルター設定
    st.sidebar.header("フィルター設定")
    
    # 業界フィルター
    industries = ["すべて"] + sorted(df["業界"].unique().tolist())
    selected_industry = st.sidebar.selectbox("業界", industries)
    
    # 職種フィルター
    positions = ["すべて"] + sorted(df["職種"].unique().tolist())
    selected_position = st.sidebar.selectbox("職種", positions)
    
    # 形式フィルター
    work_types = ["すべて"] + sorted(df["形式"].unique().tolist())
    selected_work_type = st.sidebar.selectbox("勤務形態", work_types)
    
    # 締切フィルター
    deadline_options = [
        "すべて",
        "今週締切",
        "今月締切",
        "締切済み"
    ]
    selected_deadline = st.sidebar.selectbox("締切", deadline_options)
    
    # データフィルタリング
    filtered_df = df.copy()
    
    if selected_industry != "すべて":
        filtered_df = filtered_df[filtered_df["業界"] == selected_industry]
        
    if selected_position != "すべて":
        filtered_df = filtered_df[filtered_df["職種"] == selected_position]
        
    if selected_work_type != "すべて":
        filtered_df = filtered_df[filtered_df["形式"] == selected_work_type]
        
    today = pd.Timestamp(datetime.now().date())
    if selected_deadline == "今週締切":
        end_of_week = today + timedelta(days=(6 - today.dayofweek))
        filtered_df = filtered_df[(filtered_df["応募締切"] >= today) & (filtered_df["応募締切"] <= end_of_week)]
    elif selected_deadline == "今月締切":
        next_month = today.replace(day=28) + timedelta(days=4)
        end_of_month = next_month - timedelta(days=next_month.day)
        filtered_df = filtered_df[(filtered_df["応募締切"] >= today) & (filtered_df["応募締切"] <= end_of_month)]
    elif selected_deadline == "締切済み":
        filtered_df = filtered_df[filtered_df["応募締切"] < today]
    
    # ダッシュボードのメインエリアを構築
    
    # 1. 統計情報
    st.markdown("## 📊 統計情報")
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        st.metric("登録インターンシップ数", len(df))
        
    with stats_col2:
        upcoming_deadlines = len(df[(df["応募締切"] >= today) & (df["応募締切"] <= today + timedelta(days=7))])
        st.metric("今週締切のインターン", upcoming_deadlines)
        
    with stats_col3:
        most_common_industry = df["業界"].value_counts().index[0] if not df.empty else "なし"
        st.metric("最も多い業界", most_common_industry)
        
    with stats_col4:
        most_common_position = df["職種"].value_counts().index[0] if not df.empty else "なし"
        st.metric("最も多い職種", most_common_position)
    
    # 2. 可視化 - 業界別インターンシップ数
    st.markdown("## 📈 業界別インターンシップ数")
    
    try:
        # 業界別のインターンシップ数を集計
        industry_counts = df["業界"].value_counts().reset_index()
        industry_counts.columns = ["業界", "件数"]
        
        # 棒グラフ作成
        fig = px.bar(
            industry_counts,
            x="業界",
            y="件数",
            color="業界",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            title="業界別インターンシップ数"
        )
        fig.update_layout(xaxis_title="業界", yaxis_title="インターンシップ数")
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"グラフの作成に失敗しました: {str(e)}")
    
    # 3. インターンシップリスト
    st.markdown("## 🔍 検索結果")
    st.write(f"{len(filtered_df)} 件のインターンシップが見つかりました")
    
    # ソートオプション
    sort_options = {
        "応募締切が近い順": "応募締切",
        "会社名(昇順)": "企業名", 
        "最新登録順": "最新登録"
    }
    sort_by = st.selectbox("並び替え", list(sort_options.keys()))
    
    # ソート実行
    if sort_by == "応募締切が近い順":
        filtered_df = filtered_df.sort_values(by="応募締切")
    elif sort_by == "会社名(昇順)":
        filtered_df = filtered_df.sort_values(by="企業名")
    # 最新登録順はデフォルトのままとする
    
    # インターンシップカードを表示
    if not filtered_df.empty:
        # 3列でカードを表示
        cols = st.columns(3)
        for i, (_, internship) in enumerate(filtered_df.iterrows()):
            with cols[i % 3]:
                st.markdown(display_internship_card(internship), unsafe_allow_html=True)
    else:
        st.info("条件に一致するインターンシップはありません。フィルター設定を変更してみてください。")
    
    # 詳細表示用のモーダルダイアログ用JavaScript
    st.markdown("""
    <script>
    function showDetails(title) {
        alert("インターンシップ詳細: " + title);
        // 実際にはモーダルダイアログなどを表示
    }
    </script>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
