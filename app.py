import gradio as gr
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
import subprocess
import tempfile
import os
import json

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请在Space Secrets中设置DASHSCOPE_API_KEY")

# 永久免费额度管理（基于ip,终身10次）
USAGE_FILE = "total_usage.json"

def get_client_ip(request:gr.Request):
    """获取用户·ip"""
    return request.client.host

def check_free_quota(ip:str) -> tuple[bool,str]:
    """检查免费额度，返回[是否可用，提示信息]"""
    # 读取现有数据
    try:
        with open(USAGE_FILE,'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    
    # 获取该ip已使用次数
    used = data.get(ip,0)
    if used >= 10:
        return False,f"你的10次免费体验已用完，请输入你的API Key继续使用(右侧输入框)。"
    # 使用次数递增
    data[ip] = used + 1
    with open(USAGE_FILE,'w') as f:
        json.dump(data,f)

    remaining = 10 - used -1
    return True,f"免费次数剩余：{remaining}次/10次(永久累计)"

# 工具定义
@tool
def execute_python_code(code: str) -> str:
    """安全执行Python代码，返回输出或错误信息"""
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
        f.write(code)
        tmp_path = f.name
    try:
        result = subprocess.run(
            ['python', tmp_path],
            capture_output=True,
            timeout=5,
            text=True,
            check=False
        )
        output = result.stdout
        if result.stderr:
            return f"[ERROR] {result.stderr.strip()}"
        return output.strip() if output.strip() else "执行成功（无输出）"
    except subprocess.TimeoutExpired:
        return "[ERROR]执行超时（超过5秒）"
    finally:
        try:
            os.unlink(tmp_path)   #删除临时文件
        except OSError:
            pass

# 加载持久化的向量库
vectorstore = Chroma(
    persist_directory = "./chromadb",
    embedding_function = OpenAIEmbeddings(
        model = "text-embedding-v3",
        api_key = DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
)

# 本地知识库检索
@tool
def search_knowledge(query:str) -> str:
    """从本地知识库中检索与问题相关的内容。当用户提出的问题超出模型训练范围，或者你需要参考特定文档时，使用此工具"""
    # 处理字典参数
    if isinstance(query,dict):
        query = query.get('query') or query.get('input') or str(query)
    if not isinstance(query,str):
        query = str(query)
    if not query.strip():
        return "查询列表为空，无法检索"
    print(f"[DEBUG] search_knowledge received:{query!r},type:{type(query)}")
    docs = vectorstore.similarity_search(query,k=2)
    if not docs:
        return "未找到相关信息"
    results = "\n\n---\n\n".join([doc.page_content for doc in docs])
    return f"根据知识库检索到:\n\n{results}"

#  初始化 LLM
llm = ChatOpenAI(
    model="qwen-max",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    # api_key=os.environ.get("DASHSCOPE_API_KEY"),  # 从环境变量读取
    temperature=0
)

#  创建 Agent（LangChain 1.x 新版 API）
agent = create_agent(
    model=llm,
    tools=[execute_python_code,search_knowledge],
    system_prompt="""你是一个编程助手。对于数学计算、代码运行等任务，你必须使用 execute_python_code 工具，不要自己直接计算结果。

    当 execute_python_code 工具返回以 “[ERROR]” 开头的错误信息时，你需要：
    1. 分析错误原因（例如语法错误、除零、超时等）
    2. 尝试修正用户提供的代码或调整参数
    3. 再次调用 execute_python_code 工具，最多重试3次
    4. 如果3次后仍然失败，向用户说明无法完成该任务，并给出可能的解决建议。

    对于需要特定知识的问题（例如”解释什么是内存泄漏”、”Python中列表推导式的用法”），优先使用 search_knowledge 工具获取资料后再回答。

    请遵循上述重试逻辑，不要放弃第一次失败。"""
)

# 对话函数
def chat_with_agent(message,history,user_api_key,request:gr.Request):
    # 确定使用哪个key
    api_key_to_use = None
    usage_mode = "free"

    if user_api_key and user_api_key.strip():
        # 用户填了自己的api_key
        api_key_to_use = user_api_key.strip()
        usage_mode = "paid"
        quota_msg = "使用你自己的api_key,无限次使用"
    else:
        client_ip = get_client_ip(request)
        ok,msg = check_free_quota(client_ip)
        if not ok:
            return msg #免费次数用完，直接返回提示
        api_key_to_use = os.environ.get("DASHSCOPE_API_KEY")
        quota_msg = f" {msg}"
    
    #  初始化 LLM
    try:
        llm = ChatOpenAI(
            api_key = api_key_to_use,
            model="qwen-max",
            api_key = DASHSCOPE_API_KEY,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            temperature=0
        )
    except Exception as e:
        return f"False api key无效或网络链接错误:{str(e)}"

    # Gradio 6.x: history已经是OpenAI风格的消息列表 [{"role":"user","content":"..."}, ...]
    # 只保留role和content字段，去掉metadata等额外字段
    messages = [{"role":h["role"],"content":h["content"]} for h in history]
    messages.append({"role":"user","content":message})

    # 调用agent
    client_ip = get_client_ip(request) if usage_mode == "free" else "paid_user"
    config = {"configurable":{"thread_id":client_ip}}
    try:
        result = agent.invoke({"messages":messages},config = config)
        response = result["messages"][-1].content
    except Exception as e:
        return f"抱歉，处理时出现错误：{e}"
    # 当用户用免费模式，在回复中附加额度信息
    if usage_mode == "free":
        response = f"{response}\n\n---\n{quota_msg}"
    
    return response

# 创建gradio界面
with gr.Blocks(title="智能编程助手") as demo:
    gr.Markdown(
        """# 🤖 智能编程助手 Agent
    我能执行Python代码、回答编程问题、检索你的本地知识库。

    **免费额度**：每人终身10次免费体验。用完请填入你的阿里百炼API Key继续使用。"""
    )
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label = '对话区',height=500)
            msg = gr.Textbox(label = '请输入你的问题',placeholder='例如：写一个快速排序的函数')
            clear = gr.ClearButton([msg,chatbot])
        
        with gr.Column(scale = 1):
            api_key_input = gr.Textbox(
              label="🔑 阿里百炼 API Key（可选）",
                type="password",
                placeholder="sk-... 不填则使用终身10次免费额度",
                info="获取地址：https://bailian.console.aliyun.com/"  
            )
            gr.Markdown("""
            ### 📌 使用说明
            - 每人终身10次免费体验（基于IP地址）
            - 10次用完后必须填入自己的API Key
            - 填入自己的Key后无限次使用
            - 代码执行有5秒超时保护
            """)

        def respond(message,history,api_key,request:gr.Request):
            if not message:
                return '',history
            history = history or []
            response = chat_with_agent(message,history,api_key,request)
            history.append({'role':'user','content':message})
            history.append({'role':'assistant','content':response})
            return '',history
        
        msg.submit(
            respond,
            [msg,chatbot,api_key_input],
            [msg,chatbot]
        )


if __name__ == "__main__":
    # 如果文件不存在，创建文件
    if not os.path.exists(USAGE_FILE):
        with open(USAGE_FILE,'w') as f:
            json.dump({},f)

    demo.launch(
        server_port=7860,
        share=False,
        auth=None,
        theme=gr.themes.Soft()
    )