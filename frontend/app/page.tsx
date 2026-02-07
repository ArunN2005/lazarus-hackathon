'use client';

import { useState, useRef, useEffect } from 'react';
import { Terminal, Code, Play, Layers, AlertOctagon, CheckCircle, Cpu, ShieldAlert, GitPullRequest, Sun, Moon } from 'lucide-react';

type Artifact = {
  filename: string;
  content: string;
};

type ApiResponse = {
  logs: string;
  artifact: Artifact;
  preview: string;
};

export default function Home() {
  const [repoUrl, setRepoUrl] = useState('');
  const [instructions, setInstructions] = useState('');
  const [logs, setLogs] = useState<string[]>([]); // Changed to array for steps
  const [debugLogs, setDebugLogs] = useState<string>(''); // For raw debug output
  const [showDebug, setShowDebug] = useState(false); // Toggle
  const [preview, setPreview] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);

  // Tabs: 'terminal', 'code', 'preview'
  const [activeTab, setActiveTab] = useState<'terminal' | 'code' | 'preview'>('terminal');
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const [isDeploying, setIsDeploying] = useState(false);
  const [deployStatus, setDeployStatus] = useState<{ status: string, message: string, url?: string } | null>(null);

  // Theme State
  const [isDarkMode, setIsDarkMode] = useState(true);

  // Toggle Theme
  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.documentElement.classList.toggle('dark');
  };

  // Timer State
  const [timeLeft, setTimeLeft] = useState<number | null>(null);

  // Init Theme
  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  // Timer Countdown
  useEffect(() => {
    if (timeLeft === null || timeLeft <= 0) return;
    const interval = setInterval(() => {
      setTimeLeft((prev) => (prev !== null ? prev - 1 : null));
    }, 1000);
    return () => clearInterval(interval);
  }, [timeLeft]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const initializeProtocol = async () => {
    if (!repoUrl) return;

    setIsLoading(true);
    // Reset states
    setLogs(['[*] ESTABLISHING SECURE CONNECTION TO LAZARUS ENGINE...']);
    setDebugLogs('');
    setArtifacts([]);
    setSelectedFile(null);
    setPreview('');
    setDeployStatus(null);
    setActiveTab('terminal');

    try {
      const response = await fetch('http://localhost:8000/api/resurrect', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_url: repoUrl,
          vibe_instructions: instructions,
        }),
      });

      if (!response.ok) {
        throw new Error(`Connection Severed: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response stream");

      let buffer = '';
      setLogs([]); // Clear init log

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (!line) continue;
          try {
            const chunk = JSON.parse(line);
            if (chunk.type === 'log') {
              setLogs(prev => [...prev, chunk.content]);
              setDebugLogs(prev => prev + `[LOG] ${chunk.content}\n`);
            } else if (chunk.type === 'debug') {
              setDebugLogs(prev => prev + `${chunk.content}\n`);
            } else if (chunk.type === 'result') {
              const res = chunk.data;
              setArtifacts(res.artifacts || []);
              setPreview(res.preview || '');
              if (res.artifacts?.length) setSelectedFile(res.artifacts[0].filename);

              // Auto switch
              if (res.preview) setActiveTab('preview');
              else if (res.artifacts?.length) setActiveTab('code');

              // Start 30m Timer
              setTimeLeft(1800);

              setIsLoading(false);
            }
          } catch (e) {
            console.error("Parse error", e);
          }
        }
        buffer = lines[lines.length - 1];
      }

    } catch (error) {
      setLogs(prev => [...prev, `[ERROR] PROTOCOL FAILURE: ${error}`]);
      setDebugLogs(prev => prev + `[ERROR] ${error}\n`);
      setIsLoading(false);
    }
  };

  const deployCode = async () => {
    if (artifacts.length === 0 || !repoUrl) return;

    setIsDeploying(true);
    setDeployStatus(null);

    try {
      let lastUrl = "";
      for (const file of artifacts) {
        const response = await fetch('http://localhost:8000/api/commit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repo_url: repoUrl,
            filename: file.filename,
            content: file.content,
          }),
        });

        const data = await response.json();
        if (data.status !== 'success') {
          throw new Error(`Failed to commit: ${file.filename}`);
        }
        lastUrl = data.commit_url;
      }

      setDeployStatus({ status: 'success', message: 'MIGRATION BRANCH READY', url: lastUrl });

    } catch (error: any) {
      setDeployStatus({ status: 'error', message: `DEPLOY ERROR: ${error.message || error}` });
    } finally {
      setIsDeploying(false);
    }
  };

  const selectedContent = artifacts.find(a => a.filename === selectedFile)?.content || '';

  return (
    <main className={`min-h-screen font-mono p-8 transition-colors duration-500
        ${isDarkMode ? 'bg-[#050505] text-[#39ff14] selection:bg-[#39ff14] selection:text-black' : 'bg-gray-100 text-gray-900 selection:bg-blue-500 selection:text-white'}
    `}>

      {/* Header */}
      <div className={`max-w-7xl mx-auto mb-8 flex justify-between items-end border-b pb-4
          ${isDarkMode ? 'border-[#39ff14]/30' : 'border-gray-300'}
      `}>
        <div>
          <h1 className="text-4xl font-bold tracking-tighter animate-pulse flex items-center gap-3">
            <Cpu className="w-10 h-10" />
            LAZARUS_ENGINE
          </h1>
          <p className="text-sm opacity-70 mt-1">
            {isDarkMode ? 'AUTONOMOUS RESURRECTION PROTOCOL v9.0' : 'Enterprise Migration Suite v9.0'}
          </p>
        </div>

        <div className="flex items-center gap-4">
          {/* THEME TOGGLE */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-full transition-all hover:scale-110 
                    ${isDarkMode ? 'bg-[#39ff14]/20 hover:bg-[#39ff14] text-[#39ff14] hover:text-black' : 'bg-gray-200 hover:bg-gray-300 text-gray-700'}
                `}
          >
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
          <div className="flex gap-2 text-xs items-center">
            {timeLeft !== null && (
              <span className={`px-2 py-1 rounded border font-bold animate-pulse ${isDarkMode ? 'bg-red-500/20 text-red-400 border-red-500/50' : 'bg-red-100 text-red-600 border-red-300'
                }`}>
                SANDBOX DETONATION IN: {formatTime(timeLeft)}
              </span>
            )}
            <span className={`px-2 py-1 rounded border ${isDarkMode ? 'bg-[#39ff14]/10 border-[#39ff14]/50' : 'bg-green-100 text-green-800 border-green-300'}`}>STATUS: ONLINE</span>
            <span className={`px-2 py-1 rounded border ${isDarkMode ? 'bg-[#39ff14]/10 border-[#39ff14]/50' : 'bg-blue-100 text-blue-800 border-blue-300'}`}>MODE: {isDarkMode ? 'HAXOR' : 'CORP'}</span>
          </div>
        </div>
      </div>

      {/* Input Section */}
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="relative group">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className={`w-full rounded-xl px-5 py-4 focus:outline-none transition-all
                      ${isDarkMode
                  ? 'bg-[#0a0a0a] border border-[#39ff14]/30 focus:border-[#39ff14] focus:shadow-[0_0_20px_rgba(57,255,20,0.2)] placeholder-[#39ff14]/30'
                  : 'bg-white border border-gray-300 focus:border-blue-500 shadow-sm placeholder-gray-400'}
                  `}
              placeholder="ENTER TARGET REPO URL..."
            />
            <div className="absolute right-4 top-4 opacity-50"><Layers className="w-6 h-6" /></div>
          </div>
          <textarea
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            className={`w-full rounded-xl px-5 py-4 h-32 focus:outline-none transition-all resize-none
                  ${isDarkMode
                ? 'bg-[#0a0a0a] border border-[#39ff14]/30 focus:border-[#39ff14] focus:shadow-[0_0_20px_rgba(57,255,20,0.2)] placeholder-[#39ff14]/30'
                : 'bg-white border border-gray-300 focus:border-blue-500 shadow-sm placeholder-gray-400'}
              `}
            placeholder="DEFINE RESURRECTION PARAMETERS..."
          />
        </div>

        {/* Action Panel */}
        <div className="flex flex-col gap-4">
          <button
            onClick={initializeProtocol}
            disabled={isLoading}
            className={`flex-1 rounded-xl font-bold text-xl tracking-widest transition-all flex items-center justify-center gap-2
                ${isLoading
                ? (isDarkMode ? 'bg-[#39ff14]/20 cursor-wait animate-pulse' : 'bg-blue-100 text-blue-800 cursor-wait')
                : (isDarkMode ? 'bg-[#39ff14] text-black hover:shadow-[0_0_30px_#39ff14] hover:scale-[1.02]' : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg hover:scale-[1.02]')}
              `}
          >
            {isLoading ? 'INITIALIZING...' : <><Play className="fill-current" /> {isDarkMode ? 'INITIALIZE PROTOCOL' : 'START MIGRATION'}</>}
          </button>

          {/* Deploy Button */}
          <button
            onClick={deployCode}
            disabled={isDeploying || deployStatus?.status === 'fallback' || artifacts.length === 0}
            className={`h-16 rounded-xl font-bold border-2 flex items-center justify-center gap-2 transition-all
                  ${deployStatus?.status === 'success' ? (isDarkMode ? 'border-blue-500 text-blue-500 bg-blue-500/10' : 'border-green-500 text-green-600 bg-green-50') :
                deployStatus?.status === 'fallback' ? 'border-red-500 text-red-500 bg-red-500/10 cursor-not-allowed opacity-50' :
                  (isDarkMode ? 'border-[#39ff14] hover:bg-[#39ff14]/10' : 'border-blue-600 text-blue-600 hover:bg-blue-50')}
               `}
          >
            {deployStatus?.status === 'success' ? <><CheckCircle /> MIGRATION COMPLETE</> :
              deployStatus?.status === 'fallback' ? <><ShieldAlert /> SYSTEM UNSTABLE - DEPLOY DISABLED</> :
                <><GitPullRequest /> {isDarkMode ? 'CREATE MIGRATION BRANCH' : 'CREATE PULL REQUEST'}</>}
          </button>

          {deployStatus?.url && (
            <a href={deployStatus.url} target="_blank" className="text-center text-xs underline animate-bounce">
              &gt;&gt; ACCESS PR SECURE LINK &lt;&lt;
            </a>
          )}
        </div>
      </div>

      {/* Main Display Area */}
      <div className={`max-w-7xl mx-auto rounded-2xl border overflow-hidden shadow-2xl h-[600px] flex flex-col backdrop-blur-md
          ${isDarkMode ? 'bg-[#0a0a0a]/80 border-[#39ff14]/20' : 'bg-white/80 border-gray-300'}
      `}>

        {/* Tabs */}
        <div className={`flex border-b ${isDarkMode ? 'border-[#39ff14]/20' : 'border-gray-200'}`}>
          <button
            onClick={() => setActiveTab('terminal')}
            className={`flex-1 py-4 font-bold flex items-center justify-center gap-2 transition-colors 
                    ${activeTab === 'terminal'
                ? (isDarkMode ? 'bg-[#39ff14]/10 text-[#39ff14]' : 'bg-gray-100 text-blue-600 border-b-2 border-blue-600')
                : (isDarkMode ? 'text-[#39ff14]/40 hover:text-[#39ff14]' : 'text-gray-400 hover:text-gray-600')}
                `}
          >
            <Terminal className="w-4 h-4" /> {isDarkMode ? 'PROCESS STEPS' : 'Live Status'}
          </button>
          <button
            onClick={() => setActiveTab('code')}
            className={`flex-1 py-4 font-bold flex items-center justify-center gap-2 transition-colors 
                    ${activeTab === 'code'
                ? (isDarkMode ? 'bg-[#39ff14]/10 text-[#39ff14]' : 'bg-gray-100 text-blue-600 border-b-2 border-blue-600')
                : (isDarkMode ? 'text-[#39ff14]/40 hover:text-[#39ff14]' : 'text-gray-400 hover:text-gray-600')}
                `}
          >
            <Code className="w-4 h-4" /> {isDarkMode ? 'SOURCE_MATRIX' : 'Code Explorer'}
          </button>
          <button
            onClick={() => setActiveTab('preview')}
            className={`flex-1 py-4 font-bold flex items-center justify-center gap-2 transition-colors 
                    ${activeTab === 'preview'
                ? (isDarkMode ? 'bg-[#39ff14]/10 text-[#39ff14]' : 'bg-gray-100 text-blue-600 border-b-2 border-blue-600')
                : (isDarkMode ? 'text-[#39ff14]/40 hover:text-[#39ff14]' : 'text-gray-400 hover:text-gray-600')}
                `}
          >
            <AlertOctagon className="w-4 h-4" /> {isDarkMode ? 'VISUAL_INTERLINK' : 'Live Preview'}
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto relative">

          {/* TERMINAL / STEPS */}
          {activeTab === 'terminal' && (
            <div className={`p-6 space-y-4 h-full overflow-auto flex flex-col ${isDarkMode ? '' : 'text-gray-800'}`}>

              {/* Controls */}
              <div className="flex justify-between items-center mb-4">
                <h3 className={`text-sm font-bold opacity-50 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {showDebug ? 'NEURAL_DEBUG_STREAM' : 'EXECUTION_PROTOCOL_V2'}
                </h3>
                <button
                  onClick={() => setShowDebug(!showDebug)}
                  className={`text-xs px-2 py-1 rounded border transition-all
                        ${showDebug
                      ? (isDarkMode ? 'bg-[#39ff14] text-black border-[#39ff14]' : 'bg-gray-800 text-white border-gray-800')
                      : (isDarkMode ? 'text-[#39ff14]/50 border-[#39ff14]/30 hover:text-[#39ff14]' : 'text-gray-400 border-gray-300 hover:text-gray-600')
                    }
                    `}
                >
                  {showDebug ? 'HIDE_DEBUG_LOGS' : '> SHOW_DEV_LOGS'}
                </button>
              </div>

              {/* Initial State */}
              {logs.length === 0 && !isLoading && (
                <div className="flex flex-col items-center justify-center h-full opacity-30 text-center">
                  <Cpu className="w-16 h-16 mb-4 animate-pulse" />
                  <p>AWAITING NEURAL INPUT...</p>
                </div>
              )}

              {/* DEBUG VIEW */}
              {showDebug ? (
                <div className={`flex-1 font-mono text-xs whitespace-pre-wrap overflow-auto p-4 rounded
                        ${isDarkMode ? 'bg-black/50 text-[#39ff14]' : 'bg-gray-900 text-green-400'}
                   `}>
                  {debugLogs || "Waiting for stream..."}
                </div>
              ) : (
                /* STEP VIEW */
                <div className="space-y-4">
                  {logs.map((log, i) => {
                    if (!log) return null;
                    const isLast = i === logs.length - 1;
                    // Use simpler 'last message is active' logic unless not loading
                    const isActive = isLast && isLoading;

                    return (
                      <div key={i} className="flex items-center gap-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
                        {/* ICON */}
                        <div className="flex-shrink-0">
                          {isActive ? (
                            <div className={`w-6 h-6 border-2 border-t-transparent rounded-full animate-spin 
                                            ${isDarkMode ? 'border-[#39ff14]' : 'border-blue-600'}`}>
                            </div>
                          ) : (
                            <CheckCircle className={`w-6 h-6 ${isDarkMode ? 'text-[#39ff14]' : 'text-green-600'}`} />
                          )}
                        </div>

                        {/* TEXT */}
                        <div className={`text-lg tracking-wide ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                          {log}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* CODE EXPLORER */}
          {activeTab === 'code' && (
            <div className="flex h-full">
              <div className={`w-64 border-r overflow-y-auto p-4 ${isDarkMode ? 'border-[#39ff14]/20 bg-black/40' : 'border-gray-200 bg-gray-50'}`}>
                {artifacts.map((f, i) => (
                  <button
                    key={i}
                    onClick={() => setSelectedFile(f.filename)}
                    className={`w-full text-left truncate text-xs py-2 px-3 rounded mb-1 transition-all 
                                    ${selectedFile === f.filename
                        ? (isDarkMode ? 'bg-[#39ff14] text-black font-bold' : 'bg-blue-100 text-blue-700 font-bold')
                        : (isDarkMode ? 'hover:bg-[#39ff14]/10' : 'hover:bg-gray-200')}
                                `}
                  >
                    {f.filename}
                  </button>
                ))}
              </div>
              <div className={`flex-1 p-4 overflow-auto ${isDarkMode ? '' : 'bg-white'}`}>
                <pre className={`text-xs ${isDarkMode ? 'text-gray-300' : 'text-gray-800'}`}>{selectedContent}</pre>
              </div>
            </div>
          )}

          {/* PREVIEW */}
          {activeTab === 'preview' && (
            <div className="h-full w-full bg-white text-black">
              {preview ? (
                <iframe
                  srcDoc={preview}
                  className="w-full h-full border-none"
                  title="Preview"
                />
              ) : (
                <div className={`flex items-center justify-center h-full ${isDarkMode ? 'bg-[#050505] text-[#39ff14]/50' : 'bg-gray-100 text-gray-400'}`}>
                  NO VISUAL SIGNAL DETECTED
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
