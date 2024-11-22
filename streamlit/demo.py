import streamlit as st

# 模拟视频片段数据，每个片段包含缩略图路径、开始时间和结束时间
segments = [
    {"frame_path": "https://via.placeholder.com/150", "start_time": "00:00", "end_time": "00:05"},
    {"frame_path": "https://via.placeholder.com/150", "start_time": "00:05", "end_time": "00:10"},
    {"frame_path": "https://via.placeholder.com/150", "start_time": "00:10", "end_time": "00:15"},
    {"frame_path": "https://via.placeholder.com/150", "start_time": "00:15", "end_time": "00:20"},
]

# 设置页面标题
st.set_page_config(page_title="视频剪辑时间轴示例", layout="wide")
st.title("视频剪辑时间轴示例")

# 创建时间轴
st.subheader("时间轴展示")
cols = st.columns(len(segments))

# 在每列中展示片段信息
for i, segment in enumerate(segments):
    with cols[i]:
        st.image(segment["frame_path"], caption=f"{segment['start_time']} - {segment['end_time']}")
        if st.button(f"播放 {segment['start_time']}", key=f"play_{i}"):
            st.write(f"播放片段: {segment['start_time']} - {segment['end_time']}")

# 添加自定义样式，模拟剪辑软件风格
st.markdown("""
<style>
.time-segment {
    display: inline-block;
    text-align: center;
    margin: 5px;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 10px;
    width: 150px;
}
.time-segment img {
    max-width: 100%;
    border-radius: 5px;
}
.time-segment:hover {
    background-color: #f0f0f0;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# 使用 HTML 和 CSS 展示时间轴
st.markdown('<div style="display: flex;">', unsafe_allow_html=True)
for segment in segments:
    st.markdown(f"""
    <div class="time-segment">
        <img src="{segment['frame_path']}" alt="Frame">
        <p>{segment['start_time']} - {segment['end_time']}</p>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 用户选择播放片段
times = [f"{seg['start_time']} - {seg['end_time']}" for seg in segments]
selected_segment = st.selectbox("选择播放片段", times)

if st.button("播放所选片段"):
    st.write(f"播放片段: {selected_segment}")
