import json
import requests
import config # 導入我們建立的設定檔

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
        return {"error": "GEMINI_API_KEY 未在 config.py 或環境變數中設定。"}

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
        response = requests.post(config.GEMINI_API_ENDPOINT, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # 如果請求失敗 (如 4xx 或 5xx)，則拋出異常

        response_json = response.json()
        
        # 提取 Gemini 生成的核心報告內容
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
        return {"error": f"API 請求失敗: {e}", "details": response.text if 'response' in locals() else "No response"}
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[錯誤] 解析 API 回應失敗: {e}")
        return {"error": f"解析 API 回應失敗: {e}", "response_body": response_json if 'response_json' in locals() else "No JSON response"}


# ==============================================================================
# 執行範例
# 這部分模擬了後端服務器接收到一個請求後的處理過程。
# ==============================================================================
if __name__ == "__main__":
    # 模擬用戶上傳的影片，我們將其轉換為詳細的文字描述
    # 這一步在真實應用中可能由另一個多模態模型完成，或要求用戶手動輸入
    zelda_video_description = """
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

    print("正在為 'zelda_game_clip.mp4' 開始影片診斷...")
    
    # 調用主函數，獲取診斷報告
    # 這一步相當於後端 API Endpoint 的核心邏輯
    diagnostic_report = diagnose_video_with_gemini(
        video_description=zelda_video_description,
        video_title="zelda_game_clip.mp4"
    )

    # 打印最終的 JSON 結果，這個結果將被發送給前端
    print("\n--- 將發送至前端的最終 JSON 報告 ---")
    print(json.dumps(diagnostic_report, indent=2, ensure_ascii=False))

