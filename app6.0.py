from flask import Flask, request, jsonify, send_from_directory
import requests, json, os, base64, time, wave, threading
import tempfile

app = Flask(__name__, static_folder="static", static_url_path="/static")

# API配置
API_KEY = "pat_ljaZaHZQhyrxbrBGZk46M8qPWlfPeEjvRLKcNg1bc7RDOlVYyrcXrzRRRCBUbmyL"
BASE_URL = "https://api.coze.cn/v3/chat"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 百度OCR配置
BAIDU_APP_ID = "7145385"
BAIDU_API_KEY = "A1HwFSF41cRblmgpAeFA5xnK"
BAIDU_SECRET_KEY = "bPGUByhUrC4FCoohVWsaxIiw1aN9eWBP"

# 百度语音识别配置
BAIDU_SPEECH_API_KEY = "A1HwFSF41cRblmgpAeFA5xnK"  # 使用相同的API KEY
BAIDU_SPEECH_SECRET_KEY = "bPGUByhUrC4FCoohVWsaxIiw1aN9eWBP"

# 增加日志打印配置
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/")
def game_page():
    return send_from_directory(".", "game.html")

@app.route("/index8.0.html")
def index_page():
    return send_from_directory(".", "index8.0.html")  # 修改为您的HTML文件名

@app.route("/b.html")
def b_page():
    return send_from_directory(".", "b.html")

@app.route("/c.html")
def c_page():
    return send_from_directory(".", "c.html")

@app.route("/d.html")
def d_page():
    return send_from_directory(".", "d.html")

@app.route("/e.html")
def e_page():
    return send_from_directory(".", "e.html")




@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    bot_id = data.get("bot_id")
    message = data.get("message")
    conv_id = data.get("conversation_id")

    # 校验必填参数
    if not bot_id or not message:
        logger.error(f"缺少必填参数：bot_id={bot_id}, message={message}")
        return jsonify({"error": "缺少bot_id或message参数", "reply": ""}), 400

    payload = {
        "bot_id": bot_id,
        "user_id": "student",
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [{"role": "user", "content": message, "content_type": "text"}],
    }
    if conv_id:
        payload["conversation_id"] = conv_id

    try:
        # 1. 发送聊天请求
        logger.info(f"发送请求到Coze API: bot_id={bot_id}, conv_id={conv_id}, message={message[:20]}...")
        r = requests.post(BASE_URL, headers=HEADERS, data=json.dumps(payload), timeout=30)
        r.raise_for_status()  # 抛出HTTP错误
        response_data = r.json()

        # 容错处理：检查返回数据结构
        if "data" not in response_data:
            logger.error(f"Coze API返回无data字段: {response_data}")
            return jsonify({"error": f"Coze API返回异常: {response_data}", "reply": ""}), 500

        d = response_data["data"]
        conv_id = d.get("conversation_id")
        chat_id = d.get("id")

        # 校验关键ID是否存在
        if not conv_id or not chat_id:
            logger.error(f"缺少conversation_id或chat_id: {d}")
            return jsonify({"error": "获取会话ID失败", "reply": ""}), 500

        # 2. 轮询状态（增加等待间隔，避免高频请求）
        retrieve_url = f"{BASE_URL}/retrieve?conversation_id={conv_id}&chat_id={chat_id}"
        status = "pending"
        max_retries = 40  # 最多轮询20秒（0.5秒/次）
        for i in range(max_retries):
            time.sleep(1)  # 关键修改：增加等待间隔
            s_response = requests.get(retrieve_url, headers=HEADERS, timeout=10)
            s_response.raise_for_status()
            s_data = s_response.json().get("data", {})
            status = s_data.get("status", "pending")
            logger.info(f"轮询第{i + 1}次，状态: {status}")

            if status == "completed":
                break
            elif status in ["failed", "cancelled"]:
                logger.error(f"智能体处理失败，状态: {status}, 详情: {s_data}")
                return jsonify({"error": f"智能体处理失败: {status}", "reply": ""}), 500

        # 检查是否超时
        if status != "completed":
            logger.error(f"轮询超时，最终状态: {status}")
            return jsonify({"error": "智能体响应超时", "reply": ""}), 500

        # 3. 获取消息列表
        msg_url = f"{BASE_URL}/message/list?chat_id={chat_id}&conversation_id={conv_id}"
        msg_response = requests.get(msg_url, headers=HEADERS, timeout=10)
        msg_response.raise_for_status()
        msgs_data = msg_response.json().get("data", [])

        # 容错处理：查找AI回复
        answer = ""
        for m in msgs_data:
            if m.get("type") == "answer" and m.get("content"):
                answer = m["content"]
                break

        if not answer:
            logger.error(f"未找到AI回复，消息列表: {msgs_data}")
            return jsonify({"error": "未找到智能体回复内容", "conversation_id": conv_id, "reply": ""}), 500

        logger.info(f"成功获取回复: {answer[:50]}...")
        return jsonify({"reply": answer, "conversation_id": conv_id})

    except requests.exceptions.Timeout:
        logger.error("请求Coze API超时")
        return jsonify({"error": "请求智能体超时，请稍后重试", "reply": ""}), 500
    except requests.exceptions.HTTPError as e:
        logger.error(f"Coze API HTTP错误: {e}, 响应内容: {r.text if 'r' in locals() else '无'}")
        return jsonify({"error": f"智能体接口错误: {e}", "reply": ""}), 500
    except Exception as e:
        logger.error(f"聊天接口异常: {str(e)}", exc_info=True)
        return jsonify({"error": f"服务器内部错误: {str(e)}", "reply": ""}), 500


# 以下OCR、语音识别等代码保持不变（省略，完整代码见下方）
@app.route("/ocr", methods=["POST"])
def ocr():
    """处理图片上传和OCR识别"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({"error": "没有上传图片文件"}), 400

        file = request.files['image']

        # 检查文件名
        if file.filename == '':
            return jsonify({"error": "没有选择文件"}), 400

        # 检查文件类型
        allowed_extensions = {'jpg', 'jpeg', 'png', 'bmp'}
        if not ('.' in file.filename and
                file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({"error": "不支持的文件类型"}), 400

        # 读取图片并进行Base64编码
        img_data = file.read()
        base64_data = base64.b64encode(img_data).decode()

        # 获取百度OCR的access token
        access_token = get_baidu_access_token()
        if not access_token:
            return jsonify({"error": "无法连接到百度OCR服务，请检查网络连接"}), 500

        # 调用百度OCR接口，增加重试机制
        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/general_basic?access_token={access_token}"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'image': base64_data}

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"第 {attempt + 1} 次尝试调用OCR API...")
                response = requests.post(url, headers=headers, data=data, timeout=30)  # 设置30秒超时
                result = response.json()

                # 处理识别结果
                if 'words_result' in result:
                    text_result = ""
                    for item in result['words_result']:
                        text_result += item['words'] + '\n'
                    return jsonify({"text": text_result.strip()})
                else:
                    error_msg = result.get('error_msg', '未知错误')
                    error_code = result.get('error_code', '未知错误码')
                    return jsonify({"error": f"识别失败: {error_msg} (错误码: {error_code})"}), 500

            except requests.exceptions.Timeout:
                print(f"第 {attempt + 1} 次OCR API调用超时")
                if attempt < max_retries - 1:
                    time.sleep(3)  # 等待3秒后重试
                    continue
                else:
                    return jsonify({"error": "OCR服务响应超时，请稍后重试"}), 500
            except Exception as e:
                print(f"第 {attempt + 1} 次OCR API调用失败: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                else:
                    return jsonify({"error": f"OCR服务调用失败: {str(e)}"}), 500

    except Exception as e:
        print(f"OCR处理异常: {str(e)}")
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


def get_baidu_access_token():
    """获取百度API的access token"""
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"

    # 重试机制
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"第 {attempt + 1} 次尝试获取access_token...")
            response = requests.get(url, timeout=10)  # 设置10秒超时
            result = response.json()

            if 'access_token' in result:
                print(f"成功获取access_token")
                return result.get("access_token")
            else:
                error_msg = result.get('error_description', '未知错误')
                print(f"获取access_token失败: {error_msg}")

        except requests.exceptions.Timeout:
            print(f"第 {attempt + 1} 次尝试超时")
            if attempt < max_retries - 1:
                time.sleep(2)  # 等待2秒后重试
                continue
            else:
                print("所有重试均超时")
                return None
        except Exception as e:
            print(f"第 {attempt + 1} 次尝试失败: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                return None

    return None


class BaiduSpeechRecognition:
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key
        self.access_token = None
        self.get_access_token()

    def get_access_token(self):
        url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={self.api_key}&client_secret={self.secret_key}"
        try:
            response = requests.post(url)
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                print(f"成功获取百度语音识别access_token")
        except Exception as e:
            print(f"获取百度API access_token失败: {str(e)}")

    def speech_recognition(self, audio_file_path):
        if not self.access_token:
            self.get_access_token()
            if not self.access_token:
                return None

        url = f"https://vop.baidubce.com/server_api?dev_pid=1537&cuid=test_python&token={self.access_token}"

        try:
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
        except FileNotFoundError:
            return None

        headers = {
            'Content-Type': 'audio/wav; rate=16000',
            'Content-Length': str(len(audio_data))
        }

        try:
            response = requests.post(url, headers=headers, data=audio_data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result.get('err_no') == 0:
                    return result.get('result', [])[0] if result.get('result') else "未识别到内容"
                else:
                    error_msg = result.get('err_msg', '未知错误')
                    print(f"语音识别失败: {error_msg}")
                    return None
            else:
                print(f"语音识别请求失败，状态码: {response.status_code}")
                return None
        except Exception as e:
            print(f"语音识别请求失败: {str(e)}")
            return None


# 初始化语音识别
speech_recognizer = BaiduSpeechRecognition(BAIDU_SPEECH_API_KEY, BAIDU_SPEECH_SECRET_KEY)


@app.route("/speech-recognition", methods=["POST"])
def speech_recognition():
    """处理语音识别"""
    try:
        # 检查是否有音频文件上传
        if 'audio' not in request.files:
            return jsonify({"error": "没有上传音频文件"}), 400

        audio_file = request.files['audio']

        # 检查文件名
        if audio_file.filename == '':
            return jsonify({"error": "没有选择文件"}), 400

        # 创建临时文件保存音频
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            audio_file.save(temp_audio.name)

            # 调用百度语音识别
            result = speech_recognizer.speech_recognition(temp_audio.name)

            # 删除临时文件
            os.unlink(temp_audio.name)

            if result:
                return jsonify({"text": result})
            else:
                return jsonify({"error": "语音识别失败"}), 500

    except Exception as e:
        print(f"语音识别处理异常: {str(e)}")
        return jsonify({"error": f"处理失败: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)