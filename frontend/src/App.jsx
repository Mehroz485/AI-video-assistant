import { useState } from 'react';

const WAVE_HEIGHTS = [40, 65, 30, 80, 55, 20, 70, 45, 90, 35, 60, 25, 75, 50, 85, 40, 65, 30, 55, 20, 70, 45, 80, 35];
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
function formatContent(text) {
  if (!text) return null;
  return text
    .split('\n')
    .filter((line) => line.trim().length > 0)
    .map((line, i) => {
      const trimmed = line.trim();
      if (trimmed.startsWith('#')) {
        return (
          <h4 key={i} className="font-display text-sm font-semibold tracking-wide text-[#EDEFF2] mt-3 mb-1 first:mt-0">
            {trimmed.replace(/^#+\s*/, '')}
          </h4>
        );
      }
      const parts = trimmed.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
      return (
        <p key={i} className="text-[#C7CDD6] leading-relaxed mb-2 last:mb-0">
          {parts.map((part, j) =>
            part.startsWith('**') && part.endsWith('**') ? (
              <strong key={j} className="text-[#EDEFF2] font-semibold">{part.slice(2, -2)}</strong>
            ) : (
              <span key={j}>{part}</span>
            )
          )}
        </p>
      );
    });
}

function App() {
  const [source, setSource] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [videoData, setVideoData] = useState(null);
  const [processError, setProcessError] = useState(null);

  const [chatMessage, setChatMessage] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [isChatting, setIsChatting] = useState(false);

  const handleProcessVideo = async () => {
    if (!source) return;
    setIsProcessing(true);
    setProcessError(null);
    setVideoData(null);
    setChatHistory([]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source: source, language: "english" }),
      });

      if (!response.ok) throw new Error("Processing failed");

      const data = await response.json();
      setVideoData(data);
    } catch (error) {
      setProcessError("Signal lost — check that the backend is running on :8000.");
      console.error(error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || !videoData?.session_id) return;

    const userMsg = chatMessage;
    setChatHistory((prev) => [...prev, { role: "user", content: userMsg }]);
    setChatMessage("");
    setIsChatting(true);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: videoData.session_id,
          question: userMsg,
        }),
      });

      const data = await response.json();
      setChatHistory((prev) => [...prev, { role: "ai", content: data.answer }]);
    } catch (error) {
      setChatHistory((prev) => [...prev, { role: "ai", content: "Transmission failed. No response received." }]);
    } finally {
      setIsChatting(false);
    }
  };

  const isLive = isProcessing || isChatting;

  return (
    <div className="min-h-screen bg-[#090D12] text-[#EDEFF2] font-sans">
      <div className="max-w-6xl mx-auto px-6 py-10 space-y-10">

        {/* Top bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-[#FF5C38] tally-active' : 'bg-[#2BC4B0]'}`} />
            <span className="font-mono-signal text-xs tracking-[0.2em] text-[#8A93A3] uppercase">
              {isLive ? 'Recording' : 'Standby'}
            </span>
          </div>
          {videoData?.session_id && (
            <span className="font-mono-signal text-xs tracking-wide text-[#8A93A3]">
              SESSION #{String(videoData.session_id).slice(0, 8)}
            </span>
          )}
        </div>

        {/* Hero / input */}
        <header className="space-y-6">
          <h1 className="font-display text-4xl md:text-5xl font-semibold tracking-tight">
            Feed it a video.
            <br />
            <span className="text-[#8A93A3]">Talk to what's inside.</span>
          </h1>

          <div className="bg-[#12171F] border border-[#29323F] rounded-2xl p-5 space-y-4">
            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="youtube.com/watch?v=... or /path/to/file.mp4"
                className="flex-1 px-4 py-3 bg-[#090D12] border border-[#29323F] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#2BC4B0] text-[#EDEFF2] placeholder:text-[#5B6472] font-mono-signal text-sm"
                value={source}
                onChange={(e) => setSource(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleProcessVideo()}
              />
              <button
                onClick={handleProcessVideo}
                disabled={isProcessing || !source}
                className="px-7 py-3 bg-[#FF5C38] text-[#090D12] font-display font-semibold rounded-xl hover:bg-[#ff7454] disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
              >
                {isProcessing ? 'Analyzing…' : '▶ Analyze'}
              </button>
            </div>

            <div className="flex items-end gap-[3px] h-8 px-1">
              {WAVE_HEIGHTS.map((h, i) => (
                <div
                  key={i}
                  className={`w-[3px] rounded-full ${isProcessing ? 'bg-[#FF5C38] wave-bar' : 'bg-[#29323F]'}`}
                  style={{ height: `${h}%`, animationDelay: `${i * 0.05}s` }}
                />
              ))}
            </div>

            {processError && (
              <p className="font-mono-signal text-xs text-[#FF5C38]">{processError}</p>
            )}
          </div>
        </header>

        {/* Results */}
        {videoData && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">

            {/* Transcript panel */}
            <div className="bg-[#12171F] border border-[#29323F] rounded-2xl overflow-hidden">
              <div className="px-5 py-4 border-b border-[#29323F] flex items-center justify-between">
                <span className="font-mono-signal text-xs tracking-[0.2em] text-[#8A93A3] uppercase">Reel</span>
              </div>
              <div className="p-5 space-y-5">
                <h2 className="font-display text-xl font-semibold">{videoData.title}</h2>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono-signal text-xs text-[#2BC4B0]">00:01</span>
                    <span className="font-mono-signal text-xs tracking-wide text-[#8A93A3] uppercase">Summary</span>
                  </div>
                  <div className="bg-[#0D1218] rounded-xl border border-[#29323F] p-4">
                    {formatContent(videoData.summary)}
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono-signal text-xs text-[#2BC4B0]">00:02</span>
                    <span className="font-mono-signal text-xs tracking-wide text-[#8A93A3] uppercase">Key Decisions</span>
                  </div>
                  <div className="bg-[#0D1218] rounded-xl border border-[#29323F] p-4">
                    {videoData.key_decisions ? (
                      formatContent(videoData.key_decisions)
                    ) : (
                      <p className="text-[#5B6472] font-mono-signal text-sm">None detected.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Chat panel */}
            <div className="bg-[#12171F] border border-[#29323F] rounded-2xl flex flex-col h-[600px] overflow-hidden">
              <div className="px-5 py-4 border-b border-[#29323F] flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full ${isChatting ? 'bg-[#FF5C38] tally-active' : 'bg-[#2BC4B0]'}`} />
                <span className="font-mono-signal text-xs tracking-[0.2em] text-[#8A93A3] uppercase">Live Channel</span>
              </div>

              <div className="flex-1 p-4 overflow-y-auto space-y-3">
                {chatHistory.length === 0 ? (
                  <div className="h-full flex items-center justify-center">
                    <p className="font-mono-signal text-sm text-[#5B6472] text-center">
                      Channel open.<br />Ask about the video.
                    </p>
                  </div>
                ) : (
                  chatHistory.map((msg, index) => {
                    const turn = Math.floor(index / 2) + 1;
                    const label = `${msg.role === 'user' ? 'TX' : 'RX'} ${String(turn).padStart(2, '0')}`;
                    return (
                      <div key={index} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                        <span className="font-mono-signal text-[10px] text-[#5B6472] mb-1 px-1">{label}</span>
                        <div
                          className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                            msg.role === 'user'
                              ? 'bg-[#FF5C38] text-[#090D12] font-medium rounded-tr-sm'
                              : 'bg-[#0D1218] border border-[#29323F] text-[#EDEFF2] rounded-tl-sm'
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    );
                  })
                )}
                {isChatting && (
                  <div className="flex items-center gap-2 px-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2BC4B0] tally-active" />
                    <span className="font-mono-signal text-xs text-[#5B6472]">receiving…</span>
                  </div>
                )}
              </div>

              <form onSubmit={handleSendMessage} className="p-4 border-t border-[#29323F] flex gap-2">
                <input
                  type="text"
                  placeholder="Transmit a question..."
                  className="flex-1 px-4 py-2 bg-[#0D1218] border border-[#29323F] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#2BC4B0] text-[#EDEFF2] placeholder:text-[#5B6472] text-sm"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                />
                <button
                  type="submit"
                  disabled={isChatting || !chatMessage.trim()}
                  className="px-5 py-2 bg-[#EDEFF2] text-[#090D12] font-semibold rounded-lg hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  Send ▸
                </button>
              </form>
            </div>

          </div>
        )}
      </div>
    </div>
  );
}

export default App;