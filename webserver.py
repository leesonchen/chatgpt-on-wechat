from flask import Flask, request, send_file, jsonify
import os
import tempfile
import threading
import time
from config import conf, load_config

app = Flask(__name__)

# 文件服务器
FILE_SERVER = ''

# 设置上传文件的保存目录
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
auth_tokens = []

# 设置允许上传的文件类型
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'wav', 'mp3', 'mp4', 'zip', 'rar', 'docx', 'xlsx', 'pptx', 'doc', 'xls', 'ppt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_file(path, wait_seconds=600):
    thread = threading.Thread(target=_delete_file, args=(path, wait_seconds))
    thread.start()

def _delete_file(path, wait_seconds):
    time.sleep(wait_seconds)
    try:
        os.remove(path)
        print("[webserver] file {} has been deleted".format(path))
    except Exception as e:
        print("[webserver] file {} delete failed: {}".format(path, e))

@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查是否有文件被上传
    if 'file' not in request.files:
        return 'No file uploaded', 400

    file = request.files['file']
    print("[webserver] file: {}".format(file))

    token = request.form.get('token', '')
    print("[webserver] token: {}".format(token))

    # 如果用户没有选择文件，浏览器也会发送一个没有文件名的空文件
    if file.filename == '':
        return 'No selected file', 400

    # 如果用户token不正确，返回无权限
    if token not in auth_tokens:
        return 'No permission', 403

    # 检查文件类型是否允许
    if not allowed_file(file.filename):
        return 'File type not allowed', 400

    # 创建临时文件
    newfile = tempfile.NamedTemporaryFile(delete=False).name
    newfile = os.path.basename(newfile)
    path = os.path.join(app.config['UPLOAD_FOLDER'], newfile)

    # 保存上传的文件到服务器
    file.save(path)

    wait_seconds = 600
    delete_file(path, wait_seconds)

    # 构建文件下载链接
    download_url = f"{FILE_SERVER}/download/{newfile}"

    # 返回下载链接给客户端
    return jsonify({'download_url': download_url, 'expires': wait_seconds}), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
    except FileNotFoundError:
        return 'File not found', 404

if __name__ == '__main__':
    load_config()
    auth_tokens = conf().get('file_upload_auth_tokens', [])
    FILE_SERVER = conf().get('file_web_server', '')

    app.run(port=5000, debug=False)