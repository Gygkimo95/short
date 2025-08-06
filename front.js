import React, { useState, useCallback } from 'react';

// ==============================================================================
// 模擬後端 API 服務
// 在真實應用中，這部分邏輯應位於後端伺服器上。
// ==============================================================================
const mockApi = {
    // 模擬後端根據影片特徵生成報告的核心方法
    generateReport: (fileName) => {
        // 模擬 AI 分析影片後得出的量化特徵
        // 這裡我們根據檔名簡單模擬幾種不同的影片類型
        let features;
        if (fileName.includes('zelda') || fileName.includes('game')) {
            // 遊戲高光時刻，操作好但製作糙
            features = { score: 78, type: 'good' };
        } else if (fileName.includes('perfect') || fileName.includes('final')) {
            // 製作精良的成片
            features = { score: 92, type: 'excellent' };
        } else {
            // 有明顯短板的素材
            features = { score: 59, type: 'improve' };
        }

        // 根據特徵從報告模板庫中生成完整報告
        const reportTemplates = {
            excellent: {
                score: features.score,
                conclusion: '表现非常出色',
                conclusionClass: 'text-green-600',
                description: '已超越大部分同类作品，建议立即发布！',
                suggestions: [
                    { priority: '亮点', priorityClass: 'bg-green-500', title: '黄金5秒钩子', description: '视频开头的悬念设置非常成功，能迅速抓住用户注意力，这是爆款的关键！' },
                    { priority: '微调', priorityClass: 'bg-blue-500', title: '字幕样式', description: '可尝试为字幕增加轻微的动态效果，让信息呈现更生动。' }
                ]
            },
            good: {
                score: features.score,
                conclusion: '建议优化后再发布',
                conclusionClass: 'text-orange-500',
                description: '整体不错，有爆款潜质！根据以下建议优化后，效果会更佳。',
                videoAnalysis: {
                    title: '详细视频分析',
                    items: [
                        { title: '画面构造', content: '采用双层构图。前景是玩家的双手和手柄，后景是游戏画面。视角为严格的第一人称，沉浸感很强。' },
                        { title: '剪辑手法', content: '视频采用了“一镜到底”的拍摄方式，优点是真实、原始，缺点是节奏完全依赖于游戏本身。' },
                        { title: '音效和BGM', content: '所有声音都来自游戏内部，完全依赖《塞尔达》本身出色的音效设计来驱动情绪，但没有添加任何额外的音乐或音效来增强表现力。' },
                        { title: '结构逻辑', content: '叙事结构遵循了经典的“问题出现 -> 构思对策 -> 解决问题 -> 展示结果”模型，逻辑清晰，一气呵成。' }
                    ]
                },
                overallReview: {
                    title: '综合评分与优化建议',
                    pros: ['游戏操作本身很精彩', '第一人称视角代入感强', '完整记录了高光时刻'],
                    cons: ['制作上过于“原生态”', '缺乏后期包装和优化，在短视频平台很难脱颖而出'],
                    optimizationDirection: [
                        '增加“钩子” (Hook): 视频的前3秒必须抓住人心。',
                        '强化节奏: 使用剪辑来控制节奏，增强冲击力。',
                        '丰富听觉: 加入合适的BGM和音效。',
                        '赋予意义: 通过文案（语音或字幕）为操作赋予一个主题。'
                    ]
                },
                optimizedScripts: {
                    title: '优化后的脚本方案',
                    scripts: [
                        {
                            title: '方案一：酷炫技巧流',
                            description: '风格: 快节奏、强卡点、炫技教学。BGM: 节奏感强烈的电子乐或Trap音乐。',
                            steps: [
                                { time: '0-1s', picture: '【快切】 炸弹爆炸瞬间的特写。', voice: '（无语音）', sfx: '爆炸巨响 + 强节奏BGM起' },
                                { time: '1-3s', picture: '画面切回开头，林克站在高台，被多个激光瞄准。', voice: '“被这样围攻，你是不是只会跑？”', sfx: 'BGM变弱，突出敌人警报声' },
                                { time: '3-6s', picture: '玩家进入林克时间，特写选中“炸弹花”。', voice: '“别慌，让子弹飞一会儿。”', sfx: '“叮”的选中音效，画面轻微放大' },
                                { time: '8-10s', picture: '【高潮】 炸弹爆炸，清空全场。', voice: '“BOOM！”', sfx: 'BGM达到高潮，与爆炸声完美卡点' }
                            ]
                        },
                        {
                            title: '方案二：幽默整活流',
                            description: '风格: 搞笑、玩梗、反转。BGM: 前期用滑稽的音乐，高潮用反差大的激昂音乐。',
                            steps: [
                                 { time: '0-3s', picture: '林克被多个激光瞄准，镜头来回切换。', voice: '（字幕）敌人：“优势在我！五打一，你能秒我？”', sfx: '紧张又带点滑稽的音乐' },
                                 { time: '3-6s', picture: '玩家进入林克时间，慢悠悠地选武器。', voice: '（字幕）我：“哦？是吗？”', sfx: '音乐暂停，加个黑人问号的Meme贴图' },
                                 { time: '8-10s', picture: '【高潮】 炸弹爆炸，清空全场。', voice: '（字幕可配一个“？”或者“秒了”）', sfx: '音乐高潮卡点爆炸' }
                            ]
                        },
                    ]
                }
            },
            improve: {
                score: features.score,
                conclusion: '有待提升',
                conclusionClass: 'text-red-600',
                description: '作品有较大提升空间，建议根据以下核心问题修改后，再重新诊断。',
                suggestions: [
                    { priority: '高优先级', priorityClass: 'bg-red-500', title: '音频质量', description: '音频是核心短板，检测到明显的环境噪音，这会严重影响完播率，请务必优先处理。' },
                    { priority: '高优先级', priorityClass: 'bg-red-500', title: '画面稳定性', description: '视频中段有明显晃动，建议使用稳定器或进行后期防抖处理。' }
                ]
            }
        };
        
        return reportTemplates[features.type];
    },

    // 模拟 API 請求
    fetchReport: function(fileName) {
        console.log(`[API] Received request for file: ${fileName}`);
        return new Promise(resolve => {
            setTimeout(() => {
                const report = this.generateReport(fileName);
                console.log(`[API] Responding with report. Score: ${report.score}`);
                resolve(report);
            }, 2500); // 模擬 2.5 秒的網絡和處理延遲
        });
    }
};

// Component: Header
const Header = () => (
    <header className="text-center mb-10">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">爆款打造大师</h1>
        <p className="text-gray-600">上传您的视频，获取专业的AI诊断与优化建议</p>
    </header>
);

// Component: UploadView
const UploadView = ({ onFileSelect, onStartAnalysis, selectedFile, isStartEnabled }) => (
    <div id="upload-view">
        <h2 className="text-xl font-semibold mb-4 text-center">开始诊断您的视频</h2>
        <label htmlFor="video-upload" className="w-full flex flex-col justify-center items-center px-4 py-12 bg-slate-50 text-blue-600 rounded-xl shadow-inner tracking-wide border-2 border-dashed border-gray-300 cursor-pointer hover:bg-blue-50 hover:border-blue-400 transition-all duration-300">
            <svg className="w-12 h-12 mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
            <span className="text-lg font-medium leading-normal">点击上传 或 将文件拖拽于此</span>
            <p className="text-xs text-gray-500 mt-1">支持 MP4, MOV, AVI 等格式</p>
            <input type='file' className="hidden" id="video-upload" onChange={onFileSelect} />
        </label>
        {selectedFile && (
            <div className="text-center mt-4">
                <p className="text-sm text-gray-600">已选择文件: <span className="font-medium text-gray-800">{selectedFile.name}</span></p>
            </div>
        )}
        <div className="text-center mt-6">
            <button onClick={onStartAnalysis} disabled={!isStartEnabled} className="bg-blue-600 text-white font-semibold py-3 px-12 rounded-lg hover:bg-blue-700 transition-all duration-300 disabled:bg-gray-300 disabled:cursor-not-allowed">
                开始诊断
            </button>
        </div>
    </div>
);

// Component: AnalysisView
const AnalysisView = () => (
    <div className="text-center py-12">
        <div className="inline-block loader"></div>
        <h3 className="text-xl font-semibold mt-6 text-gray-800">AI 正在进行深度诊断...</h3>
        <p className="text-gray-500 mt-2">正在进行多维度数据比对，请稍候。</p>
    </div>
);

// Sub-Component: OptimizedScriptsSection
const OptimizedScriptsSection = ({ scripts }) => {
    const [activeTab, setActiveTab] = useState(0);
    const activeScript = scripts[activeTab];

    return (
        <div className="analysis-section">
            <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">优化后的脚本方案</h3>
            <div className="flex border-b mb-4 overflow-x-auto">
                {scripts.map((script, index) => (
                    <button
                        key={index}
                        className={`script-tab py-2 px-4 font-medium text-sm border-b-2 flex-shrink-0 ${activeTab === index ? 'active' : 'border-transparent'}`}
                        onClick={() => setActiveTab(index)}
                    >
                        {script.title.split('：')[1]}
                    </button>
                ))}
            </div>
            <div className="bg-white p-4 rounded-lg border">
                <p className="text-sm text-gray-600 mb-4">{activeScript.description}</p>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left min-w-[600px]">
                        <thead className="bg-slate-50 text-xs text-gray-700 uppercase">
                            <tr>
                                <th scope="col" className="px-4 py-2">时间(秒)</th>
                                <th scope="col" className="px-4 py-2">画面</th>
                                <th scope="col" className="px-4 py-2">语音/字幕</th>
                                <th scope="col" className="px-4 py-2">音效/剪辑</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activeScript.steps.map((step, idx) => (
                                <tr key={idx} className="border-b">
                                    <td className="px-4 py-2 font-medium">{step.time}</td>
                                    <td className="px-4 py-2">{step.picture}</td>
                                    <td className="px-4 py-2">{step.voice}</td>
                                    <td className="px-4 py-2 text-blue-600">{step.sfx}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

// Component: ReportView
const ReportView = ({ onReset, reportData }) => {
    if (!reportData) return null;

    const { score, conclusion, conclusionClass, description } = reportData;

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">诊断报告</h2>
                <button onClick={onReset} className="bg-gray-200 text-gray-700 font-semibold py-2 px-4 rounded-lg hover:bg-gray-300 transition-all duration-300 text-sm">诊断新视频</button>
            </div>
            
            <div id="report-content">
                <div className="bg-slate-50 p-6 rounded-xl border border-gray-200 text-center report-card mb-8">
                    <p className="text-lg text-gray-600">综合评分</p>
                    <p className={`text-6xl font-bold my-2 ${conclusionClass}`}>{score}<span className="text-2xl text-gray-500">/100</span></p>
                    <p className={`text-xl font-semibold ${conclusionClass}`}>{conclusion}</p>
                    <p className="text-sm text-gray-500 mt-1">{description}</p>
                </div>
                
                {reportData.videoAnalysis ? (
                    <>
                        <div className="analysis-section mb-8">
                            <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">详细视频分析</h3>
                            <dl className="space-y-4">
                                {reportData.videoAnalysis.items.map((item, index) => (
                                    <div key={index} className="bg-white p-4 rounded-lg border">
                                        <dt className="font-semibold text-gray-900">{item.title}</dt>
                                        <dd className="text-sm text-gray-600 mt-1">{item.content}</dd>
                                    </div>
                                ))}
                            </dl>
                        </div>
                        <div className="analysis-section mb-8">
                            <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">综合评价与优化建议</h3>
                            <div className="grid md:grid-cols-2 gap-6">
                                <div className="bg-white p-4 rounded-lg border">
                                    <h4 className="font-semibold text-green-600 mb-2">优点 (Pros)</h4>
                                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                                        {reportData.overallReview.pros.map((pro, i) => <li key={i}>{pro}</li>)}
                                    </ul>
                                </div>
                                <div className="bg-white p-4 rounded-lg border">
                                    <h4 className="font-semibold text-red-600 mb-2">缺点 (Cons)</h4>
                                    <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                                        {reportData.overallReview.cons.map((con, i) => <li key={i}>{con}</li>)}
                                    </ul>
                                </div>
                            </div>
                            <div className="bg-white p-4 rounded-lg border mt-6">
                                <h4 className="font-semibold text-blue-600 mb-2">优化方向</h4>
                                <ul className="list-decimal list-inside space-y-1 text-sm text-gray-600">
                                    {reportData.overallReview.optimizationDirection.map((dir, i) => <li key={i}>{dir}</li>)}
                                </ul>
                            </div>
                        </div>
                        <OptimizedScriptsSection scripts={reportData.optimizedScripts.scripts} />
                    </>
                ) : (
                    <div className="mt-8">
                        <h3 className="text-lg font-semibold mb-4 text-center">具体诊断建议</h3>
                        <ul className="space-y-4">
                            {reportData.suggestions.map((s, i) => (
                                <li key={i} className="flex items-start p-4 bg-slate-50 border-l-4 rounded-r-lg" style={{ borderColor: s.priorityClass.match(/bg-([a-z]+)-500/)[0].replace('bg-','').replace('-500','') }}>
                                    <span className={`text-xs font-bold text-white rounded-full px-2.5 py-1 mr-4 ${s.priorityClass}`}>{s.priority}</span>
                                    <div>
                                        <p className="font-semibold">{s.title}</p>
                                        <p className="text-sm text-gray-600">{s.description}</p>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    );
};


// Main App Component
export default function App() {
    const [view, setView] = useState('upload'); // 'upload', 'analysis', 'report'
    const [selectedFile, setSelectedFile] = useState(null);
    const [reportData, setReportData] = useState(null);

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (file) {
            setSelectedFile(file);
        }
    };

    const handleStartAnalysis = useCallback(async () => {
        if (!selectedFile) return;
        
        setView('analysis');
        
        // Call the mock API
        const data = await mockApi.fetchReport(selectedFile.name);
        
        setReportData(data);
        setView('report');

    }, [selectedFile]);

    const handleReset = useCallback(() => {
        setView('upload');
        setSelectedFile(null);
        setReportData(null);
        const fileInput = document.getElementById('video-upload');
        if(fileInput) fileInput.value = '';
    }, []);

    return (
        <div className="container mx-auto p-4 md:p-8 max-w-4xl main-container">
            <Header />
            <main className="bg-white p-6 md:p-10 rounded-2xl shadow-lg border border-gray-200">
                {view === 'upload' && (
                    <UploadView 
                        onFileSelect={handleFileSelect}
                        onStartAnalysis={handleStartAnalysis}
                        selectedFile={selectedFile}
                        isStartEnabled={!!selectedFile}
                    />
                )}
                {view === 'analysis' && <AnalysisView />}
                {view === 'report' && (
                    <ReportView 
                        onReset={handleReset}
                        reportData={reportData}
                    />
                )}
            </main>
        </div>
    );
}
