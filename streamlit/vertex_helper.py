from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import os
from http_helper import call_workflow_api
import logging
from datetime import datetime
from google.cloud import storage

# 全局配置
generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0.8,
    "top_p": 0.95,
}
safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.OFF
    ),
]

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def initialize_vertexai():
  # cred = service_account.Credentials.from_service_account_file("config/gen-lang-client.json")
  # vertexai.init(project="gen-lang-client-0786739350", location="us-central1", credentials=cred)

  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/gen-lang-client.json'
  vertexai_location = os.getenv('VERTEXAI_LOCATION', 'asia-southeast1')
  vertexai.init(project="gen-lang-client-0786739350", location=vertexai_location)

  return "Vertex AI initialized"

# 在模块级别调用初始化函数
initialize_vertexai()


# analysis video, if is_url is false,  source is file contents
def analyze_video(source, is_url, mime_type="video/mp4"):
  if is_url:
    ## TODO, check to see if source is a public url or GCS uri, assume all GCS uri for the moment
    video_file_uri = f"gs://{source}"
    video_file_url = f"https://storage.cloud.google.com/{source}"
    video_file = Part.from_uri(video_file_uri, mime_type)
  else:
    video_file = Part.from_data(
      mime_type=mime_type,
      data=source
    )

  prompt_read_video = read_from_resource('prompt/video_analysis_prompt.md')
  contents = [video_file, prompt_read_video]

  model = GenerativeModel("gemini-1.5-flash-002")
  responses  = model.generate_content(contents, generation_config=generation_config, safety_settings=safety_settings, stream=True)
  return responses


def create_script(sample_script, input_data):
  input_obj = {
    "script_sample": str(sample_script),
    "product_info": str(input_data)
  }
  result = call_workflow_api(input_obj)
  return result['script_created']


def translate_script(sample_script, input_data):
  input_obj = {
    "script_sample": str(sample_script),
    "lang_info": str(input_data)
  }
  result = call_workflow_api(input_obj)
  return result['script_translated']


def translate_script_local(script, target_language):
  prompt_translate = f"""
  把下面文本翻译成目标语言包 {target_language}, 要求符合目标语言国家的口语习惯，符合tiktok短视频的表达方式。并保持输出格式和原文完全一致。

  文本：
  {script}
  """

  model = GenerativeModel("gemini-1.5-pro")
  response = model.generate_content([prompt_translate], generation_config=generation_config, safety_settings=safety_settings,)
  return response.text


def read_from_resource(file_path):
  try:
    with open(file_path, 'r', encoding='utf-8') as f:
      file_content = f.read()
  except UnicodeDecodeError:
      # 如果 UTF-8 失败，尝试其他编码
    with open(file_path, 'r', encoding='gbk') as f:
      file_content = f.read()
  return file_content


def upload_to_gcs(uploaded_file):
    """
    将Streamlit上传的文件保存到Google Cloud Storage
    
    Args:
        uploaded_file: Streamlit的UploadedFile对象
        
    Returns:
        str: 文件在GCS中的URI
    """
    bucket_name = os.getenv('GCS_BUCKET_NAME', 'shorts_analysis')
    
    try:
        # 创建storage客户端
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        
        # 生成唯一的blob名称
        now = datetime.now()
        date = now.strftime('%Y%m%d')
        time = now.strftime('%H%M%S')
        blob_name = f"videos/{date}/{time}_{uploaded_file.name}"
        
        # 创建新的blob并上传文件
        blob = bucket.blob(blob_name)
        
        # 重置文件流到开头
        uploaded_file.seek(0)
        
        blob.upload_from_file(uploaded_file, timeout=300)
        
        # 返回GCS URI: "gs://{bucket_name}/{blob_name}"
        gcs_uri = f"{bucket_name}/{blob_name}"
        return gcs_uri
        
    except Exception as e:
        logging.error(f"上传文件到GCS时发生错误: {str(e)}")
        raise e



if __name__ == "__main__":
    prompt_test = f"tell me a long jok"

    initialize_vertexai()
    
    model = GenerativeModel("gemini-1.5-flash-002")
    responses = model.generate_content(
        [prompt_test],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )
    
    for response in responses:
        print(response.text)

