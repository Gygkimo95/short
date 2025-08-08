import json
import asyncio
import google.generativeai as genai
import config  # 导入我们建立的配置文件
import tempfile # 导入 tempfile 模块
import os # 导入 os 模块
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
    try:
        for cand in getattr(resp, "candidates", []):
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for p in parts:
                inline = getattr(p, "inline_data", None)
                if inline and getattr(inline, "mime_type", "") == "application/json":
                    data = getattr(inline, "data", b"")
                    if isinstance(data, (bytes, bytearray)):
                        return json.loads(data.decode("utf-8", "ignore"))
                    try:
                        return json.loads(base64.b64decode(data).decode("utf-8", "ignore"))
                    except Exception:
                        return json.loads(str(data))
    except Exception:
        pass
    return None


def _parse_model_json(s: str):
    s = s.lstrip("\ufeff")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    s = s.replace("```json", "```").replace("```", "")
    # 括号平衡扫描，提取第一个完整 JSON 对象
    in_str = False; esc = False; depth = 0; start = None; frag = None
    for i, ch in enumerate(s):
        if esc: esc = False; continue
        if ch == '\\': esc = True; continue
        if ch == '"': in_str = not in_str; continue
        if in_str: continue
        if ch == '{':
            if depth == 0: start = i
            depth += 1
        elif ch == '}':
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    frag = s[start:i+1]; break
    if not frag:
        i = s.find('{')
        if i == -1:
            raise HTTPException(status_code=500, detail="AI返回的数据缺少有效JSON包裹")
        # 若缺失末尾括号，尽力补齐
        in_str = False; esc = False; depth = 0
        for ch in s[i:]:
            if esc: esc = False
            elif ch == '\\': esc = True
            elif ch == '"': in_str = not in_str
            elif not in_str:
                if ch == '{': depth += 1
                elif ch == '}': depth = max(0, depth-1)
        frag = s[i:] + ('}' * depth)
    # 把字符串内部的裸换行转义
    out=[]; in_str=False; esc=False
    for ch in frag:
        if esc: out.append(ch); esc=False
        elif ch == '\\': out.append(ch); esc=True
        elif ch == '"': out.append(ch); in_str = not in_str
        elif ch in '\r\n' and in_str: out.append('\\n')
        else: out.append(ch)
    cleaned = ''.join(out).strip()
    return json.loads(cleaned)


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
                    preview = p.text.replace("\n","\\n")[:200]
                    print(f"[DEBUG]   - part[{pi}] type=text len={len(p.text)} preview={preview}")
                elif hasattr(p, "inline_data") and p.inline_data:
                    mt = getattr(p.inline_data, "mime_type", "")
                    data = getattr(p.inline_data, "data", b"")
                    size = len(data) if isinstance(data, (bytes, bytearray)) else len(str(data))
                    print(f"[DEBUG]   - part[{pi}] type=inline_data mime={mt} size={size}")
                elif hasattr(p, "file_data") and p.file_data:
                    print(f"[DEBUG]   - part[{pi}] type=file_data uri={getattr(p.file_data,'file_uri','')}")
                else:
                    print(f"[DEBUG]   - part[{pi}] type=unknown")
    except Exception as e:
        print(f"[DEBUG] inspect response failed: {e}")

def _debug_dump_response(resp):
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


async def diagnose_video_with_gemini(video_file: UploadFile):
    """
    接收上传的视频文件，调用 Gemini API 执行完整的诊断流程并返回 JSON 报告。

    Args:
        video_file (UploadFile): 用户上传的视频文件对象。

    Returns:
        dict: 包含完整诊断报告的 Python 字典。
              如果 API 调用失败，则会引发 HTTPException。
    """
    if not config.API_KEY:
        raise HTTPException(status_code=500, detail="后端 AI 服务未正确配置 API 密钥。")

    local_tmp_path = None
    video_file_gai = None # 预先定义
    try:
        # 1. 将上传的文件保存到本地临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.filename)[1]) as tmp:
            content = await video_file.read()
            tmp.write(content)
            local_tmp_path = tmp.name
        
        video_title = video_file.filename or "untitled.mp4"
        print(f"视频已保存到本地临时文件: {local_tmp_path}")
        print(f"--- 正在上传视频 '{video_title}' 到 Google AI... ---")
        
        # 2. 从临时文件路径上传文件
        video_file_gai = genai.upload_file(
            path=local_tmp_path,
            display_name=f"short-video-diag-{video_title}",
            mime_type=video_file.content_type
        )
        
        # 轮询文件状态
        while video_file_gai.state.name == "PROCESSING":
            print("视频正在处理中，请稍候...")
            await asyncio.sleep(5)
            video_file_gai = genai.get_file(video_file_gai.name)

        if video_file_gai.state.name == "FAILED":
            print(f"[错误] Google AI 文件处理失败: {video_file_gai.state}")
            raise HTTPException(status_code=500, detail="AI 服务无法处理上传的视频文件。")

        print(f"--- 视频上传成功，文件名为: {video_file_gai.name} ---")

        # 3. 准备 Prompt 和模型配置
        full_prompt_text = f"""
{config.SYSTEM_PROMPT}

{config.EVALUATION_SHEET}

---
现在，请根据上述规则和评估表，对这个视频文件进行全面分析。请严格按照我指定的 JSON 格式输出你的分析结果。
"""
        
        prompt_parts = [full_prompt_text, video_file_gai]
        
        USE_RESPONSE_SCHEMA = True
        model = genai.GenerativeModel(
            model_name=config.MODEL_NAME,
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0,
                "response_mime_type": "application/json",
                **({"response_schema": config.JSON_RESPONSE_SCHEMA} if USE_RESPONSE_SCHEMA else {})
            }
        )
        
        # 4. 调用模型
        print("--- 正在向 Gemini Flash 发送分析请求... ---")
        response = await model.generate_content_async(prompt_parts)

        _debug_print_response_structure(response)
        _debug_dump_response(response)

        report_data = _extract_json_from_response(response)
        if report_data is None:
            report_text = response.text
            print("=== AI 返回的原始文本(截断) ===")
            print(report_text[:4000])
            print("=== 原始文本结束 ===")
            report_data = _parse_model_json(report_text)
        
        print("=== 解析后的 JSON 数据结构 ===")
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
        # 清理 Google AI 上的文件
        if video_file_gai:
            try:
                print(f"--- 正在从 Google AI 删除临时文件: {video_file_gai.name} ---")
                genai.delete_file(video_file_gai.name)
                print("--- Google AI 临时文件删除成功。 ---")
            except Exception as e:
                print(f"[警告] 删除 Google AI 上的临时文件失败: {e}")
        
        # 清理本地的临时文件
        if local_tmp_path and os.path.exists(local_tmp_path):
            os.remove(local_tmp_path)
            print(f"--- 本地临时文件删除成功: {local_tmp_path} ---")


@app.post("/diagnose")
async def diagnose_endpoint(video: UploadFile = File(...)):
    """
    API 端点，接收前端上传的视频文件，调用诊断函数并返回结果。
    """
    if not video.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="上传的文件不是有效的视频格式。")

    print(f"接收到上传文件: {video.filename}, 类型: {video.content_type}")
    
    diagnostic_report = await diagnose_video_with_gemini(video)

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
    print("--- 启动后端服务器 ---")
    print("请在浏览器中打开前端页面: http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

