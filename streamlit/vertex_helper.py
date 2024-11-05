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


def create_imitation(sample_script, input_data):
  input_obj = {
    "script_sample": str(sample_script),
    "product_info": str(input_data)
  }
  result = call_workflow_api(input_obj)
  return result['script_imitated']


def create_imitation_old(sample_script, input_data):
  outline_km = read_from_resource('prompt/短视频脚本创作框架 V3 (专注于祛痘护肤产品-LLM版).md')
  content_km = read_from_resource('prompt/km-祛痘.md')

  target_lan = input_data['target_language']

  prompt_outline = f"""
  作为一个专业的短视频编导和内容营销专家，根据提供的短视频参考脚本，{target_lan}作为输出语言，模仿创作一个类似的脚本。
  注意follow如下的创作过程：
  1. 模仿<短视频参考脚本>中提供的参考脚本，包括分镜结构，高光画面等，根据<产品信息>提供的信息, 模仿创作一个短视频脚本，并输出详细的分镜。
  2. 可以利用<短视频脚本创作框架>提供的创作框架，作为创作指导，但尽量完全模仿参考脚本。创作框架仅仅是作为指导，尽量被模仿的对象。
  2. 以表格形式详细输出分镜脚本，包含如下字段：序号，画面内容，时间轴，口播，字幕，画面特点，目的&意义&必要性，参考画面。
    - 口播内容一定要用符合目标国家和人群的口语习惯，且要符合媒体平台的特点。学习<分镜知识>的文字风格和文字长度
    - 画面内容的描述要详细一点，学习<分镜知识>的文字风格和文字长度。
  3. 注意：参考画面，为可以参考自“短视频参考脚本”中的画面秒数，格式严格遵守：<参考画面>01-03</参考画面>。 对于高光画面一定要有参考的画面。
  4. 脚本创作完之后，对整体结构做一个概述，把核心结构概括出来，按这个格式

  <短视频参考脚本>
  {sample_script}
  </短视频参考脚本>

  <短视频脚本创作框架>
  {outline_km}
  </短视频脚本创作框架>

  <产品信息>
  {input_data}
  </产品信息>

  <分镜知识>
  {content_km}
  </分镜知识


  参考如下输出：
  ## 脚本构思：

  1. 选定结构: 主题设定 → 问题呈现 → 产品介绍 → 使用演示 → 效果展示 → 多元化说服 → 购买召唤
  2. 创意表现形式:
      选择"通俗"系列: 展示使用产品前后, 自信心和生活状态的改变
      内容:
      - 视频前半部分使用黑白/低饱和度画面, 展现主人公在居住问题中缺乏自信, 生活中受到影响的状态
      - 产品出现后画面变为彩色多彩, 主人公使用产品后, 自信问题得到改善, 人物表情自信阳光, 生活也明显提升很多上.
  3. BA/GA结账: 选择BA策略, 达人拥有"Before购家"要材, 引BA更能直观展示产品对居住的改善效果.
  4. 情感元素: 自卑 → 希望 → 喜悦 → 自信
  5. 核心传播点:
      - 居住问题明确
      - 产品有效改化居印
      - 使用方便
      - 提升自信, 改变生活

  ## 【Dr.Leo Acne Drying Lotion】

   - Video Topic (first 3s):What???? Acne shrinks in 12 hours???[the first 3s must have this text]*
   - Footage requirement for first 3 seconds：Close-up shot showing the product from the front
   - Background music：/
   - Video duration:40s
   - Headline:  Elevate Your Skincare Routine  | Unboxing Dr. Leo's Essentials
   - Hashtag：#drleo#drleoMY#acne#AcneBuster#AcneSolution#acnetreatment #skincare#fyp#pimple

  ## 分镜脚本

  | 序号 | 画面内容 | 时间轴 | 口播 | 字幕 | 画面特点 | 目的&意义&必要性 | 参考画面&时间节点 |
  |------|----------|------|-----------|-----------|-----------|------------------|------------------|
  | 1 | 以黑白色调拍摄达人面部特写，确保面部表情传达出明显的困扰感。面部特写需占据整个屏幕，痘印问题清晰可见。拍摄角度需要突出面部痘痘和痘印的状态，表情要自然传达出困扰感。 | 00:00-00:02 | "烦人的痘印又来了，真的好困扰..." | "又来了...这些顽固的痘印😣" | 黑白滤镜处理，光线充足，面部特写清晰，痘印问题明显 | 主题设定：快速引起目标受众共鸣，建立情感连接 | <参考画面>1-3</参考画面> |
  | 2 | 采用黑白色调，中景构图拍摄达人的失落状态。画面构图要求达人坐在镜子前或洗手台前，表现出沮丧的情绪。动作可以包括低头、轻触脸部等，确保表情和动作传达出困扰感。 | 00:02-00:04 | "用了很多产品都没效果" | "尝试了各种方法，为什么还是没改善？😭" | 黑白画面，情绪化构图，柔和打光突出失落感 | 问题深化：展现痘印困扰的情感冲击，为产品解决方案做铺垫 |  |
  | 3 | 转换为彩色画面，特写镜头对准产品包装。产品需在画面正中央，确保品牌Logo清晰可读。使用环形补光，突出包装的质感。配合手持动作，展示产品的各个角度。 | 00:04-00:06 | "直到我发现了这款网红祛痘精华" | "Dr.Leo祛痘精华✨" | 彩色画面，产品特写，光线明亮，突出产品质感 | 产品引入：以专业的展示方式建立产品可信度 |  |
  | 4 | 制作分屏对比效果：左侧放置使用产品前的痘痘状态照片，右侧是使用后的清透肌肤照片。两张照片的拍摄角度、光线保持一致，使用相同的面部位置进行对比。加入转场动画。 | 00:06-00:09 | "看看我使用前后的对比，效果真的太明显了！" | "从红肿到光滑平整，见证奇迹的时刻！✨" | 对比鲜明，转场流畅，细节清晰 | 效果展示：通过直观对比增强产品说服力 | <参考画面>55-57</参考画面> |
  | 5 | 近距离特写展示使用方法。画面需要分解展示：取量、涂抹等每个步骤。确保光线充足，质地特写清晰。面部涂抹时需要突出产品的清爽质地，动作要规范专业。 | 00:09-00:11 | "使用方法超简单，取适量轻轻涂抹就可以" | "-取适量产品 <br>.-轻轻涂抹 -冰爽触感 -一夜见效" | 专业使用手法，步骤清晰，画面明亮 | 使用教学：降低使用门槛，增强购买意愿 |  |
  | 6 | 彩色特写镜头展示达人的完美肤质状态。使用自然光源，确保面部充满整个屏幕。通过多角度展示肤质改善效果，突出毛孔细腻度和肌肤光泽。 | 00:11-00:13 | "独特配方快速修护痘痘，改善肤质" | "-硫磺+烟酰胺快速祛痘 -1.8%水杨酸温和去痘印" | 自然光下的肌肤特写，突出细节和效果 | 效果强化：展示产品的实际效果，增强说服力 |  |
  | 7 | 采用全景构图，拍摄达人在明亮的户外场景自信漫步的画面。可以选择在商场或街道等生活场景，光线充足，画面饱和度适中。达人需要表现出自信、愉悦的状态。 | 00:13-00:15 | "告别痘痘困扰，重获自信人生！" | "和Dr.Leo一起，告别烦恼肌！💕" | 画面明亮饱和，构图完整，体现生活感 | 情感升华：将产品与美好生活联系，促进购买决策 |  |

  核心结构: 居印问题B+产品适度特写+BA对比+近景使用+全景BA人生活方式GA+CTA

  ## 分析：
  高光画面模仿:
    - 痘痘特写 (00:01-00:03): 我使用了类似的画面，但添加了夸张的滤镜和特效，以增强视觉冲击力，并使用印尼语表达焦虑情绪。
    - 使用前后对比 (00:55-00:57): 我使用了分屏对比的方式，更直观地展现产品效果，并使用印尼语强调"Perubahannya luar biasa!" (效果太惊人了！)

  转化效果提升:
    - 更精准的语言和文化元素: 使用印尼语和当地文化元素，更能引起目标受众的共鸣。
    - 更快速的节奏和视觉冲击: 更符合短视频平台用户的观看习惯，更容易抓住用户的注意力。
    - 更注重情感价值和生活方式的改变: 突出产品带来的自信和积极改变，更能打动消费者。

  """

  model = GenerativeModel("gemini-1.5-pro")
  outline_response = model.generate_content([prompt_outline], generation_config=generation_config, safety_settings=safety_settings)
  return outline_response.text


def translate_script(script, target_language):
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

