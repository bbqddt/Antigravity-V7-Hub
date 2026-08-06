import sys
import os

# 确保服务器能找到当前目录下的文件
sys.path.insert(0, os.path.dirname(__file__))

# 这里的 from app 指的是你的 app.py 文件
# import app as application 是虚拟主机要求的固定格式
try:
    from app import app as application
except Exception as e:
    def application(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
        return [f"越南节点启动失败，报错信息: {str(e)}".encode('utf-8')]