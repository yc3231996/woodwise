import streamlit as st
import time
import re
import base64
import av
from io import BytesIO
from vertex_helper import analyze_video, upload_to_gcs, create_script, translate_script, read_from_resource
from vertexai.generative_models import Part
import json
from file_manager import FileManager
from media_helper import create_gif
import os
from sql_manager import SQLManager

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
    st.title("视频解读和创作")

    # 如果密码不正确，不显示应用内容
    if not check_password():
        st.stop()

    # 添加侧边栏
    # 视频上传区域
    st.sidebar.title("上传视频")
    upload_option = st.sidebar.radio("选择上传方式", options=["上传视频", "视频 URL"], horizontal=True, disabled=True)

    if upload_option == "上传视频":
        uploaded_file = st.sidebar.file_uploader("上传你的视频", type=["mp4"], help="支持的格式: MP4", key="file_uploader_sidebar")
    elif upload_option == "视频 URL":
        video_url = st.sidebar.text_input("请提供视频链接 (暂不可用)", placeholder="https://...", disabled=True, key="text_input_video_url_sidebar")

    # 产品信息选择区
    st.sidebar.divider()
    st.sidebar.markdown("## 产品信息：")
    selected_product = st.sidebar.selectbox("选择产品线", ["祛痘产品", "清洁面膜", "洗面奶", "隔离霜", "美白面霜", "美白精华", "防晒霜", "舒缓修复凝胶", "补水面膜"], index=None)
    # 默认产品信息
    product_info = load_product_info(selected_product) if selected_product else ""
    # 允许用户输入自定义产品信息
    user_input_info = st.sidebar.text_area("产品信息", product_info, height=250)
    # 更新session状态，保存用户输入的产品信息
    st.session_state['selected_product'] = selected_product
    st.session_state['product_info'] = user_input_info

    # 翻译功能区
    st.sidebar.divider()

    # 历史记录区
    st.sidebar.markdown("## 历史记录：")
    current_user = "test" # TODO need to enhance to get from session
    # history_container = st.sidebar.container()
    # records = get_manager().get_threads_by_user(current_user) # TODO， 需要一个值返回video path的方法，否则全部的内容过大
    # with history_container:
    #     for record in records:
    #         history_container.markdown(f"**Video Path:** {record['video_path']}", unsafe_allow_html=True)
    

    # 主布局区：解读结果区要用empty占位符，因为流式输出之后，需要用gif替换过的新结果覆盖原来的结果
    tools_container = st.container()
    analysis_container = st.empty()

    with tools_container:
        btn1 = st.button("解读视频")
        btn2 = st.button("创作新脚本")
        if btn1:
            if uploaded_file:
                process_video(uploaded_file, is_url=False, output_container=analysis_container)
            # elif video_url:
            #     process_video(video_url, is_url=True)
            else:
                st.warning("请提供视频 URL 或上传视频文件")

        if btn2:
            # 检查selected_product和product_info在session中，且不为空
            if st.session_state.get("selected_product") and st.session_state.get("product_info") :
                start_creation(product_info)
            else:
                st.info("请选择产品线开始创作")
    
        with st.expander("翻译"):
            with st.form(key='translation_form'):
                lang_info = st.text_input(label="目标语言", value="翻译成英文")
                translation_option = st.radio("选择翻译内容", options=["视频解读", "新创作的脚本"])
                submit_button = st.form_submit_button("开始翻译")
                
                if submit_button:
                    if translation_option == "视频解读" and 'video_analysis' in st.session_state:
                        start_translate(st.session_state['video_analysis'], lang_info)
                    elif translation_option == "新创作的脚本" and 'created_script' in st.session_state:
                        start_translate(st.session_state['created_script'], lang_info)
                    else:
                        st.warning("请先解读视频或创作新脚本")


    if 'video_analysis' in st.session_state:
        analysis_container.markdown(st.session_state['video_analysis'], unsafe_allow_html=True)
        # st.download_button(label="下载短视频解读", data=st.session_state['video_analysis'], file_name="video_analysis.md", mime="text/markdown")
    
    if 'created_script' in st.session_state:
        st.markdown("-----")
        st.markdown("# 创作结果：")
        st.markdown(st.session_state['created_script'], unsafe_allow_html=True)
        # st.download_button(label="下载新创作的脚本", data=st.session_state['created_script'], file_name="test.md", mime="text/markdown")    

    if 'translated_script' in st.session_state:
        st.markdown("-----")
        st.markdown("# 翻译结果：")
        st.markdown(st.session_state['translated_script'], unsafe_allow_html=True)
        # st.download_button(label="下载翻译", data=st.session_state['translated_script'], file_name="translated_script.md", mime="text/markdown")

    # save contents to database
    if 'video_path' in st.session_state:
        thread = {
            "thread_id": st.session_state['video_path'],
            "user": current_user,
            "video_path": st.session_state.get('video_path', ''),
            "video_info": st.session_state.get('video_info', ''),
            "video_analysis": st.session_state.get('video_analysis', ''),
            "created_script": st.session_state.get('created_script', ''),
            "translated_script": st.session_state.get('translated_script', ''),
            "others": ""
        }
        get_manager().upsert_thread(thread)

    
    # chat area for experimental
    if chat_input := st.chat_input():
        st.chat_message("Assistant").write(chat_input)



def process_video(source, is_url, output_container):
     # 创建一个空的容器用于显示流式输出
    # output_container = st.empty()

    # 用于累积完整的响应
    full_response = ""
    new_full_script= ""
    
    with st.spinner('正在解读视频...'):
        ## TODO, only support file upload case for now
        file_contents = source.read()
        mime_type = source.type
        file_name = source.name

        # save video to temp path for later use
        file_manager = FileManager()
        paths = file_manager.save_video_file(file_contents, file_name)

        # 在session中只存储视频文件路径，不存储视频本身
        st.session_state['video_path'] = paths['relative_video_path']
        st.session_state['frames_dir'] = paths['relative_frames_dir']

        if DEBUG:
            # mock
            full_response = analyze_video_mock()
            output_container.markdown(full_response, unsafe_allow_html=True)
        else:
            if source.size > 5 * 1024 * 1024:
                 # 对于大文件，上传到GCS
                 file_gcs_uri = upload_to_gcs(source)
                 responses = analyze_video(file_gcs_uri, True, mime_type)
            else:
                responses = analyze_video(file_contents, False, mime_type)

            # streaming response
            for response in responses:
                chunk = response.text
                full_response += chunk
                output_container.markdown(full_response, unsafe_allow_html=True)

        # when response is done, try to enhance result with images
        with st.spinner('正在生成参考图片...'):
            new_full_script = enhance_script_with_img(full_response)

        # put result in session for later use
        st.session_state['video_analysis'] = new_full_script

    st.success('解读完成！')


def start_creation(product_info : str):
    if 'video_analysis' not in st.session_state:
        st.warning("请先创作新的视频脚本！")
    else:
        with st.spinner('正在创作中...'):
            if DEBUG:
                created_script = create_script_mock(st.session_state['video_analysis'], product_info)
            else:
                created_script = create_script(st.session_state['video_analysis'], product_info)

        st.success('创作完成！')
        st.session_state['created_script'] = created_script
        return created_script


def start_translate(script, lang_info):
    with st.spinner('正在翻译...'):
        if DEBUG:
            translated_script = translate_script_mock(script, lang_info)
        else:
            translated_script = translate_script(script, lang_info)

    st.success('翻译完成！')
    st.session_state['translated_script'] = translated_script
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
    # 生成GIF，获取参考画面时间段和对应的GIF
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


# 缓存文件读取
@st.cache_data
def load_product_info(product_name):
    try:
        with open(f"prompt/{product_name}.md", "r", encoding="utf-8") as file:
            return file.read()  # 读取文件内容并返回
    except FileNotFoundError:
        return ""  # 文件不存在时，返回空字符串


@st.cache_resource
def get_manager():
    return SQLManager()


# mock method
def analyze_video_mock():
    # 模拟解读过程
    time.sleep(1) 

    # file_contents, mime_type, file_name = source
    # display_video_frame(20)

    st.info(st.session_state['video_path'])
    st.info(st.session_state['frames_dir'])
    # st.video(file_contents, start_time=10, end_time=15, )

    script_analysis_sample = read_from_resource('prompt/script-analysis-mock.md')

    # return script_analysis_sample
    return "this is a test result"

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
def create_script_mock(imitated_script, product_info):
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
    DEBUG = False
    main()

