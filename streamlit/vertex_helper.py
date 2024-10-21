from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting
import os
import base64

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
    file_contents, mime_type = source
    # base64_encoded = base64.b64encode(file_contents).decode('utf-8')
    video_file = Part.from_data(
      mime_type=mime_type,
      data=file_contents
    )

  prompt_read_video = f"""
  你是一个短视频编导和营销专家，仔细理解视频，分解下这个视频的拍摄框架，比如可以分成哪些分镜，详细描述每个分镜的画面内容以及画面特点，并分析分镜的用意和目的。
  前三秒非常关键，重点分析前三秒有什么特点，尤其从吸引眼球，埋下伏笔，吸引用户等角度分析前三秒。
  这个视频在tiktok上有较好的转化效果，分析为什么有好的转化效果，并指出你认为的非常吸引用户，有很好转化效果的高光画面（高光帧），并注明时间戳和理由。
  
  参考如下输出：
  1. 开场白 (00:00-00:12):
  - 画面内容: 一位年轻女性对着镜头，用英语和菲律宾语（Tagalog）解释视频内容，并回应评论区关于产品使用时间的提问。
  - 画面特点: 近景，人物清晰可见，表情自然亲切，营造轻松氛围。背景较为简洁，不会分散注意力。
  - 分镜用意: 快速吸引用户注意力，交代视频主题，并制造悬念，引导用户继续观看。

  2. 产品介绍（00:12-00:18）
  - 画面内容: 展示产品瓶身、成分表、使用方法（摇匀，均匀涂抹在爆痘区域）。
  - 画面特点: 运用文字、图片和视频相结合的方式，清晰地展现产品信息，细节突出，并使用“Limited-time discount, hurry and buy now.”的营销话术。
  - 分镜用意: 直观地展现产品，激发用户的购买欲。

  3. 产品展示和功效介绍（00:21-00:31）
  - 画面内容: 静态展示产品包装盒，以及产品功效介绍，例如“design for acne prone skin”、“fade red and dark acne scars”、“deeply cleanses stubborn acne”、“gently treats acne soothes the skin”。
  - 画面特点: 产品包装设计简洁美观，文案突出产品卖点。
  - 分镜用意: 再次强化产品卖点，提升产品信任度。

  4.结尾 (00:57-00:58):
  - 画面内容: 展现使用后的效果对比图。
  - 画面特点: 前后对比明显，视觉冲击力强。
  - 分镜用意: 再次强调产品功效，留下深刻印象。

  前三秒分析:
  前三秒画面快速切换，从女性讲解过渡到痘痘特写（00:01-00:03），制造了视觉冲击和危机感，立刻抓住了用户的眼球。很多用户有痘痘困扰，看到这样的画面会下意识地想了解解决方案。

  高光画面分析:
  - 00:01-00:03: 痘痘特写图，引起用户共鸣，激发用户想了解解决方案的欲望。
  - 00:55-00:57: 使用前后对比图，效果显著，直接展现产品功效，增强说服力。

  为什么转化效果好:
  - 精准定位: 目标用户是那些有痘痘困扰的群体，视频内容直接切中用户痛点。
  - 短平快: 视频节奏明快，信息量大，不会让用户感到枯燥。
  - 视觉冲击: 痘痘特写、前后对比图等画面，具有很强的视觉冲击力。
  - 清晰的解决方案: 视频不仅展示产品，还详细讲解了使用方法，并针对不同情况给出了解决方案。
  - 信任感: 产品成分表、功效介绍、使用演示等细节，增强了用户的信任感。
  - 限时优惠: “Limited-time discount”的营销话术，制造了紧迫感，促使用户立即下单。

  """

  contents = [video_file, prompt_read_video]

  model = GenerativeModel("gemini-1.5-flash-002")
  response_transcript = model.generate_content(contents, generation_config=generation_config, safety_settings=safety_settings)
  return response_transcript.text


def create_imitation(sample_script, input_data):
  # read gdoc or md file
  outline_km_path = 'prompt/短视频脚本创作框架 V3 (专注于祛痘护肤产品-LLM版).md'
  try:
    with open(outline_km_path, 'r', encoding='utf-8') as f:
      outline_km = f.read()
  except UnicodeDecodeError:
      # 如果 UTF-8 失败，尝试其他编码
    with open(outline_km_path, 'r', encoding='gbk') as f:
      outline_km = f.read()

  prompt_outline = f"""
  作为一个专业的短视频编导和内容营销专家，根据提供的短视频参考脚本，并根据自己的短视频脚本创作框架进行创作，用{input_data['target_language']}作为语言，仿写一个类似的脚本。
  注意follow如下的创作过程：
  1. 分析参考脚本和自己的创作框架,模仿参考脚本的结构和高光画面，包括字幕，输出详细的分镜，同时详细阐述创作理由，对每一个分镜需要详细说明其目的，意义及必要性。
  2. 以表格形式详细输出分镜脚本，某些重要的画面，提其参考自参考脚本的第几秒，用图片链接来输出，图片URL为http://images/second(其中second为第几秒)
  3. 字幕和旁白台词，一定要用符合目标国家和人群的口语化的词语。
  4. 脚本创作完之后，对整体结构做一个概述，把核心结构概括出来，按这个格式，比如：全脸痘痘B+全脸GA+产品近景特写+近景使用+全脸GA+CTA

  短视频参考脚本：
  {sample_script}

  短视频脚本创作框架：
  {outline_km}

  输入信息：
  {input_data}

  参考如下输出：
  1. 选定结构: 主题设定 → 问题呈现 → 产品介绍 → 使用演示 → 效果展示 → 多元化说服 → 购买召唤
  2. 视觉效果: 分屏对比, 近景特写, 播放效果, 动画文字
  3. 创意表现形式:
     选择"通俗"系列: 展示使用产品前后, 自信心和生活状态的改变
     内容:
     - 视频前半部分使用黑白/低饱和度画面, 展现主人公在居住问题中缺乏自信, 生活中受到影响的状态
     - 产品出现后画面变为彩色多彩, 主人公使用产品后, 自信问题得到改善, 人物表情自信阳光, 生活也明显提升很多上.
  4. BA/GA结账: 选择BA策略, 达人拥有"Before购家"要材, 引BA更能直观展示产品对居住的改善效果.
  5. 情感元素: 自卑 → 希望 → 喜悦 → 自信
  6. 时长: 15秒
  7. 核心传播点:
     - 居住问题明确
     - 产品有效改化居印
     - 使用方便
     - 提升自信, 改变生活

  ## 分镜脚本

  | 序号 | 画面内容 | 时长 | 字幕 (旁白台词) | 画面特点 | 目的&意义&必要性 | 参考时间节点 |
  |------|----------|------|----------------|----------|------------------|--------------|
  | 1 | 黑白色调, 近景特写达人无奈的印象 | 2秒 | 你是否也苦恼居印问题呢? | 使用参考脚本00:01-00:03的画面特写, 达到处理成黑白画面. 突出居印问题 | 主题设定: 快速吸引目标受众, 引起共鸣 | 00:01-00:03 |
  | 2 | 黑白色调, 中景拍摄达人运倩画面, 神情失落 | 2秒 | 无法自信地面对他人 | 展现居印问题对生活的负面影响, 引发情感共鸣 | 问题呈现: 深化痛点, 为产品解决方案做铺垫 |  |
  | 3 | 彩色画面, 产品包装盒特写, 突出产品名称 | 2秒 | XXX好居产品, 你的居印放心! | 产品包装画面走大方, 使用动画文字突出产品名 | 产品介绍: 引入解决方案, 激发观众兴趣 |  |
  | 4 | 左侧为达人使用产品前的照片, 右侧为达人使用产品后的照片 | 3秒 | 使用前 VS 使用后效果看得见! | 使用前后效果对比, 突出使用产品前后居印的改变 | 效果展示: 直观展示产品效果, 增强说服力 | 00:55-00:57 |
  | 5 | 近景特写, 达人手持产品, 演示使用方法 | 2秒 | 使用方法简单, 快速吸收! | 画面清晰流畅, 突出产品使用方法易吸收 | 使用演示: 降低使用门槛, 增强产品吸引力 |  |
  | 6 | 彩色画面, 近景拍摄达人面部, 肤色均匀亮泽 | 2秒 | 居印改化, 肌肤重现光彩 | 达人面部特写, 展现使用产品后健康自信的肌肤状态 | 效果展示: 强化产品价值, 刺激购买欲望 |  |
  | 7 | 彩色画面, 全景拍摄达人自信地走在街上 | 2秒 | 找回自信, 拥抱更美好的生活! | 画面明亮充满活力, 展现达人积极向上的生活状态 | 情感升华: 将产品与自信美好生活紧密联系 |  |

  核心结构: 居印问题B+产品适度特写+BA对比+近景使用+全景BA人生活方式GA+CTA

  ## 分析：
  契合点: 
   - 参考脚本和我的创作框架都使用了"问题-解决方案"的叙事结构，并注重使用前后对比的效果展示。

  不契合点:
   - 参考脚本节奏较慢，信息量更大，我的脚本更注重视觉冲击和情感表达，节奏更快。
   - 参考脚本使用中英双语字幕，我的脚本针对印度尼西亚市场，使用印尼语和英语。
   - 参考脚本更注重产品信息和使用方法的介绍，我的脚本更注重产品带来的情感价值和生活方式的改变。

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


if __name__ == "__main__":
    prompt_test = f"hi"

    model = GenerativeModel("gemini-1.5-pro")
    responses = model.generate_content(
        [prompt_test],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    for response in responses:
        print(response.text)

