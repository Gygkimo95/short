import json
import asyncio
import google.generativeai as genai
import config  # 导入我们建立的配置文件

from fastapi import FastAPI, HTTPException, UploadFile, File
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

# --- Google AI SDK 初始化 ---
# 在应用启动时配置好SDK
if not config.API_KEY:
    print("错误：未在环境变量中找到 GEMINI_API_KEY。服务将无法处理AI请求。")
    # 在这种情况下，让应用启动，但后续的AI调用会失败
else:
    genai.configure(api_key=config.API_KEY)


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

    # 我们不再需要手动读取字节。 video_title 的获取保持不变。
    video_title = video_file.filename or "untitled.mp4"
    
    print(f"--- 正在上传视频 '{video_title}' 到 Google AI... ---")
    
    try:
        # 1. 上传文件到 Google AI
        # 修正：直接将 FastAPI 的文件对象 (video_file) 传递给 SDK。
        # SDK 能够处理这种文件流对象。
        # 同时，明确提供 mime_type 以获得最佳效果。
        print(f"Uploading file '{video_title}' with mime_type: {video_file.content_type}")
        video_file_gai = genai.upload_file(
            path=video_file.file, # <--- 关键修正
            display_name=f"short-video-diag-{video_title}",
            mime_type=video_file.content_type
        )
        
        # 轮询文件状态，直到它准备好或失败
        while video_file_gai.state.name == "PROCESSING":
            print("视频正在处理中，请稍候...")
            await asyncio.sleep(5) # 使用异步sleep
            video_file_gai = genai.get_file(video_file_gai.name)

        if video_file_gai.state.name == "FAILED":
            print(f"[错误] Google AI 文件处理失败: {video_file_gai.state}")
            raise HTTPException(status_code=500, detail="AI 服务无法处理上传的视频文件。")

        print(f"--- 视频上传成功，文件名为: {video_file_gai.name} ---")

        # 2. 准备 Prompt 和模型配置
        # 将所有文字指令合并成一个大的 prompt 字符串
        full_prompt_text = f"""
{config.SYSTEM_PROMPT}

{config.EVALUATION_SHEET}

---
现在，请根据上述规则和评估表，对这个视频文件进行全面分析。请严格按照我指定的 JSON 格式输出你的分析结果。
"""
        
        # 构造一个包含文本和视频的 list，作为 `contents` 参数
        # 这与 curl 示例中的 `parts` 数组概念上是对应的
        # SDK 会自动处理这个 list，将其转换为正确的 API 请求格式
        prompt_parts = [full_prompt_text, video_file_gai]
        
        model = genai.GenerativeModel(
            model_name=config.MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": config.JSON_RESPONSE_SCHEMA
            }
        )
        
        # 3. 调用模型进行分析
        print("--- 正在向 Gemini Pro 1.5 发送分析请求... ---")
        response = await model.generate_content_async(prompt_parts)
        
        # 提取并解析报告
        report_text = response.text
        report_data = json.loads(report_text)
        
        final_report = {
            "reportId": f"diag_report_{hash(video_title)}",
            "videoTitle": video_title,
            "aiModelVersion": f"ShortFormVideo_Assessor_Gemini_{config.MODEL_NAME}",
            **report_data
        }

        print("--- 成功从 Gemini API 接收并解析报告。 ---")
        return final_report

    except Exception as e:
        # 统一的异常处理
        print(f"[严重错误] 在处理视频或调用AI时发生未知错误: {e}")
        # 增加更详细的错误日志
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"处理视频时发生内部错误: {str(e)}")

    finally:
        # 4. 清理资源：无论成功与否，都尝试删除上传的文件
        if 'video_file_gai' in locals() and video_file_gai:
            try:
                print(f"--- 正在从 Google AI 删除临时文件: {video_file_gai.name} ---")
                await genai.delete_file_async(video_file_gai.name)
                print("--- 临时文件删除成功。 ---")
            except Exception as e:
                # 如果删除失败，只记录日志，不影响给用户的返回结果
                print(f"[警告] 删除 Google AI 上的临时文件失败: {e}")


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

