import streamlit as st
from googleapiclient.discovery import build
import pandas as pd

# タイトルと説明
st.title("YouTube動画検索アプリ")
st.write("検索キーワードを入力して、YouTube動画を検索できます。")

# API情報
DEVELOPER_KEY
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# YouTube API 初期化
@st.cache_resource
def get_youtube_client():
    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=DEVELOPER_KEY
    )

youtube = get_youtube_client()

# 動画の基本情報とURLを取得する関数
def get_video_info(part, q, order, type, total_count):
    dic_list = []
    max_results = 50  # YouTube API の上限
    search_response = youtube.search().list(part=part, q=q, order=order, type=type, maxResults=max_results)
    output = search_response.execute()

    while len(dic_list) < total_count:
        dic_list += output['items']
        if 'nextPageToken' not in output:
            break
        next_page_token = output['nextPageToken']
        search_response = youtube.search().list(
            part=part,
            q=q,
            order=order,
            type=type,
            maxResults=max_results,
            pageToken=next_page_token
        )
        output = search_response.execute()

    # 取得数をtotal_countに制限
    dic_list = dic_list[:total_count]
    df = pd.DataFrame(dic_list)

    # videoId 抽出
    df1 = pd.DataFrame(list(df['id']))['videoId']
    video_urls = "https://www.youtube.com/watch?v=" + df1

    # 動画の基本情報抽出
    df2 = pd.DataFrame(list(df['snippet']))[['channelTitle','publishedAt','channelId','title','description']]

    # 結合
    df_out = pd.concat([df1.rename("videoId"), video_urls.rename("videoUrl"), df2], axis=1)
    return df_out

# 統計情報を取得する関数
@st.cache_data
def get_statistics(id):
    try:
        stats = youtube.videos().list(part='statistics', id=id).execute()['items'][0]['statistics']
        return stats
    except:
        return {}  # 取得失敗時は空辞書

# サイドバーに検索条件入力フォームを配置
with st.sidebar:
    st.header("検索条件")
    
    # 検索キーワード入力
    search_query = st.text_input("検索キーワード", "金価格")
    
    # 表示件数選択
    total_count = st.slider("表示件数", min_value=10, max_value=200, value=50, step=10)
    
    # 並び順選択
    order_options = {
        '再生回数順': 'viewCount',
        '関連性順': 'relevance',
        'アップロード日時順': 'date',
        '評価順': 'rating'
    }
    order_selection = st.selectbox("並び順", list(order_options.keys()))
    order = order_options[order_selection]
    
    # 検索ボタン
    search_button = st.button("検索")

# 検索実行
if search_button or 'search_results' not in st.session_state:
    with st.spinner(f"「{search_query}」を検索中..."):
        # 検索実行
        df_out = get_video_info(part='snippet', q=search_query, order=order, type='video', total_count=total_count)
        
        # 統計情報取得
        st.text("動画の統計情報を取得中...")
        stats_list = []
        for vid in df_out['videoId']:
            stats_list.append(get_statistics(vid))
        
        df_static = pd.DataFrame(stats_list)
        df_output = pd.concat([df_out, df_static], axis=1)
        
        # 結果をセッションに保存
        st.session_state['search_results'] = df_output
        st.session_state['search_query'] = search_query

# 結果表示
if 'search_results' in st.session_state:
    st.header(f"「{st.session_state['search_query']}」の検索結果")
    
    # データフレーム表示
    st.dataframe(st.session_state['search_results'])
    
    # CSVダウンロード機能
    csv = st.session_state['search_results'].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="検索結果をCSVダウンロード",
        data=csv,
        file_name=f"youtube_search_{st.session_state['search_query']}.csv",
        mime="text/csv",
    )
    
    # 上位動画のプレビュー表示
    st.header("動画プレビュー")
    
    # 2列レイアウトで最大5件表示
    for i in range(0, min(5, len(st.session_state['search_results']))):
        row = st.session_state['search_results'].iloc[i]
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # サムネイル表示
            st.image(f"https://img.youtube.com/vi/{row['videoId']}/mqdefault.jpg")
        
        with col2:
            # 動画情報表示
            st.subheader(row['title'])
            st.write(f"チャンネル: {row['channelTitle']}")
            st.write(f"公開日: {row['publishedAt']}")
            
            # 統計情報表示
            if 'viewCount' in row:
                st.write(f"再生回数: {row.get('viewCount', '不明')}")
            if 'likeCount' in row:
                st.write(f"高評価数: {row.get('likeCount', '不明')}")
            
            # YouTube視聴リンク
            st.markdown(f"[YouTubeで視聴する]({row['videoUrl']})")
