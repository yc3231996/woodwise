import os
import requests
from typing import Dict, Any
from dotenv import load_dotenv

def call_workflow_api(input_obj: Dict[str, Any], user_id: str = "dify-woodwise") -> Dict[str, Any]:
    """
    调用工作流API的函数
    
    Args:
        input_obj (Dict[str, Any]): 输入参数对象
        user_id (str): 用户ID，默认为"abc-123"
        
    Returns:
        Dict[str, Any]: API响应内容
        
    Raises:
        requests.exceptions.RequestException: 当HTTP请求失败时抛出异常
        ValueError: 当环境变量未正确配置时抛出异常
    """
    # 加载环境变量
    load_dotenv()
    
    # 从环境变量获取配置
    api_key = os.getenv('WORKFLOW_API_KEY')
    api_url = os.getenv('WORKFLOW_API_URL')
    
    if not api_key or not api_url:
        raise ValueError("请在.env文件中配置WORKFLOW_API_KEY和WORKFLOW_API_URL")
    
    # 构建完整的URL
    url = f"{api_url}/v1/workflows/run"
    
    # 设置请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 请求体数据
    payload = {
        "inputs": input_obj,
        "response_mode": "blocking",
        "user": user_id
    }
    
    try:
        # 发送POST请求
        response = requests.post(
            url=url,
            headers=headers,
            json=payload,
            timeout=60  # 设置30秒超时
        )
        
        # 检查响应状态码
        response.raise_for_status()
        
        # 验证响应格式
        if response.headers.get('content-type') != 'application/json':
            raise ValueError("API返回的不是JSON格式")
        
        # 解析响应
        result = response.json()
        
        # 验证响应结构
        if not isinstance(result, dict):
            raise ValueError("API响应格式不正确")
        
        # 检查必要字段
        required_fields = ['workflow_run_id', 'task_id', 'data']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"API响应缺少必要字段: {field}")
        
        return result['data']['outputs']
            
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        raise

# 使用示例
if __name__ == "__main__":
    # 测试输入数据
    test_input = {
        "script_sample": "hello, sample script",
        "product_info": "product info is here"
    }
    
    try:
        result = call_workflow_api(test_input)
        print("API响应:", result['script_imitated'])
    except Exception as e:
        print(f"发生错误: {e}")