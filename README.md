# 启动：
## 进入venv
source ./venv/bin/activate

## 在streamlit目录下启动服务，会在运行目录下的static目录下生成vidoes目录用于存放上传的视频
nohup streamlit run app.py &

## 查看进程：
ps -ef | grep streamlit


对于上传的文件存储在数据盘中，用ln建立连接
ln -s [目标文件或目录] [符号链接路径]


streamlit的static资源默认访问为/app/static