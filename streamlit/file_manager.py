import os
import uuid
from datetime import datetime
from pathlib import Path

class FileManager:
    def __init__(self, base_dir="tmp"):
        self.base_dir = base_dir
        self._ensure_base_dirs()

    def _ensure_base_dirs(self):
        """确保基础目录结构存在"""
        Path(self.base_dir).mkdir(exist_ok=True)
        Path(self.base_dir, "videos").mkdir(exist_ok=True)

    def get_date_dir(self):
        """获取当天的日期目录"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        date_dir = Path(self.base_dir, "videos", date_str)
        date_dir.mkdir(exist_ok=True)
        return date_dir

    def generate_video_path(self, original_filename):
        """生成唯一的视频文件路径"""
        # 生成唯一文件名
        unique_id = str(uuid.uuid4())[:8]
        extension = Path(original_filename).suffix
        filename = f"{unique_id}{extension}"
        
        # 创建日期目录和帧目录
        date_dir = self.get_date_dir()
        frames_dir = date_dir / unique_id
        frames_dir.mkdir(exist_ok=True)
        
        return {
            'video_path': date_dir / filename,
            'frames_dir': frames_dir,
            'relative_video_path': str(Path("videos") / date_dir.name / filename),
            'relative_frames_dir': str(Path("videos") / date_dir.name / unique_id)
        }

    def save_video_file(self, file_content, original_filename):
        """保存视频文件并返回相关路径"""
        paths = self.generate_video_path(original_filename)
        
        # 写入文件
        with open(paths['video_path'], 'wb') as f:
            f.write(file_content)
        
        return paths

    def get_video_content(self, relative_path):
        """根据相对路径读取视频内容"""
        full_path = Path(self.base_dir) / relative_path
        if not full_path.exists():
            raise FileNotFoundError(f"Video file not found: {relative_path}")
            
        with open(full_path, 'rb') as f:
            return f.read()

    def save_frame(self, frames_dir, frame_number, image_data, is_gif=False):
        """保存帧图片"""
        frames_dir = Path(self.base_dir) / frames_dir
        if is_gif:
            filename = f"frame_{frame_number[0]:03d}-{frame_number[1]:03d}.gif"
        else:
            filename = f"frame_{frame_number:03d}.jpg"
        
        frame_path = frames_dir / filename
        image_data.save(frame_path)
        return str(Path(frames_dir.name) / filename)