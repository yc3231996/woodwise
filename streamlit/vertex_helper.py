from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import os
import base64
from http_helper import call_workflow_api

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


def initialize_vertexai():
  # cred = service_account.Credentials.from_service_account_file("config/gen-lang-client.json")
  # vertexai.init(project="gen-lang-client-0786739350", location="us-central1", credentials=cred)

  os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'config/gen-lang-client.json'
  vertexai.init(project="gen-lang-client-0786739350", location="us-central1")

  return "Vertex AI initialized"

# 在模块级别调用初始化函数
initialize_vertexai()


# analysis video
def analyze_video(source, is_url):
  if is_url:
    video_file_uri = f"gs://{source}"
    video_file_url = f"https://storage.cloud.google.com/{source}"
    video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")
  else:
    file_contents, mime_type, file_name = source
    # base64_encoded = base64.b64encode(file_contents).decode('utf-8')
    video_file = Part.from_data(
      mime_type=mime_type,
      data=file_contents
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
  return result['script_imitated']


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

