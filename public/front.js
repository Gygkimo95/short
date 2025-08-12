const { useState, useCallback } = React;

// ==============================================================================
// 模擬後端 API 服務 (此部分將被真實 API 調用取代)
// ==============================================================================
// const mockApi = { ... }; // 已移除 mockApi 物件

// Component: Header
const Header = () => (
    <header className="text-center mb-10">
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">爆款打造大师</h1>
        <p className="text-gray-600">上传您的视频，获取专业的AI诊断与优化建议</p>
    </header>
);

// Component: UploadView
const UploadView = ({ onFileSelect, onStartAnalysis, selectedFile, isStartEnabled, isLoading }) => (
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
            <button onClick={onStartAnalysis} disabled={!isStartEnabled || isLoading} className="bg-blue-600 text-white font-semibold py-3 px-12 rounded-lg hover:bg-blue-700 transition-all duration-300 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center min-w-[150px]">
                {isLoading ? (
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                    '开始诊断'
                )}
            </button>
        </div>
    </div>
);

// Component: AnalysisView
const AnalysisView = () => (
    <div className="text-center py-12">
        <div className="inline-block loader"></div>
        <h3 className="text-xl font-semibold mt-6 text-gray-800">AI 正在进行深度诊断...</h3>
        <p className="text-gray-500 mt-2">正在分析视频、调用AI模型、生成报告，请稍候。</p>
    </div>
);

// Sub-Component: OptimizedScriptsSection
const OptimizedScriptsSection = ({ title, scripts }) => {
    const [activeTab, setActiveTab] = useState(0);
    if (!scripts || scripts.length === 0) return null;
    const activeScript = scripts[activeTab];

    return (
        <div className="analysis-section">
            <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">{title || '优化后的脚本方案'}</h3>
            <div className="flex border-b mb-4 overflow-x-auto">
                {scripts.map((script, index) => (
                    <button
                        key={index}
                        className={`script-tab py-2 px-4 font-medium text-sm border-b-2 flex-shrink-0 ${activeTab === index ? 'active' : 'border-transparent'}`}
                        onClick={() => setActiveTab(index)}
                    >
                        {script.style || `方案 ${index + 1}`}
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

// Helper function to get color class based on score
const getScoreClass = (score) => {
    if (score >= 85) return 'text-green-600';
    if (score >= 70) return 'text-orange-500';
    return 'text-red-600';
};

const getPriorityClass = (priority = "") => {
    const p = priority.toLowerCase();
    if (p.includes('高')) return 'bg-red-500';
    if (p.includes('中')) return 'bg-orange-500';
    if (p.includes('低')) return 'bg-blue-500';
    return 'bg-gray-400';
}


// ==============================================================================
// Component: RadarChart (新增)
// 这个新组件使用 Chart.js 库来绘制雷达图。
// ==============================================================================
const RadarChart = ({ data }) => {
    const chartRef = React.useRef(null);
    const chartInstanceRef = React.useRef(null);

    React.useEffect(() => {
        if (!chartRef.current || !data) return;

        // 销毁旧的图表实例，防止内存泄漏和重叠渲染
        if (chartInstanceRef.current) {
            chartInstanceRef.current.destroy();
        }

        const ctx = chartRef.current.getContext('2d');
        chartInstanceRef.current = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: data.datasets[0]?.label || '您的视频',
                        data: data.datasets[0]?.data,
                        fill: true,
                        backgroundColor: 'rgba(59, 130, 246, 0.2)', // 蓝色区域
                        borderColor: 'rgb(59, 130, 246)',
                        pointBackgroundColor: 'rgb(59, 130, 246)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgb(59, 130, 246)'
                    },
                    {
                        label: data.datasets[1]?.label || '爆款模型',
                        data: data.datasets[1]?.data,
                        fill: true,
                        backgroundColor: 'rgba(34, 197, 94, 0.2)', // 绿色区域
                        borderColor: 'rgb(34, 197, 94)',
                        pointBackgroundColor: 'rgb(34, 197, 94)',
                        pointBorderColor: '#fff',
                        pointHoverBackgroundColor: '#fff',
                        pointHoverBorderColor: 'rgb(34, 197, 94)'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top', // 将图例放在顶部
                    },
                },
                scales: {
                    r: {
                        angleLines: { display: true },
                        suggestedMin: 0,
                        suggestedMax: 100,
                        pointLabels: {
                            font: { size: 13 }
                        },
                        ticks: {
                            stepSize: 20 // 刻度步长
                        }
                    }
                }
            }
        });

        // 组件卸载时销毁图表
        return () => {
            if (chartInstanceRef.current) {
                chartInstanceRef.current.destroy();
            }
        };
    }, [data]); // 当 data 变化时重新渲染图表

    return (
        <div className="bg-white p-4 rounded-lg border">
            <canvas ref={chartRef}></canvas>
        </div>
    );
};


// Component: ReportView
const ReportView = ({ onReset, reportData }) => {
    if (!reportData) return null;

    let { 
        overallScore, 
        conclusion, // This might be undefined
        radarData, // <-- 新增: 雷达图数据
        detailedAnalysis, 
        overallReview, 
        optimizedScripts,
        potentialLevel, // <-- 新增，用于备用
        potentialLevelText // <-- 新增，用于备用
    } = reportData;

    // 如果AI返回的数据没有 conclusion 对象，我们手动构建一个
    if (!conclusion && potentialLevel && potentialLevelText) {
        conclusion = {
            title: potentialLevel,
            description: potentialLevelText
        };
    }

    const scoreClass = getScoreClass(overallScore);

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-gray-800">诊断报告</h2>
                <button onClick={onReset} className="bg-gray-200 text-gray-700 font-semibold py-2 px-4 rounded-lg hover:bg-gray-300 transition-all duration-300 text-sm">诊断新视频</button>
            </div>
            
            <div id="report-content">
                <div className="bg-slate-50 p-6 rounded-xl border border-gray-200 text-center report-card mb-8">
                    <p className="text-lg text-gray-600">综合评分</p>
                    <p className={`text-6xl font-bold my-2 ${scoreClass}`}>{overallScore}<span className="text-2xl text-gray-500">/100</span></p>
                    <p className={`text-xl font-semibold ${scoreClass}`}>{conclusion?.title}</p>
                    <p className="text-sm text-gray-500 mt-1">{conclusion?.description}</p>
                </div>

                {/* --- 新增：数据雷达图模块 --- */}
                {radarData && radarData.labels && radarData.datasets && (
                    <div className="analysis-section mb-8">
                        <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">数据雷达图</h3>
                        <RadarChart data={radarData} />
                    </div>
                )}
                
                {detailedAnalysis && (
                    <div className="analysis-section mb-8">
                        <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">{detailedAnalysis.title || '详细视频分析'}</h3>
                        <dl className="space-y-4">
                            {detailedAnalysis.sections?.map((item, index) => (
                                <div key={index} className="bg-white p-4 rounded-lg border">
                                    <dt className="font-semibold text-gray-900">{item.dimension}</dt>
                                    <dd className="text-sm text-gray-600 mt-1">{item.content}</dd>
                                </div>
                            ))}
                        </dl>
                    </div>
                )}
                
                {overallReview && (
                    <div className="analysis-section mb-8">
                        <h3 className="text-xl font-bold text-gray-800 mb-4 pb-2 border-b-2">{overallReview.title || '综合评价与优化建议'}</h3>
                        <div className="grid md:grid-cols-2 gap-6">
                            <div className="bg-white p-4 rounded-lg border">
                                <h4 className="font-semibold text-green-600 mb-2">优点 (Pros)</h4>
                                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                                    {overallReview.pros?.map((pro, i) => <li key={i}>{pro}</li>)}
                                </ul>
                            </div>
                            <div className="bg-white p-4 rounded-lg border">
                                <h4 className="font-semibold text-red-600 mb-2">缺点 (Cons)</h4>
                                <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                                    {overallReview.cons?.map((con, i) => <li key={i}>{con}</li>)}
                                </ul>
                            </div>
                        </div>
                        <div className="bg-white p-4 rounded-lg border mt-6">
                             <h4 className="font-semibold text-blue-600 mb-2">优化方向</h4>
                             <ul className="space-y-3 mt-4">
                                {overallReview.optimizationDirections?.map((dir, i) => (
                                    <li key={i} className="flex items-start text-sm">
                                        <span className={`text-xs font-bold text-white rounded-full px-2 py-0.5 mr-3 ${getPriorityClass(dir.priority)}`}>
                                            {dir.priority}
                                        </span>
                                        <span className="text-gray-700">{dir.direction}</span>
                                    </li>
                                ))}
                             </ul>
                        </div>
                    </div>
                )}

                {optimizedScripts && optimizedScripts.scripts && 
                    <OptimizedScriptsSection 
                        title={optimizedScripts.title}
                        scripts={optimizedScripts.scripts} 
                    />
                }
            </div>
        </div>
    );
};


// Main App Component
function App() {
    const [view, setView] = useState('upload'); // 'upload', 'analysis', 'report'
    const [selectedFile, setSelectedFile] = useState(null);
    const [reportData, setReportData] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleFileSelect = (event) => {
        const file = event.target.files[0];
        if (file) {
            setSelectedFile(file);
            setError(null);
        }
    };

    const handleStartAnalysis = useCallback(async () => {
        if (!selectedFile) return;
        
        setView('analysis');
        setIsLoading(true);
        setError(null);
        
        try {
            // 1. 创建一个 FormData 对象
            // 这是在网页中上传文件的标准方式。
            const formData = new FormData();
            
            // 2. 将视频文件追加到 FormData 中
            // 第一个参数 "video" 是一个键名，必须与后端 FastAPI 接口中 `File(...)` 的参数名一致。
            // 第二个参数是文件对象，第三个是文件名。
            formData.append('video', selectedFile, selectedFile.name);

            // 3. 发送 FormData 到后端
            // 注意：当使用 FormData 时，浏览器会自动设置正确的 'Content-Type' (multipart/form-data)，
            // 所以我们不再需要在 headers 中手动设置它。
            const response = await fetch('http://10.186.60.38:8000/diagnose', {
                method: 'POST',
                body: formData, // 直接将 formData 作为 body
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({ detail: `服务器错误，状态码: ${response.status}` }));
                throw new Error(errData.detail || '分析时发生未知错误');
            }

            const data = await response.json();
            setReportData(data);
            setView('report');

        } catch (err) {
            console.error('Analysis failed:', err);
            setError(err.message);
            setView('upload');
        } finally {
            setIsLoading(false);
        }

    }, [selectedFile]);

    const handleReset = useCallback(() => {
        setView('upload');
        setSelectedFile(null);
        setReportData(null);
        setError(null);
        setIsLoading(false);
        const fileInput = document.getElementById('video-upload');
        if(fileInput) fileInput.value = '';
    }, []);

    return (
        <div className="container mx-auto p-4 md:p-8 max-w-4xl main-container">
            <Header />
            <main className="bg-white p-6 md:p-10 rounded-2xl shadow-lg border border-gray-200">
                {view === 'upload' && (
                     <>
                        <UploadView 
                            onFileSelect={handleFileSelect}
                            onStartAnalysis={handleStartAnalysis}
                            selectedFile={selectedFile}
                            isStartEnabled={!!selectedFile}
                            isLoading={isLoading}
                        />
                        {error && (
                            <div className="mt-4 text-center text-red-600 bg-red-100 p-3 rounded-lg">
                                <p><strong>分析失败:</strong> {error}</p>
                            </div>
                        )}
                    </>
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

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
