import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import re

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
    .description-box {
        padding: 15px;
        background-color: #f9f9f9;
        border-radius: 5px;
        margin-top: 10px;
        font-family: inherit;
    }
    .description-box h3 {
        font-size: 1.2em;
        margin-top: 1em;
        margin-bottom: 0.5em;
        color: #2c3e50;
    }
    .description-box p {
        margin-bottom: 0.7em;
    }
    .description-box ul {
        margin-left: 1.5em;
        margin-bottom: 1em;
    }
    .description-box li {
        margin-bottom: 0.5em;
    }
    details summary {
        cursor: pointer;
        font-weight: bold;
        color: #3498db;
        padding: 5px 0;
    }
    details summary:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# Google Sheets APIへの接続
@st.cache_resource
def get_google_sheets_service():
    """Google Sheets APIサービスを取得する関数"""
    try:
        # シークレットが存在するか確認
        if "gcp_service_account" not in st.secrets:
            st.error("シークレット設定が見つかりません。Streamlit Cloudの設定を確認してください。")
            st.write("設定方法についてのガイド:")
            st.write("1. Streamlit Cloudのダッシュボードでアプリの設定を開く")
            st.write("2. 左側メニューから「Secrets」を選択")
            st.write("3. サービスアカウント情報とスプレッドシートIDを設定する")
            return None
            
        # Streamlit Secretsからサービスアカウントの認証情報を取得
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        
        return build('sheets', 'v4', credentials=credentials)
    except Exception as e:
        st.error(f"認証エラー: {str(e)}")
        st.write("デバッグ情報:")
        st.write(f"利用可能なシークレットキー: {list(st.secrets.keys())}")
        return None

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

# 列名を標準化する関数
def standardize_columns(df):
    """列名を標準化する関数"""
    # 列名のマッピング (ExcelファイルとGoogleスプレッドシートの列名の対応)
    column_mapping = {
        # Excelの列名: 標準列名
        "インターン名": "インターン名",
        "企業名": "企業名",
        "業界": "業界",
        "インターン職種": "職種",
        "職種": "職種",
        "勤務地": "勤務地",
        "最寄り駅": "最寄り駅",
        "期間": "期間",
        "報酬": "報酬",
        "交通費": "交通費",
        "勤務可能時間": "勤務可能時間",
        "勤務日数": "勤務日数",
        "勤務時間": "勤務時間",
        "選考フロー": "選考フロー",
        "応募締切": "応募締切",
        "開始予定日": "開始予定日",
        "募集人数": "募集人数",
        "必須スキル": "必須スキル",
        "歓迎スキル": "歓迎スキル",
        "形式": "形式",
        "募集対象": "募集対象",
        "説明": "説明"
    }
    
    # 列名を変換
    renamed_columns = {}
    for col in df.columns:
        if col in column_mapping:
            renamed_columns[col] = column_mapping[col]
    
    if renamed_columns:
        df = df.rename(columns=renamed_columns)
    
    # 必須列の確認と追加
    required_columns = ["インターン名", "企業名", "業界", "職種", "勤務地", "説明"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = "不明"  # 不足している列は「不明」で埋める
    
    return df

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

def format_markdown_description(description):
    """マークダウン形式のテキストをHTMLに変換する関数"""
    if not description or pd.isna(description):
        return "詳細情報はありません"
    
    # ### で始まる行を<h3>タグに変換
    description = re.sub(r'###\s+(.+)', r'<h3>\1</h3>', description)
    
    # 各行をパラグラフに変換（空行は除く）
    lines = description.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:  # 空行はスキップ
            continue
            
        # すでにHTMLタグがある場合はそのまま
        if line.startswith('<') and line.endswith('>'):
            formatted_lines.append(line)
            continue
            
        # 箇条書き（・）の処理
        if line.startswith('・'):
            # 最初の箇条書きアイテムの場合、リスト開始タグを追加
            if not in_list:
                formatted_lines.append('<ul style="margin-left: 1.5em; padding-left: 0;">')
                in_list = True
                
            # 箇条書きアイテムをリストアイテムに変換
            item = line[1:].strip()
            formatted_lines.append(f"<li style='margin-bottom: 0.5em;'>{item}</li>")
        else:
            # 箇条書きが終了した場合、リスト終了タグを追加
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
                
            # 通常の段落
            if not line.startswith('<h3>') and not line.endswith('</h3>'):
                formatted_lines.append(f"<p style='margin-bottom: 0.7em;'>{line}</p>")
            else:
                formatted_lines.append(line)
    
    # 最後の要素がリストの場合、リストを閉じる
    if in_list:
        formatted_lines.append('</ul>')
        
    return ''.join(formatted_lines)

def display_internship_card(internship):
    """インターンシップカードを表示する関数"""
    try:
        company = internship.get("企業名", "不明")
        position = internship.get("職種", "不明")
        title = internship.get("インターン名", f"{company} {position}インターンシップ")
        industry = internship.get("業界", "不明")
        location = internship.get("勤務地", "不明")
        work_type = internship.get("形式", "不明") if "形式" in internship else "不明"
        salary = internship.get("報酬", "不明")
        deadline = internship.get("応募締切", "")
        deadline_formatted = format_deadline(deadline)
        description = internship.get("説明", "詳細情報はありません")
        
        # 説明をマークダウンからHTMLに変換
        formatted_description = format_markdown_description(description)
        
        # タグに使用するクラス名を決定
        industry_class = "tag"
        if isinstance(industry, str):
            if "IT" in industry or "テクノロジー" in industry:
                industry_class += " tag-it"
            elif "広告" in industry or "マーケティング" in industry:
                industry_class += " tag-marketing"
        
        if isinstance(position, str):
            if "デザイナー" in position:
                industry_class += " tag-design"
        
        if isinstance(industry, str) and "金融" in industry:
            industry_class += " tag-finance"
            
        # カードのHTMLを生成
        card_html = f"""
        <div class="card">
            <h3 class="headline">{title}</h3>
            <p class="subheader">{company} | <span class="{industry_class}">{industry}</span> | {work_type}</p>
            <p>勤務地: {location}</p>
            <p>報酬: {salary}</p>
            <p>応募締切: {deadline_formatted}</p>
            <details>
                <summary>詳細情報を見る</summary>
                <div class="description-box">
                    {formatted_description}
                </div>
            </details>
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
    
    # データソースの選択
    data_source = st.radio(
        "データソースを選択",
        ["Googleスプレッドシート", "Excelファイルをアップロード"]
    )
    
    df = pd.DataFrame()
    
    if data_source == "Googleスプレッドシート":
        # Google Sheetsからデータ取得
        with st.spinner("Googleスプレッドシートからデータを読み込み中..."):
            df = fetch_internship_data()
    else:
        # Excelファイルをアップロード
        uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx", "xls"])
        if uploaded_file is not None:
            try:
                with st.spinner("Excelファイルを読み込み中..."):
                    df = pd.read_excel(uploaded_file)
                    df = standardize_columns(df)  # 列名を標準化
                st.success("Excelファイルの読み込みが完了しました")
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {str(e)}")
    
    if df.empty:
        st.warning("データがありません。インターンシップ情報を先に登録するか、Excelファイルをアップロードしてください。")
        return
    
    # サイドバーにデバッグ情報を追加
    with st.sidebar.expander("デバッグ情報（開発者用）"):
        st.write("利用可能なシークレットキー:")
        try:
            st.write(list(st.secrets.keys()))
            
            if "gcp_service_account" in st.secrets:
                st.write("gcp_service_account内のキー:")
                st.write(list(st.secrets["gcp_service_account"].keys()))
            else:
                st.write("gcp_service_accountが見つかりません")
        except:
            st.write("シークレット情報にアクセスできません")
        
        st.write("データフレーム情報:")
        st.write(f"行数: {len(df)}")
        st.write(f"列名: {list(df.columns)}")
    
    # サイドバー - フィルター設定
    st.sidebar.header("フィルター設定")
    
    # 業界フィルター
    industries = ["すべて"] + sorted(df["業界"].unique().tolist())
    selected_industry = st.sidebar.selectbox("業界", industries)
    
    # 職種フィルター
    positions = ["すべて"] + sorted(df["職種"].unique().tolist())
    selected_position = st.sidebar.selectbox("職種", positions)
    
    # 形式フィルター
    work_types = ["すべて"]
    if "形式" in df.columns:
        work_types += sorted(df["形式"].unique().tolist())
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
        
    if selected_work_type != "すべて" and "形式" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["形式"] == selected_work_type]
        
    # 日付フィルタリング
    if "応募締切" in filtered_df.columns and not filtered_df["応募締切"].isnull().all():
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
        today = pd.Timestamp(datetime.now().date())
        if "応募締切" in df.columns and not df["応募締切"].isnull().all():
            upcoming_deadlines = len(df[(df["応募締切"] >= today) & (df["応募締切"] <= today + timedelta(days=7))])
            st.metric("今週締切のインターン", upcoming_deadlines)
        else:
            st.metric("今週締切のインターン", "不明")
        
    with stats_col3:
        if "業界" in df.columns and not df["業界"].isnull().all():
            most_common_industry = df["業界"].value_counts().index[0] if not df.empty else "なし"
            st.metric("最も多い業界", most_common_industry)
        else:
            st.metric("最も多い業界", "不明")
        
    with stats_col4:
        if "職種" in df.columns and not df["職種"].isnull().all():
            most_common_position = df["職種"].value_counts().index[0] if not df.empty else "なし"
            st.metric("最も多い職種", most_common_position)
        else:
            st.metric("最も多い職種", "不明")
    
    # 2. 可視化 - 業界別インターンシップ数
    if "業界" in df.columns and not df["業界"].isnull().all():
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
    if sort_by == "応募締切が近い順" and "応募締切" in filtered_df.columns:
        filtered_df = filtered_df.sort_values(by="応募締切")
    elif sort_by == "会社名(昇順)" and "企業名" in filtered_df.columns:
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

if __name__ == "__main__":
    main()
