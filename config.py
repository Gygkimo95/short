import os

# --- 1. API 金鑰與端點設定 ---
# 建議將金鑰儲存在環境變數中，以提高安全性。
# 在您的伺服器環境中設定： export GEMINI_API_KEY="YOUR_API_KEY"
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    print("警告：未在環境變數中找到 GEMINI_API_KEY。請設定該變數。")
    # 您也可以在此處臨時填寫金鑰進行測試，但不建議在生產環境中使用。
    # API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    
GEMINI_API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

# --- 2. AI 角色與任務指令 (Prompt) ---
SYSTEM_PROMPT = """
角色：你是一个专业的短剧切片评估人员，评估切片视频是否有爆火的能力。
任务：文档是你抽象出来的评估表，需要你结合评估表，分析并评估当前视频的实际综合素质，并给出优缺点及优化建议。
要求：需要审慎、严格地评估，若评估结果较好，但实际播放效果不理想，我们将取消你的评估资质。

目的与目标：
帮助用户评估其短剧切片视频的爆火潜力。
提供客观、专业的评估，涵盖视频的各个方面。
给出具体、可操作的优化建议，以提高视频的吸引力与传播效果。

行为与规则：
1. 评估流程:
   a) 我将提供一个视频的详细文字描述。
   b) 你必须严格根据下方提供的 [评估表] 对视频进行全面分析。
   c) 评估维度包括故事冲突、节奏感、人物塑造、剪辑手法、音效与配乐、标题与封面设计。
   d) 你需要在我指定的JSON结构中，提供详细的评分和文字分析。
2. 评估结果呈现:
   a) 在JSON中明确列出视频的优点和缺点。
   b) 给出针对性的、可执行的优化建议。
3. 语气与态度:
   a) 保持专业、审慎、严谨的评估态度。
   b) 语言客观、中立，避免使用主观色彩过强的词汇。
   c) 在给出负面评价时，应以建设性的优化建议作为补充。
"""

# --- 3. 評估量表 ---
EVALUATION_SHEET = """
[评估表：抖音短剧切片爆款潜力终极自评表 V3.1]
评分哲学：拒绝“平均主义”，为长板打高分，为短板打低分。理解“指数化”分差，9分代表“天花板”，10分代表“开创性”。
评估标准等级：95+ (SSS级), 85-94 (A+级), 80-84 (A级), 70-79 (B级), <70 (C级)。

一级维度与权重:
一、黄金开局吸引力 (25%)
    1.1 初始钩子强度 (10%)
    1.2 情境代入速度 (7%)
    1.3 前5秒资讯有效性 (8%)
二、剧情节奏与爽点密度 (25%)
    2.1 核心冲突清晰度 (7%)
    2.2 关键反转与爽点 (12%)
    2.3 叙事推进效率 (6%)
三、情绪价值与角色共鸣 (20%)
    3.1 情绪体验曲线 (8%)
    3.2 普适价值内核 (6%)
    3.3 角色人设塑造 (6%)
四、传播分享驱动力 (10%)
    4.1 结尾悬念/记忆点 (6%)
    4.2 社交货币价值 (4%)
五、基础制作质量 (5%)
    5.1 视听体验与演员表现 (5%)
六、市场竞争力与传播辨识度 (15%)
    6.1 剧情/人设新颖度 (7%)
    6.2 “记忆锚点”强度 (5%)
    6.3 封面/标题吸引力 (3%)
"""

# --- 4. Gemini API 的 JSON 輸出格式定義 (Schema) ---
JSON_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "overallScore": {"type": "NUMBER", "description": "综合评分 (0-100)"},
        "potentialLevel": {"type": "STRING", "description": "潜力等级 (A, B, C等)"},
        "potentialLevelText": {"type": "STRING", "description": "潜力等级的文字描述"},
        "conclusion": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "一句话结论，如'建议优化后再发布'"},
                "description": {"type": "STRING", "description": "对结论的简短描述"}
            }
        },
        "detailedAnalysis": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "default": "详细视频分析"},
                "sections": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "dimension": {"type": "STRING", "description": "分析维度，如'画面构造'"},
                            "content": {"type": "STRING", "description": "对该维度的详细文字分析"}
                        }
                    }
                }
            }
        },
        "overallReview": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "default": "综合评价与优化建议"},
                "pros": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "优点列表"},
                "cons": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "缺点列表"},
                "optimizationDirections": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "priority": {"type": "STRING", "description": "优化建议的优先级 (高, 中, 低)"},
                            "direction": {"type": "STRING", "description": "具体的优化建议文字"}
                        }
                    }
                }
            }
        },
        "optimizedScripts": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "default": "优化后的脚本方案"},
                "scripts": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "style": {"type": "STRING", "description": "脚本风格，如'酷炫技巧流'"},
                            "description": {"type": "STRING", "description": "对风格和BGM的描述"},
                            "steps": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "time": {"type": "STRING", "description": "时间点，如'0-3s'"},
                                        "picture": {"type": "STRING", "description": "画面描述"},
                                        "voice": {"type": "STRING", "description": "语音或字幕内容"},
                                        "sfx": {"type": "STRING", "description": "音效或剪辑说明"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
