import os
from langchain_community.document_loaders import DirectoryLoader,TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import chroma
from langchain_openai import OpenAIEmbeddings

# 加载知识库
loader = DirectoryLoader(
    r"D:\Vscode\ai\knowledge",
    glob = "**/*.txt",   #加载目标知识库文件夹中的所有文本文件
    loader_cls = TextLoader,
    loader_kwargs = {"encoding":'utf-8'}
)
docs = loader.load()
print(f"加载了{len(docs)}个文档")

# 文档切分（chunk)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 500,   #每块字符
    chunk_overlap = 50,   #重叠字符串数量
    separators = ['\n\n','\n',',','。','!']
)
chunks = text_splitter.split_documents(docs)
print(f"切分为{len(chunks)}个块")

embeddings = OpenAIEmbeddings(
    model = 'text-embedding-v3',
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 创建向量数据库并持久化到本地目录
vectorstore = chroma.Chroma.from_documents(
    documents = chunks,
    embedding = embeddings,
    persist_directory = './chromadb'   #保存在本地文件夹
)
print("向量数据库已构建完成，保存在./chromadb 中")

