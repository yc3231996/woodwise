import streamlit as st
import time
import re
import base64
import av
from io import BytesIO
from vertex_helper import analyze_video, create_script, translate_script, read_from_resource
from vertexai.generative_models import Part
import json
from file_manager import FileManager
from media_helper import create_gif
import os

# 添加密码保护
def check_password():
    """返回`True` 如果用户输入了正确的密码."""
    def password_entered():
        """检查是否输入了正确的密码."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 不要在会话状态中存储密码
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 第一次运行，显示输入框
        st.text_input(
            "密码", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # 密码错误，再次显示输入框
        st.text_input(
            "密码", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 密码错误")
        return False
    else:
        # 密码正确
        return True

def main():
    st.set_page_config(page_title="视频解读和创作", layout="wide")

    # 如果密码不正确，不显示应用内容
    if not check_password():
        st.stop()

    # # 添加侧边栏
    # st.sidebar.markdown("## 产品知识库")
    # st.session_state['selected_product'] = st.sidebar.selectbox("选择产品线", ["祛痘", "泥膜", "洗面奶", "隔离", "双管洁面"], disabled=True)

    st.title("视频解读和创作")
    # 视频输入选项卡
    tab1, tab2 = st.tabs(["上传视频", "视频 URL"])
    with tab1:
        uploaded_file = st.file_uploader("上传你的视频", type=["mp4", "mov", "avi"], help="支持的格式：MP4, MOV, AVI")
    with tab2:
        video_url = st.text_input("请提供视频链接", placeholder="https://...", disabled=True)
        st.info("视频URL功能暂时不可用")

    # 解读按钮
    if st.button("解读视频"):
        if video_url:
            process_video(video_url, is_url=True)
        elif uploaded_file:
            file_contents = uploaded_file.read()
            mime_type = uploaded_file.type
            file_name = uploaded_file.name
            process_video((file_contents, mime_type, file_name), is_url=False)
        else:
            st.warning("请提供视频 URL 或上传视频文件")

    lang_info = st.text_input(label="翻译指令", value="翻译成英文")
    if st.button("翻译脚本"):
        if 'video_analysis' in st.session_state:
            start_translate(st.session_state['video_analysis'], lang_info)
        else:
            st.info("请先解读视频")

    if st.button("显示翻译前的脚本"):
        if 'video_analysis' in st.session_state:
            st.markdown(st.session_state['video_analysis'], unsafe_allow_html=True)

    if st.button("显示翻译后的脚本"):
        if 'translated_script' in st.session_state:
            st.markdown(st.session_state['translated_script'], unsafe_allow_html=True)
        elif 'video_analysis' in st.session_state:
            st.markdown(st.session_state['video_analysis'], unsafe_allow_html=True)


def process_video(source, is_url):
     # 创建一个空的容器用于显示流式输出
    output_container = st.empty()
    # 用于累积完整的响应
    full_response = ""
    new_full_script= ""

    with st.spinner('正在解读视频...'):
        file_contents, mime_type, file_name = source

        # save video to temp path for later use
        file_manager = FileManager()
        paths = file_manager.save_video_file(file_contents, file_name)

        # 在session中只存储s视频文件路径
        st.session_state['video_path'] = paths['relative_video_path']
        st.session_state['frames_dir'] = paths['relative_frames_dir']

        ## mock
        # new_full_script = analyze_video_mock(source, is_url)
        # output_container.markdown(full_response, unsafe_allow_html=True)

        responses = analyze_video(source, is_url)
        for response in responses:
            chunk = response.text
            full_response += chunk
            output_container.markdown(full_response, unsafe_allow_html=True)

        # when response is done, try to enhance result with images
        with st.spinner('正在生成参考图片...'):
            new_full_script = enhance_script_with_img(full_response)
            output_container.markdown(new_full_script, unsafe_allow_html=True)

        st.session_state['video_analysis'] = new_full_script

    st.success('解读完成！')


def start_creation(inspiration : str):
    with st.spinner('正在创作中...'):
        created_script = create_script_mock(st.session_state['imitated_script'], inspiration)
        st.session_state['created_script'] = created_script
    st.success('创作完成！')


def start_translate(script, lang_info):
    with st.spinner('正在翻译...'):
        # translated_script = translate_script_mock(script, target_language)
        translated_script = translate_script(script, lang_info)
    st.success('翻译完成！')
    st.session_state['translated_script'] = translated_script
    st.markdown(translated_script, unsafe_allow_html=True)
    return translated_script


# 返回第time_sec秒的画面image对象
def get_video_frame(time_sec):
    file_manager = FileManager()
    video_content = file_manager.get_video_content(st.session_state['video_path'])  # 临时加载到内存
    with av.open(BytesIO(video_content)) as container:
        stream = container.streams.video[0]
        
        # 设置时间戳
        pts = int(time_sec * stream.time_base.denominator / stream.time_base.numerator)
        
        # 使用更高效的方式定位和解码
        container.seek(pts, stream=stream, any_frame=False)
        
        # 只解码目标位置附近的帧
        for frame in container.decode(video=0):
            # 检查帧的显示时间是否接近目标时间
            frame_time = float(frame.pts * stream.time_base)
            if abs(frame_time - time_sec) < 0.1:  # 允许0.1秒的误差
                return frame.to_image()
        
        return None


# 返回第time_sec秒的画面的base64字符串
def get_video_frame_base64(time_sec):
    frame = get_video_frame( time_sec)
    if frame:
        buffered = BytesIO()
        frame.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None


def display_video_frame(second):
     # 使用st.image方法
    frame = get_video_frame(second)
    if frame:
        st.image(frame, caption=f'第 {second} 秒的帧 ', width=300)  # 设置图片宽度为300像素
    else:
        st.error('无法提取指定时间的帧')


# 获取脚本中出现的参考画面
def get_img_clip(script):
    # 使用两个不同的模式来匹配两种格式
    pattern1 = r'<参考画面>(\d+)-(\d+)</参考画面>'
    pattern2 = r'<参考画面>(\d{2}:\d{2})-(\d{2}:\d{2})</参考画面>'
    
    matches1 = re.findall(pattern1, script)
    matches2 = re.findall(pattern2, script)
    
    reference_frames = []
    
    # 处理简单数字格式
    for start_time, end_time in matches1:
        reference_frames.append({
            'start': int(start_time),
            'end': int(end_time)
        })
    
    # 处理时:分格式
    for start_time, end_time in matches2:
        reference_frames.append({
            'start': convert_to_seconds(start_time),
            'end': convert_to_seconds(end_time)
        })
    
    return reference_frames

def convert_to_seconds(time_str):
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds


def create_gif_for_script(script):
    # 获取脚本中的所有参考画面时间段
    reference_frames = get_img_clip(script)
    
    # 如果没有找到参考画面，直接返回
    if not reference_frames:
        return [], []
    
    file_manager = FileManager()
    gif_paths = []
    
    # 获取视频内容
    video_content = file_manager.get_video_content(st.session_state['video_path'])
    full_frame_dir = file_manager.get_frame_dir(st.session_state['frames_dir'])
    
    # 为每个时间区间创建GIF
    for frame in reference_frames:
        try:
            # 调用create_gif函数生成GIF
            gif_path = create_gif(
                video_bytes=video_content,
                output_path=f"{full_frame_dir}/frame_{frame['start']}_{frame['end']}.gif",
                start_time=frame['start'],
                end_time=frame['end'],
                fps=10,
                target_width=320
            )
            
            if gif_path:
                gif_paths.append(gif_path)
                
        except Exception as e:
            st.error(f"创建GIF时出错: {str(e)}")
            continue
    
    return reference_frames, gif_paths


def enhance_script_with_img(script):
    # 获取所有参考画面时间段和对应的GIF
    reference_frames, gifs = create_gif_for_script(script)
    
    # 创建时间段到GIF路径的映射
    time_to_gif = {}
    for frame, gif_path in zip(reference_frames, gifs):
        key = f"{frame['start']}-{frame['end']}"
        time_to_gif[key] = '/app/' + gif_path

    # 使用两个不同的模式来匹配两种格式
    pattern1 = r'<参考画面>(\d+)-(\d+)</参考画面>'
    pattern2 = r'<参考画面>(\d{2}:\d{2})-(\d{2}:\d{2})</参考画面>'
    
    def replace_with_gif(match):
        start, end = match.groups()
        if ':' in start:
            # 转换时:分格式为秒
            start_seconds = convert_to_seconds(start)
            end_seconds = convert_to_seconds(end)
        else:
            start_seconds = int(start)
            end_seconds = int(end)
        
        # 查找对应的GIF路径
        key = f"{start_seconds}-{end_seconds}"
        if key in time_to_gif:
            return f'<img src="{time_to_gif[key]}" style="width: 200px;" alt="时间段 {start_seconds}s-{end_seconds}s 的GIF">'
        else:
            return match.group(0)  # 如果找不到对应的GIF，保留原始标记
    
    # 替换两种格式的参考画面标记
    new_script = re.sub(pattern1, replace_with_gif, script)
    new_script = re.sub(pattern2, replace_with_gif, new_script)
    
    return new_script


def display_reference_gifs(script):
    reference_frames, gifs = create_gif_for_script(script)
    if reference_frames and gifs:
        st.subheader("参考画面")

        for frame, gif_path in zip(reference_frames, gifs):
            full_path = '/app/' + gif_path
            st.write(f"""
                <div>
                    <p>{frame['start']}s - {frame['end']}s</p>
                    <img src="{full_path}" style="width: 150px" alt="参考画面"/>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.warning("视频源找不到")


# mock method
def analyze_video_mock(source, is_url):
    # 模拟解读过程
    time.sleep(1)  # 模拟耗时操作
    source_type = "URL" if is_url else "上传文件"

    file_contents, mime_type, file_name = source
    # display_video_frame(20)

    st.info(st.session_state['video_path'])
    st.info(st.session_state['frames_dir'])
    # st.video(file_contents, start_time=10, end_time=15, )

    script_analysis_sample = read_from_resource('prompt/script-analysis-mock.md')

    return script_analysis_sample

# mock method
def create_imitation_mock(analysis, input_data):
    # 模拟模仿过程
    time.sleep(2) 

    outline_km_path = 'prompt/短视频脚本创作框架 V3 (专注于祛痘护肤产品-LLM版).md'
    try:
        with open(outline_km_path, 'r', encoding='utf-8') as f:
            outline_km = f.read()
    except UnicodeDecodeError:
        # 如果 UTF-8 失败，尝试其他编码
        with open(outline_km_path, 'r', encoding='gbk') as f:
            outline_km = f.read()

    return f"""
    基于原视频的结构和您提供的信息，以下是一个模仿创作的脚本大纲：
    <img src="data:image/png;base64,{get_video_frame_base64(file_contents, 10)}" style="width: 50%; max-width: 300px;" alt="第10秒的帧">
    """


# create script mock
def create_script_mock(imitated_script, inspiration):
    # 模拟创作过程
    time.sleep(2)  # 模拟耗时操作
    return "created script"


# mock method 
def translate_script_mock(script, target_language):
     # 模拟耗时操作
    time.sleep(1) 
    return f"""
    这是一个模拟的翻译结果（目标语言：{target_language}）：
    Country: [Translated country name]
    Target audience: [Translated target audience description]
    Product selling points: [Translated product points]
    Target language: {target_language}

    Influencer description:
    - Skin type: [Translated skin type]

    1. Opening (0:00 - 0:30)
       - Introduce the influencer and product background

    2. Product showcase (0:30 - 2:00)
       - Highlight product selling points

    3. Personal usage experience (2:00 - 3:30)
       - Combine influencer characteristics and skin type

    ![Product Image](https://example.com/product_image.jpg)
    """


if __name__ == "__main__":
    main()

