import streamlit as st
import time
import re
import base64
import av
from io import BytesIO
from vertex_helper import analyze_video, create_imitation, translate_script, read_from_resource
from vertexai.generative_models import Part

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

    # 添加侧边栏
    st.sidebar.markdown("## 产品知识库")
    st.sidebar.selectbox("选择产品线", ["祛痘产品线"])

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
            process_video((file_contents, mime_type), is_url=False)
        else:
            st.warning("请提供视频 URL 或上传视频文件")

    # 显示解读结果
    if 'video_analysis' in st.session_state:
        st.markdown("## 视频解读结果")
        st.markdown(st.session_state['video_analysis'], unsafe_allow_html=True)

        # 显示模仿创作表单
        st.header("模仿创作")
        with st.form("imitation_form"):
            st.subheader("市场描述")
            country = st.text_input("国家 *", help="必填项")
            
            col1, col2 = st.columns(2)
            with col1:
                product_points = st.text_area("产品卖点", help="可选项")
            with col2:
                target_audience = st.text_area("目标人群描述", help="可选项")
            
            st.subheader("达人描述")
            col3, col4 = st.columns(2)
            with col3:
                skin_type = st.selectbox("皮肤类别", ["历史严重但现在改善", "油性肤质", "干性肤质"])
                ba_ability = st.selectbox("BA能力", ["Before爆款", "无Before爆款", "其他"])
                ba_ability_custom = st.text_input("自定义BA能力", help="如果上面选择'其他'，请在此输入自定义BA能力")
            with col4:
                voice_over_skill = st.selectbox("口播能力", ["强口播", "故事描述型"])
                image = st.selectbox("形象", ["美女", "帅哥", "其他"])
                image_custom = st.text_input("自定义形象", help="如果上面选择'其他'，请在此输入自定义形象描述")

            st.subheader("输出格式")
            target_language = st.selectbox("目标语言", ["中文", "英文", "印尼语", "泰语", "马来语", "越南语"])

            submitted = st.form_submit_button("开始创作")
        
        # 创作脚本显示在表单外部
        if submitted:
            if not country:
                st.error("请填写国家信息")
            else:
                # 处理BA能力和形象的选择
                final_ba_ability = ba_ability_custom if ba_ability == "其他" else ba_ability
                final_image = image_custom if image == "其他" else image
                start_creation(country, target_audience, product_points, skin_type, final_ba_ability, voice_over_skill, final_image, target_language)

    # 显示创作结果
    if 'creation_script' in st.session_state:
        st.markdown("## 模仿创作脚本")
        # 显示参考图片
        if 'video_source' in st.session_state:
            video_source = st.session_state['video_source']
            if isinstance(video_source, str):  # URL
                # URl模式中不支持显示参考图片
                st.markdown(st.session_state['creation_script'], unsafe_allow_html=True)
            else:  # Uploaded file
                file_contents, _ = video_source
                enhanced_script = enhance_script_with_img2(st.session_state['creation_script'], file_contents)
                st.markdown(enhanced_script, unsafe_allow_html=True)
        else:
            st.warning("视频源找不到")

        # 显示翻译功能
        st.header("翻译")
        target_lang = st.text_input("目标语言", value="英语")
        if st.button("翻译"):
            translated_script = start_translate(st.session_state['creation_script'], target_lang)

    # 显示翻译结果
    if 'translated_script' in st.session_state:
        st.markdown("### 翻译结果")
        st.markdown(st.session_state['translated_script'], unsafe_allow_html=True)


def process_video(source, is_url):
    with st.spinner('正在解读视频...'):
        if is_url:
            video_analysis = analyze_video(source, is_url)
        else:
            video_analysis = analyze_video_mock(source, is_url)
            # video_analysis = analyze_video(source, is_url)
        st.session_state['video_analysis'] = video_analysis
        st.session_state['video_source'] = source
    st.success('解读完成！')


def start_creation(country, target_audience, product_points, skin_type, ba_ability, voice_over_skill, image, target_language):
    input_data = {
        "country": country,
        "target_audience": target_audience,
        "product": product_points,
        "influencer_traits": {
            "skin_type": skin_type,
            "ba_ability": ba_ability,
            "voice_over_skill": voice_over_skill,
            "image": image
        },
        "target_language": target_language
    }
    
    with st.spinner('正在创作中...'):
        # creation_script = create_imitation_mock(st.session_state['video_analysis'], input_data)
        creation_script = create_imitation(st.session_state['video_analysis'], input_data)
        st.session_state['creation_script'] = creation_script
    st.success('创作完成！')


def start_translate(script, target_language):
    # 模拟翻译过程
    with st.spinner('正在翻译...'):
        # translated_script = translate_script_mock(script, target_language)
        translated_script = translate_script(script, target_language)
        st.session_state['translated_script'] = translated_script
    st.success('翻译完成！')
    return translated_script


def display_video_player(source):
    if isinstance(source, str):  # URL
        video_id = extract_video_id(source)
        if video_id:
            st.video(f"https://www.youtube.com/watch?v={video_id}")
        else:
            st.video(source)
    else:  # Uploaded file
        st.video(source)

def extract_video_id(url):
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    match = re.match(youtube_regex, url)
    return match.group(6) if match else None


# 返回第time_sec秒的画面image对象
def get_video_frame(video_bytes, time_sec):
    with av.open(BytesIO(video_bytes)) as container:
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
def get_video_frame_base64(video_bytes, time_sec):
    frame = get_video_frame(video_bytes, time_sec)
    if frame:
        buffered = BytesIO()
        frame.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None


def display_video_frame(video_bytes, second):
     # 使用st.image方法
    frame = get_video_frame(video_bytes, second)
    if frame:
        st.image(frame, caption=f'第 {second} 秒的帧 ', width=300)  # 设置图片宽度为300像素
    else:
        st.error('无法提取指定时间的帧')


def display_video_frame_base64(video_bytes, second):
     # 使用 base64 方法在 markdown 中显示图片
    frame_base64 = get_video_frame_base64(video_bytes, second)
    if frame_base64:
        st.markdown(f"## 第 {second} 秒的帧 (在 markdown 中使用 base64)")
        st.markdown(f"![frame](data:image/png;base64,{frame_base64})")
    else:
        st.error('无法提取指定时间的帧 (base64 方法)')


# 处理脚本中出现的参考画面
def enhance_script_with_img(script):
    # 使用两个不同的模式来匹配两种格式
    pattern1 = r'<参考画面>(\d+)-(\d+)</参考画面>'
    pattern2 = r'<参考画面>(\d{2}:\d{2})-(\d{2}:\d{2})</参考画面>'
    
    matches1 = re.findall(pattern1, script)
    matches2 = re.findall(pattern2, script)
    
    reference_frames = []
    
    # 处理简单数字格式
    for start_time, end_time in matches1:
        start_seconds = int(start_time)
        end_seconds = int(end_time)
        mid_time = (start_seconds + end_seconds) / 2
        reference_frames.append(mid_time)
    
    # 处理时:分格式
    for start_time, end_time in matches2:
        start_seconds = convert_to_seconds(start_time)
        end_seconds = convert_to_seconds(end_time)
        mid_time = (start_seconds + end_seconds) / 2
        reference_frames.append(mid_time)
    
    return reference_frames

def convert_to_seconds(time_str):
    minutes, seconds = map(int, time_str.split(':'))
    return minutes * 60 + seconds


def enhance_script_with_img2(script, video_bytes):
    # 使用两个不同的模式来匹配两种格式
    pattern1 = r'<参考画面>(\d+)-(\d+)</参考画面>'
    pattern2 = r'<参考画面>(\d{2}:\d{2})-(\d{2}:\d{2})</参考画面>'
    
    def replace_with_image(match):
        start, end = match.groups()
        if ':' in start:
            start_seconds = convert_to_seconds(start)
            end_seconds = convert_to_seconds(end)
        else:
            start_seconds = int(start)
            end_seconds = int(end)
        
        mid_time = (start_seconds + end_seconds) / 2
        frame_base64 = get_video_frame_base64(video_bytes, mid_time)
        
        if frame_base64:
            return f'<img src="data:image/png;base64,{frame_base64}" style="width: 100px;" alt="第{mid_time}秒的帧">'
        else:
            return match.group(0)  # 如果无法获取图片,保留原始标记
    
    # 替换两种格式的参考画面标记
    new_script = re.sub(pattern1, replace_with_image, script)
    new_script = re.sub(pattern2, replace_with_image, new_script)
    
    return new_script


# mock method
def analyze_video_mock(source, is_url):
    # 模拟解读过程
    time.sleep(1)  # 模拟耗时操作
    source_type = "URL" if is_url else "上传文件"

    file_contents, mime_type = source
    display_video_frame(file_contents,  50)

    script_analysis_sample = read_from_resource('prompt/script-analysis-sample.md')
     
    mock_analysis = f"""
    这是一个示例视频解读结果（{source_type}）。
    使用markdown语法显示图片
    ![frame](data:image/png;base64,{get_video_frame_base64(file_contents, 10)})

    使用html显示图片
    <img src="data:image/png;base64,{get_video_frame_base64(file_contents, 10)}" style="width: 50%; max-width: 300px;" alt="第10秒的帧">
    """
    return script_analysis_sample

# mock method
def create_imitation_mock(analysis, input_data):
    # 模拟创作过程
    time.sleep(3)  # 模拟耗时操作

    outline_km_path = 'prompt/短视频脚本创作框架 V3 (专注于祛痘护肤产品-LLM版).md'
    try:
        with open(outline_km_path, 'r', encoding='utf-8') as f:
            outline_km = f.read()
    except UnicodeDecodeError:
        # 如果 UTF-8 失败，尝试其他编码
        with open(outline_km_path, 'r', encoding='gbk') as f:
                outline_km = f.read()

    file_contents, mime_type = st.session_state['video_source']

    return f"""
    基于原视频的结构和您提供的信息，以下是一个模仿创作的脚本大纲：

    国家：{input_data['country']}
    目标受众：{input_data['target_audience']}
    产品卖点：{input_data['product']}
    目标语言：{input_data['target_language']}

    达人描述：
    - 皮肤类别：{input_data['influencer_traits']['skin_type']}
    - BA能力：{input_data['influencer_traits']['ba_ability']}
    - 口播能力：{input_data['influencer_traits']['voice_over_skill']}
    - 形象：{input_data['influencer_traits']['image']}

## 分镜脚本

| 序号 | 画面内容 | 时长 | 字幕 (旁白台词) | 画面特点 | 目的&意义&必要性 | 参考时间节点 |
|------|----------|------|----------------|----------|------------------|--------------|
| 1 | 黑白色调, 近景特写达人无奈的印象 | 2秒 | 你是否也苦恼居印问题呢? | 使用参考脚本00:01-00:03的画面特写, 达到处理成黑白画面. 突出居印问题 | 主题设定: 快速吸引目标受众, 引起共鸣 | 00:01-00:03 |
| 2 | 黑白色调, 中景拍摄达人运倩画面, 神情失落 | 2秒 | 无法自信地面对他人 | 展现居印问题对生活的负面影响, 引发情感共鸣 | 问题呈现: 深化痛点, 为产品解决方案做铺垫 | <参考画面>1-3</参考画面> |
| 3 | 彩色画面, 产品包装盒特写, 突出产品名称 | 2秒 | XXX好居产品, 你的居印放心! | 产品包装画面走大方, 使用动画文字突出产品名 | 产品介绍: 引入解决方案, 激发观众兴趣 | <参考画面>00:10-00:12</参考画面> |
| 4 | 左侧为达人使用产品前的照片, 右侧为达人使用产品后的照片 | 3秒 | 使用前 VS 使用后效果看得见! | 使用前后效果对比, 突出使用产品前后居印的改变 | 效果展示: 直观展示产品效果, 增强说服�� | <img src="data:image/png;base64,{get_video_frame_base64(file_contents, 10)}" style="width: 100px;" alt="第10秒的帧"> |
| 5 | 近景特写, 达人手持产品, 演示使用方法 | 2秒 | 使用方法简单, 快速吸收! | 画面清晰流畅, 突出产品使用方法易吸收 | 使用演示: 降低使用门槛, 增强产品吸引力 | <参考画面>00:55-00:57</参考画面> |
| 6 | 彩色画面, 近景拍摄达人面部, 肤色均匀亮泽 | 2秒 | 居印改化, 肌肤重现光彩 | 达人面部特写, 展现使用产品后健康自信的肌肤状态 | 效果展示: 强化产品价值, 刺激购买欲望 |  |
| 7 | 彩色画面, 全景拍摄达人自信地走在街上 | 2秒 | 找回自信, 拥抱更美好的生活! | 画面明亮充满活力, 展现达人积极向上的生活状态 | 情感升华: 将产品与自信美好生活紧密联系 |  |

核心结构: 居印问题B+产品适度特写+BA对比+近景使用+全景BA人生活方式GA+CTA

<img src="data:image/png;base64,{get_video_frame_base64(file_contents, 10)}" style="width: 50%; max-width: 300px;" alt="第10秒的帧">

    """


# mock method 
def translate_script_mock(script, target_language):
     # 模拟耗时操作
    time.sleep(1) 
    return f"""
    这是一个模拟的翻译结果（目标语言：{target_language}）：

    Based on the original video structure and the information you provided, here's an outline for an imitation script:

    Country: [Translated country name]
    Target audience: [Translated target audience description]
    Product selling points: [Translated product points]
    Target language: {target_language}

    Influencer description:
    - Skin type: [Translated skin type]
    - BA ability: [Translated BA ability]
    - Voice-over skill: [Translated voice-over skill]
    - Image: [Translated image description]

    1. Opening (0:00 - 0:30)
       - Introduce the influencer and product background

    2. Product showcase (0:30 - 2:00)
       - Highlight product selling points

    3. Personal usage experience (2:00 - 3:30)
       - Combine influencer characteristics and skin type

    4. Target audience suitability analysis (3:30 - 4:30)
       - Specific advice for the target audience

    5. Summary and call-to-action (4:30 - 5:00)
       - Emphasize product advantages, encourage purchase

    ![Product Image](https://example.com/product_image.jpg)
    """


if __name__ == "__main__":
    main()

