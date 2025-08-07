import json
import requests
import config # 導入我們建立的設定檔
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# 允许所有来源的CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应配置为更严格的来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def diagnose_video_with_gemini(video_description: str, video_title: str = "untitled.mp4"):
    """
    接收影片描述，調用 Gemini API 執行完整的診斷流程並返回 JSON 報告。

    Args:
        video_description (str): 对用户上传视频的详细文字描述。
        video_title (str): 视频的文件名。

    Returns:
        dict: 包含完整诊断报告的 Python 字典。
              如果 API 调用失败，则返回错误信息。
    """
    if not config.API_KEY:
        # 在伺服器端日誌中打印錯誤，但返回給用戶一個更通用的訊息
        print("[錯誤] GEMINI_API_KEY 未設定。")
        raise HTTPException(status_code=500, detail="後端 AI 服務未正确配置。")

    # 組合最終的 Prompt，從 config 模組中獲取變數
    final_prompt = f"""
{config.SYSTEM_PROMPT}

{config.EVALUATION_SHEET}

---
现在，请根据上述规则和评估表，对以下视频内容进行分析。

[视频内容描述]
{video_description}
[视频内容描述结束]

请严格按照我指定的 JSON 格式输出你的分析结果，不要有任何额外的文字或解释。
"""

    # 構造 API 請求體
    payload = {
        "contents": [
            {
                "parts": [{"text": final_prompt}]
            }
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": config.JSON_RESPONSE_SCHEMA
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    print("--- 正在向 Gemini API 發送請求... ---")
    try:
        response = requests.post(config.GEMINI_API_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=60)
        response.raise_for_status()  # 如果請求失敗 (如 4xx 或 5xx)，則拋出異常

        response_json = response.json()
        
        # 提取 Gemini 生成的核心報告內容
        # 增加更安全的访问方式
        if not response_json.get('candidates'):
             print(f"[錯誤] API 回應中缺少 'candidates' 欄位。回應: {response_json}")
             raise HTTPException(status_code=500, detail="從 AI 服務收到的回應格式不正確。")

        report_text = response_json['candidates'][0]['content']['parts'][0]['text']
        report_data = json.loads(report_text)

        # 組合最終返回給前端的完整數據
        final_report = {
            "reportId": f"diag_report_{hash(video_description)}",
            "videoTitle": video_title,
            "aiModelVersion": "ShortFormVideo_Assessor_V3.1_Gemini",
            **report_data
        }
        
        print("--- 成功從 Gemini API 接收並解析報告。 ---")
        return final_report

    except requests.exceptions.RequestException as e:
        print(f"[錯誤] API 請求失敗: {e}")
        # 如果有回應內容，也一併打印出來
        error_details = e.response.text if e.response else "No response from server."
        print(f"Server response: {error_details}")
        raise HTTPException(status_code=502, detail=f"AI 服務請求失敗: {e}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[錯誤] 解析 API 回應失敗: {e}")
        # 附上收到的原始 body 以便 debug
        response_body = response.text if 'response' in locals() and response.text else "No response body."
        print(f"Raw response body: {response_body}")
        raise HTTPException(status_code=500, detail=f"解析 AI 服務回應時出錯: {e}")


@app.post("/diagnose")
async def diagnose_endpoint(request: dict):
    """
    API 端點，接收前端請求，調用診斷函式並返回結果。
    """
    file_name = request.get("fileName")
    if not file_name:
        raise HTTPException(status_code=400, detail="請求中未包含 'fileName'。")

    # 注意：这是一个临时桥接方案。
    # 目前，无论上传什么视频，后端都会使用一个固定的视频描述来进行AI分析。
    # 这是为了方便测试端到端的流程。
    video_description = """
    这是一个典型的第一人称视角（POV）游戏实况片段，时长约20秒。
    记录了玩家在《塞尔达传说：王国之泪》中一个精彩的战斗瞬间。
    视频内容如下：
    0-6秒：主角（林克）站在一个高台上，下方有多个魔像敌人。所有敌人都用激光瞄准主角，发出“滴滴”的警报声，气氛紧张，危机四伏。
    7-12秒：玩家触发了“林克时间”（子弹时间），周围一切变慢。玩家冷静地打开武器选择轮盘，选择了“炸弹花”和箭矢进行组合。
    12-14秒：玩家瞄准下方的敌人中心，射出带有炸弹花的关键一箭。
    14-15秒：炸弹在敌人中心引发巨大爆炸，瞬间清空了所有敌人。
    15-20秒：危机解除，主角从高台跳下，平稳落地，展示战果。
    整个视频没有剪辑，没有额外配音或字幕，使用的是游戏内原生的画面和音效。
    """
    # 使用前端传来的真实文件名
    video_title = file_name

    print(f"正在為 '{video_title}' 開始影片診斷 (使用預設描述)...")
    
    diagnostic_report = diagnose_video_with_gemini(
        video_description=video_description,
        video_title=video_title
    )

    return diagnostic_report

# 静态文件服务
app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('public/index.html')

@app.get("/{catchall:path}")
async def read_other_files(catchall: str):
    # 尝试从 public 目录中提供文件
    file_path = f"public/{catchall}"
    if ".." in file_path or file_path.startswith('/'):
        # 安全性检查，防止路径遍历攻击
        return FileResponse('public/index.html')
    
    # 检查文件是否存在，如果存在则返回，否则返回 index.html
    import os
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
        
    return FileResponse('public/index.html')


if __name__ == "__main__":
    print("--- 啟動後端伺服器 ---")
    print("請在瀏覽器中打開前端頁面: http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

