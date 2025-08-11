import json
import asyncio
import google.generativeai as genai
import config  # 導入我們建立的配置文件
import tempfile # 導入 tempfile 模块
import os # 導入 os 模块
import re
import unicodedata
import base64, binascii
import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# 调试总开关与日志目录
DEBUG_GEMINI = True  # 生产环境可改为 False，或用环境变量控制
LOG_DIR = Path(os.getenv("GEMINI_LOG_DIR", "/opt/short/logs"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 允许所有来源的CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应配置为更严格的来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Google AI SDK 初始化 ---
# 在应用启动时配置好SDK
if not config.API_KEY:
    print("错误：未在环境变量中找到 GEMINI_API_KEY。服务将无法处理AI请求。")
    # 在这种情况下，让应用启动，但后续的AI调用会失败
else:
    genai.configure(api_key=config.API_KEY)


def _extract_json_from_response(resp):
    """从AI响应中提取并解析JSON数据。"""
    try:
        # 优先使用 response.text，因为它通常包含了完整的文本输出
        raw_text = resp.text
        return _parse_model_json(raw_text)
    except (ValueError, AttributeError, json.JSONDecodeError) as e:
        print(f"[警告] 使用 response.text 解析失败: {e}。尝试遍历 parts。")
        # 如果 response.text 解析失败，则回退到遍历 parts
        try:
            for cand in getattr(resp, "candidates", []):
                for p in getattr(getattr(cand, "content", None), "parts", []):
                    if hasattr(p, "text") and p.text:
                        # 只要找到第一个文本部分就尝试解析
                        return _parse_model_json(p.text)
        except (ValueError, AttributeError, json.JSONDecodeError) as final_e:
             raise HTTPException(status_code=500, detail=f"AI返回的内容无法解析为有效的JSON: {final_e}")
    raise HTTPException(status_code=500, detail="AI响应中未找到可解析的JSON文本。")


def _parse_model_json(s: str):
    """
    一个更健壮的JSON解析器，用于清理AI可能返回的非标准格式。
    """
    if not isinstance(s, str):
        raise TypeError(f"Expected a string to parse, but got {type(s)}")

    # --- 核心清理步骤 ---
    # 1. 移除AI返回中可能包含的markdown代码块标记
    s = re.sub(r"^\s*```json\s*", "", s, flags=re.DOTALL)
    s = re.sub(r"\s*```\s*$", "", s, flags=re.DOTALL)
    
    # 2. 显式移除零宽空格 (U+200B) 和其他常见问题字符
    s = s.replace('\u200b', '')
    
    # 3. 去除首尾的空白字符
    s = s.strip()

    # --- 新增调试打印 ---
    if DEBUG_GEMINI:
        print("\n==================================================")
        print("=== START: Cleaned Text for JSON Parsing ===")
        print("==================================================")
        print(s)
        print("==================================================")
        print("=== END: Cleaned Text for JSON Parsing ===")
        print("==================================================\n")
    # --- 调试打印结束 ---

    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        print(f"[严重错误] JSON解析失败: {e}")
        print(f"解析失败的内容 (前500字符): {s[:500]}")
        raise HTTPException(status_code=500, detail=f"JSON解析错误: {e}")


def _debug_print_response_structure(resp):
    if not DEBUG_GEMINI: return
    try:
        cands = getattr(resp, "candidates", []) or []
        print(f"[DEBUG] candidates={len(cands)}")
        for ci, cand in enumerate(cands):
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", []) if content else []
            print(f"[DEBUG] - cand[{ci}] parts={len(parts)}")
            for pi, p in enumerate(parts):
                if hasattr(p, "text") and p.text:
                    preview = repr(p.text[:200]) # 使用 repr 更能看清特殊字符
                    print(f"[DEBUG]   - part[{pi}] type=text len={len(p.text)} preview={preview}")
                elif hasattr(p, "inline_data") and p.inline_data:
                    mt = getattr(p.inline_data, "mime_type", "")
                    data = getattr(p.inline_data, "data", b"")
                    size = len(data) if isinstance(data, (bytes, bytearray)) else len(str(data))
                    print(f"[DEBUG]   - part[{pi}] type=inline_data mime={mt} size={size}")
                else:
                    print(f"[DEBUG]   - part[{pi}] type=unknown")
    except Exception as e:
        print(f"[DEBUG] inspect response failed: {e}")

def _debug_dump_response(resp):
    # 此函数用于将最原始的响应结构记录到日志文件
    if not DEBUG_GEMINI: return
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = LOG_DIR / f"gemini_raw_{ts}.json"
        payload = {"candidates": []}
        for cand in getattr(resp, "candidates", []) or []:
            c = {"parts": []}
            parts = getattr(getattr(cand,"content",None),"parts",[]) or []
            for p in parts:
                if hasattr(p, "text") and p.text:
                    c["parts"].append({"type": "text", "text": p.text})
                elif hasattr(p, "inline_data") and p.inline_data:
                    mt = getattr(p.inline_data, "mime_type", "")
                    data = getattr(p.inline_data, "data", b"")
                    # 为了日志可读，对二进制数据进行base64编码
                    if isinstance(data, (bytes, bytearray)):
                        preview = base64.b64encode(data[:1024]).decode("utf-8")
                        c["parts"].append({"type":"inline_data","mime_type":mt,"data_base64_preview":preview,"note":"first 1KB"})
                    else:
                        c["parts"].append({"type":"inline_data","mime_type":mt,"data_preview":str(data)[:1024]})
                elif hasattr(p, "file_data") and p.file_data:
                    c["parts"].append({"type":"file_data","file_uri":getattr(p.file_data,"file_uri","")})
                else:
                    c["parts"].append({"type":"unknown"})
            payload["candidates"].append(c)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] full response dumped to: {path}")
    except Exception as e:
        print(f"[DEBUG] dump response failed: {e}")


# 新增辅助函数：检查是否包含文本部分
def _has_text_parts(resp) -> bool:
    for cand in getattr(resp, "candidates", []) or []:
        content = getattr(cand, "content", None)
        for p in getattr(content, "parts", []) or []:
            if getattr(p, "text", None):
                return True
    return False


# 新增辅助函数：打印 finish_reason 与可能的安全信息
def _debug_print_finish_and_safety(resp):
    if not DEBUG_GEMINI:
        return
    try:
        for ci, cand in enumerate(getattr(resp, "candidates", []) or []):
            fr = getattr(cand, "finish_reason", None)
            print(f"[DEBUG] - cand[{ci}] finish_reason={fr}")
            safety = getattr(cand, "safety_ratings", None) or getattr(cand, "safety_feedback", None)
            if safety:
                print(f"[DEBUG] - cand[{ci}] safety={safety}")
    except Exception as e:
        print(f"[DEBUG] finish/safety inspect failed: {e}")


async def diagnose_video_with_gemini(video_file: UploadFile):
    if not config.API_KEY:
        raise HTTPException(status_code=500, detail="后端 AI 服务未正确配置 API 密钥。")

    local_tmp_path = None
    video_file_gai = None
    try:
        # 1. 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as tmp:
            content = await video_file.read()
            tmp.write(content)
            local_tmp_path = tmp.name
        
        video_title = video_file.filename or "untitled.mp4"
        print(f"视频已保存到本地临时文件: {local_tmp_path}")
        print(f"--- 正在上传视频 '{video_title}' 到 Google AI... ---")
        
        # 2. 上传文件到 Google AI
        video_file_gai = genai.upload_file(
            path=local_tmp_path,
            display_name=f"short-video-diag-{video_title}",
            mime_type=video_file.content_type
        )
        
        while video_file_gai.state.name == "PROCESSING":
            print("视频正在处理中，请稍候...")
            await asyncio.sleep(5)
            video_file_gai = genai.get_file(video_file_gai.name)

        if video_file_gai.state.name == "FAILED":
            raise HTTPException(status_code=500, detail="AI 服务无法处理上传的视频文件。")

        print(f"--- 视频上传成功，文件名为: {video_file_gai.name} ---")

        # 3. 准备 Prompt 和模型
        full_prompt_text = f"{config.SYSTEM_PROMPT}\n\n{config.EVALUATION_SHEET}\n\n---\n现在，请根据上述规则和评估表，对这个视频文件进行全面分析。请严格按照我指定的 JSON 格式输出你的分析结果。"
        # 将视频放在前、文本在后
        prompt_parts = [video_file_gai, full_prompt_text]
        
        model = genai.GenerativeModel(
            model_name=config.MODEL_NAME,
            # ======================================================================
            # --- 變更重點 ---
            #
            # 移除了 "response_mime_type" 和 "response_schema"，
            # 讓AI以純文本模式回應。我們現在依賴 config.py 中更強的
            # Prompt指令來引導AI生成結構化的JSON文本。
            #
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0,
            }
            #
            # ======================================================================
        )
        
        # 4. 调用模型
        print("--- 正在向 Gemini 发送分析请求 (文本模式)... ---")
        response = await model.generate_content_async(prompt_parts)

        # 打印原始响应以供调试
        print("\n==================================================")
        print("=== START: AI Raw Response Text ===")
        print("==================================================")
        try:
            print(response.text)
        except Exception as e:
            print(f"无法打印 response.text: {e}")
        print("==================================================")
        print("=== END: AI Raw Response Text ===")
        print("==================================================\n")

        _debug_print_response_structure(response)
        _debug_print_finish_and_safety(response)
        _debug_dump_response(response)

        # 提取并解析JSON
        report_data = _extract_json_from_response(response)
        
        print("=== 解析后的最终 JSON 数据结构 ===")
        print(json.dumps(report_data, indent=2, ensure_ascii=False))
        print("=== JSON 数据结构结束 ===")
        
        final_report = {
            "reportId": f"diag_report_{hash(video_title)}",
            "videoTitle": video_title,
            "aiModelVersion": f"ShortFormVideo_Assessor_Gemini_{config.MODEL_NAME}",
            **report_data
        }

        print("--- 成功从 Gemini API 接收并解析报告。 ---")
        return final_report

    except Exception as e:
        print(f"[严重错误] 在处理视频或调用AI时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理视频时发生内部错误: {str(e)}")

    finally:
        # 5. 清理资源
        if video_file_gai:
            try:
                print(f"--- 正在从 Google AI 删除临时文件: {video_file_gai.name} ---")
                genai.delete_file(video_file_gai.name)
                print("--- Google AI 临时文件删除成功。 ---")
            except Exception as e:
                print(f"[警告] 删除 Google AI 上的临时文件失败: {e}")
        
        if local_tmp_path and os.path.exists(local_tmp_path):
            os.remove(local_tmp_path)
            print(f"--- 本地临时文件删除成功: {local_tmp_path} ---")


@app.post("/diagnose")
async def diagnose_endpoint(video: UploadFile = File(...)):
    if not video.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="上传的文件不是有效的视频格式。")
    print(f"接收到上传文件: {video.filename}, 类型: {video.content_type}")
    return await diagnose_video_with_gemini(video)

# 静态文件服务
app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('public/index.html')

@app.get("/{catchall:path}")
async def read_other_files(catchall: str):
    file_path = os.path.join("public", catchall)
    if ".." in file_path or not os.path.normpath(file_path).startswith("public"):
        return FileResponse('public/index.html')
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse('public/index.html')


if __name__ == "__main__":
    print("--- 启动后端服务器 ---")
    print("请在浏览器中打开前端页面: http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
