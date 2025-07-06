import os
import pytesseract
from flask import Flask, render_template
from bs4 import BeautifulSoup
import re
from flask import request, redirect, url_for, jsonify,send_from_directory
from PIL import Image
import traceback
import base64


OCR_LANGUAGES = 'chi_sim'
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}

app = Flask(__name__, static_folder=STATIC_FOLDER) # 指定 static_folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 上传限制

if not os.path.exists(os.path.join(STATIC_FOLDER, UPLOAD_FOLDER)):
    os.makedirs(os.path.join(STATIC_FOLDER, UPLOAD_FOLDER))

print("当前工作目录:", os.getcwd())

def parse_bbox(title_string):
    """从title字符串中解析 'bbox x1 y1 x2 y2'"""
    match = re.search(r'bbox\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', title_string)
    if match:
        return [int(c) for c in match.groups()]
    return None

def perform_ocr_web(pil_image):
    words_data = []
    try:
        hocr_output = pytesseract.image_to_pdf_or_hocr(pil_image, lang=OCR_LANGUAGES, extension='hocr')
        soup = BeautifulSoup(hocr_output, 'html.parser')
        
        global_idx = 0

        for line_idx, line_element in enumerate(soup.find_all('span', class_='ocr_line')):
            line_bbox = parse_bbox(line_element.get('title', ''))
            if not line_bbox:
                continue

            for word_idx, word_element in enumerate(line_element.find_all('span', class_='ocrx_word')):
                word_text = word_element.text
                word_bbox = parse_bbox(word_element.get('title', ''))
                if not word_text or not word_bbox:
                    continue
                x1, y1, x2, y2 = word_bbox
                js_box = [x1, y1, x2 - x1, y2 - y1] # 转换为 [x, y, width, height]
                words_data.append({
                    'word': word_text.strip(),
                    'box': js_box,
                    'line_index': line_idx,
                    'word_index': word_idx,
                    'global_index': global_idx
                })
                global_idx += 1
        words_data.sort(key=lambda c: c['global_index'])
        return words_data

    except pytesseract.TesseractNotFoundError:
        raise Exception("Tesseract is not installed or not found in your PATH.")
    except Exception as e:
        print(f"Error during OCR or parsing: {e}")
        raise Exception(f"An error occurred during OCR: {str(e)}")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """渲染主页面"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """TODO"""
    
    # 思路与实现:
    # 1.安装依赖，启动入口函数
    # 2.查看前端如何文件index.html
    # 3.实现上传图片功能
    # 4.Dbug调试，获取上传文件的请求对象，然后根据上述的allowed_file 判断上传的文件格式是否允许
    # 5.当格式为图片格式时，调用perform_ocr_web处理，这个是时候，需要判断传参数的内容，发现需要使用Image对象处理
    # 6.当perform_ocr_web处理后返回结果，这个是时候不知道返回格式，通过前端js代码，判断需要返回的数据格式
    try:
        # 检查是否为文件
        if 'file' not in request.files:
            return jsonify({
                    "success":False,
                    "message":f"Upload_image is error:files not found file"
            }), 500
        
        file = request.files['file']
        
        # 检查文件类型是否符合条件
        if file and allowed_file(file.filename):
            # 保存图片到本地
            save_path =  os.path.join(os.getcwd(),"static","uploads")
            file_path = os.path.join(save_path,file.filename)
            file.save(file_path)
            
            # 打开图像进行OCR处理
            img = Image.open(file.stream)
            ocr_results = perform_ocr_web(img)
            
            # 进行base64b编码
            with open(file_path, "rb") as file:
                encoded_string = base64.b64encode(file.read()).decode("utf-8")
            # 返回OCR结果和文件访问URL
            return jsonify({
                'success':True,
                'imageUrl':f"data:image/png;base64,{encoded_string}",
                "imageWidth": img.width,
                "imageHeight": img.height,
                'ocrData': ocr_results
            }), 200
        else:
            return jsonify({
                    "success":False,
                    "message":f"Upload_image is error:file type is not allow"
            }), 500
    except Exception as e:
        print(f"{traceback.format_exc()}")
        return jsonify({
                "success":False,
                "message":f"Upload_image is error:{e}"
        }), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """TODO"""
    try:
        save_path =  os.path.join(os.getcwd(),"static","uploads")
        file_path = os.path.join(save_path,filename)
        if not os.path.exists(file_path):
            return jsonify({
                "success":False,
                "message":"Uploaded_file is error:File not found"
            }), 404
        return send_from_directory(save_path, filename)
    except Exception as e:
        print(f"{traceback.format_exc()}")
        return jsonify({
                "success":False,
                "message":f"Uploaded_file is error:{e}"
        }), 500
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
