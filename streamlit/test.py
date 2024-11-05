import av
from PIL import Image
from io import BytesIO
import streamlit as st
def create_gif_with_av(video_bytes, start_time, end_time, fps=10, target_width=320):
    """
    使用 PyAV 创建 GIF
    
    参数:
        video_bytes: 视频文件的字节内容
        start_time: 开始时间(秒)
        end_time: 结束时间(秒)
        fps: GIF的帧率
        target_width: 目标宽度
    """
    frames = []
    
    # 创建内存中的视频容器
    container = av.open(BytesIO(video_bytes))
    stream = container.streams.video[0]
    
    # 计算目标高度，保持宽高比
    target_height = int(stream.height * (target_width / stream.width))
    
    # 计算时间戳
    stream_timebase = stream.time_base
    start_ts = int(start_time / stream_timebase)
    end_ts = int(end_time / stream_timebase)
    
    try:
        # 设置容器的起始位置
        container.seek(start_ts, stream=stream)
        
        # 计算帧间隔（基于目标fps）
        frame_interval = 1.0 / fps
        next_frame_time = start_time
        
        for frame in container.decode(video=0):
            # 计算当前帧的时间
            current_time = float(frame.pts * stream_timebase)
            
            if current_time < start_time:
                continue
            if current_time > end_time:
                break
                
            # 控制帧率
            if current_time >= next_frame_time:
                # 将 frame 转换为 PIL Image
                img = frame.to_image()
                
                # 调整大小
                img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                
                frames.append(img)
                next_frame_time += frame_interval
            
    finally:
        container.close()
    
    if not frames:
        raise ValueError("没有帧被捕获")
    
    # 创建 GIF
    gif_buffer = BytesIO()
    frames[0].save(
        gif_buffer,
        format='GIF',
        save_all=True,
        append_images=frames[1:],
        duration=int(1000/fps),  # 毫秒
        loop=0,
        optimize=True
    )
    gif_buffer.seek(0)
    
    return gif_buffer

# Streamlit 使用示例
def main():
    st.title("视频片段GIF预览")
    
    uploaded_file = st.file_uploader("选择视频文件", type=['mp4', 'mov', 'avi'])
    
    if uploaded_file is not None:
        video_bytes = uploaded_file.read()
        
        try:
            gif_buffer = create_gif_with_av(
                video_bytes,
                start_time=1.0,
                end_time=3.0,
                fps=10,
                target_width=320
            )
            
            # 显示 GIF
            st.image(gif_buffer, caption="1-3秒片段预览")
            
        except Exception as e:
            st.error(f"生成GIF时发生错误: {str(e)}")

if __name__ == "__main__":
    main()