import React, { useState, useEffect, useRef } from 'react';

// API Configuration
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8000`;

export default function App() {
  // Application State
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [filesList, setFilesList] = useState([]);
  const [currentFolder, setCurrentFolder] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const [waveform, setWaveform] = useState([]);
  const [nextHindiFilename, setNextHindiFilename] = useState('Scanning...');
  
  // Slicing/Waste Intervals State
  const [intervalsText, setIntervalsText] = useState('');
  const [validationFeedback, setValidationFeedback] = useState([]);
  const [validatedIntervals, setValidatedIntervals] = useState([]);

  // Playback State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Background Task Polling State
  const [taskStatus, setTaskStatus] = useState({
    status: 'idle',
    progress: 0,
    message: 'Ready',
    logs: [],
    result: {}
  });
  const [isPolling, setIsPolling] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  // Refs
  const audioRef = useRef(null);
  const canvasRef = useRef(null);
  const logsEndRef = useRef(null);

  // Fetch initial file lists & next available filename
  useEffect(() => {
    fetchFiles();
    fetchNextFilename();
  }, []);

  // Fetch files inside outputs folder
  const fetchFiles = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/files`);
      const data = await res.json();
      setFilesList(data.files || []);
      setCurrentFolder(data.folder || '');
    } catch (e) {
      console.error('Error fetching files:', e);
    }
  };

  // Fetch next incremented Hindi filename
  const fetchNextFilename = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/next-filename`);
      const data = await res.json();
      setNextHindiFilename(data.next_filename || 'Hindi1.wav');
    } catch (e) {
      setNextHindiFilename('Error scanning folder');
      console.error('Error fetching next filename:', e);
    }
  };

  // Poll status endpoint while a background task is running
  useEffect(() => {
    let timer;
    if (isPolling) {
      timer = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/status`);
          const data = await res.json();
          setTaskStatus(data);
          
          if (data.status === 'idle' || data.status === 'success' || data.status === 'error') {
            setIsPolling(false);
            fetchFiles();
            fetchNextFilename();
            
            if (data.status === 'success') {
              setShowSuccessModal(true);
            }
            
            // If download just completed, automatically load the downloaded file
            if (data.status === 'idle' && data.result?.filepath) {
              loadFile(data.result.filepath);
            }
          }
        } catch (e) {
          console.error('Status polling error:', e);
          setIsPolling(false);
        }
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isPolling]);

  // Scroll logs container to bottom on update
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [taskStatus.logs]);

  // Redraw Waveform Canvas when state changes
  useEffect(() => {
    drawWaveform();
  }, [waveform, currentTime, duration]);

  // Format seconds to H:MM:SS or MM:SS
  const formatTime = (secs) => {
    if (isNaN(secs)) return '00:00';
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = Math.floor(secs % 60);
    if (h > 0) {
      return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // Trigger youtube download task
  const handleDownload = async () => {
    if (!youtubeUrl.trim() || isPolling) return;
    try {
      const res = await fetch(`${API_BASE}/api/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: youtubeUrl })
      });
      if (res.ok) {
        setIsPolling(true);
        setYoutubeUrl('');
      } else {
        const err = await res.json();
        alert(`Error starting download: ${err.detail}`);
      }
    } catch (e) {
      alert(`Network error starting download: ${e.message}`);
    }
  };

  // Load selected file
  const loadFile = async (filepath) => {
    // Stop current audio
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
    
    setSelectedFile(filepath);
    setMetadata(null);
    setWaveform([]);
    setCurrentTime(0);
    setDuration(0);
    
    try {
      const res = await fetch(`${API_BASE}/api/load`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filepath })
      });
      if (res.ok) {
        const data = await res.json();
        setMetadata(data.metadata);
        setWaveform(data.waveform);
        setDuration(data.metadata.duration);
        
        // Auto-validate current intervals using new duration
        validateIntervals(intervalsText, data.metadata.duration);
      } else {
        const err = await res.json();
        alert(`Failed to load file: ${err.detail}`);
      }
    } catch (e) {
      alert(`Network error loading file: ${e.message}`);
    }
  };

  // HTML5 audio event handlers
  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const togglePlay = () => {
    if (!selectedFile || !audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(e => console.error("Playback error:", e));
      setIsPlaying(true);
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      setCurrentTime(0);
    }
  };

  // Canvas drawing routine
  const drawWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    
    // Clear canvas
    ctx.clearRect(0, 0, W, H);
    
    // Draw background grid lines (subtle)
    ctx.strokeStyle = '#1E1E24';
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 4]);
    for (let i = 1; i < 10; i++) {
      const x = (i / 10) * W;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, H);
      ctx.stroke();
    }
    ctx.setLineDash([]); // Reset dash

    // Draw center dividing line
    ctx.strokeStyle = '#25252D';
    ctx.beginPath();
    ctx.moveTo(0, H / 2);
    ctx.lineTo(W, H / 2);
    ctx.stroke();

    if (waveform.length === 0) {
      // Draw placeholder text
      ctx.fillStyle = '#555560';
      ctx.font = '12px Outfit';
      ctx.textAlign = 'center';
      ctx.fillText(selectedFile ? 'Loading Waveform...' : 'No Audio File Loaded', W / 2, H / 2 + 4);
      return;
    }

    const playPercent = duration > 0 ? currentTime / duration : 0;
    const cursorX = playPercent * W;

    const barWidth = Math.max(1, Math.floor(W / waveform.length));
    const centerY = H / 2;
    const maxBarH = (H - 20) / 2;

    for (let i = 0; i < waveform.length; i++) {
      const x = (i / waveform.length) * W;
      const amp = waveform[i];
      const h = Math.max(2, amp * maxBarH);

      // Determine active color if left of cursor
      if (x <= cursorX) {
        ctx.fillStyle = '#00E5FF'; // Cyber cyan
      } else {
        ctx.fillStyle = '#3E3E4C'; // Dark slate
      }

      ctx.fillRect(x, centerY - h, barWidth, h * 2);
    }

    // Draw red playback cursor line
    ctx.fillStyle = '#FF5555';
    ctx.strokeStyle = '#FF5555';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cursorX, 0);
    ctx.lineTo(cursorX, H);
    ctx.stroke();

    // Draw cursor tip (triangle at top)
    ctx.beginPath();
    ctx.moveTo(cursorX - 5, 0);
    ctx.lineTo(cursorX + 5, 0);
    ctx.lineTo(cursorX, 8);
    ctx.fill();
  };

  // Seek audio via canvas interaction
  const handleCanvasInteraction = (e) => {
    if (!duration || !canvasRef.current || !audioRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(x / rect.width, 1));
    const seekTime = pct * duration;
    
    audioRef.current.currentTime = seekTime;
    setCurrentTime(seekTime);
  };

  // Parse time input to float seconds
  const parseTimeToSeconds = (str) => {
    const s = str.trim();
    if (!s) return null;
    const parts = s.split(':');
    if (parts.length === 3) {
      return parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2]);
    } else if (parts.length === 2) {
      return parseFloat(parts[0]) * 60 + parseFloat(parts[1]);
    } else if (parts.length === 1) {
      return parseFloat(parts[0]);
    }
    throw new Error('Invalid format');
  };

  // Intervals text parsing and validation
  const validateIntervals = (text, customDuration = duration) => {
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length === 0) {
      setValidationFeedback([]);
      setValidatedIntervals([]);
      return;
    }

    const feedback = [];
    const valids = [];

    lines.forEach((line, idx) => {
      // Split by '->', ',' or '-'
      let parts = null;
      for (const delim of ['->', ',', '-']) {
        const split = line.split(delim);
        if (split.length === 2) {
          parts = split.map(p => p.trim());
          break;
        }
      }

      if (!parts) {
        // Try space split
        const split = line.split(/\s+/);
        if (split.length === 2) parts = split;
      }

      if (!parts || parts.length !== 2) {
        feedback.push({
          lineNum: idx + 1,
          valid: false,
          text: `Line ${idx + 1}: Invalid format. Use 'start -> end' or 'start,end'`
        });
        return;
      }

      try {
        const start = parseTimeToSeconds(parts[0]);
        const end = parseTimeToSeconds(parts[1]);

        if (start === null || end === null || isNaN(start) || isNaN(end)) {
          throw new Error('Parsing error');
        }

        if (start < 0 || end < 0) {
          feedback.push({
            lineNum: idx + 1,
            valid: false,
            text: `Line ${idx + 1}: Timestamps cannot be negative`
          });
        } else if (start >= end) {
          feedback.push({
            lineNum: idx + 1,
            valid: false,
            text: `Line ${idx + 1}: Start time must be less than end time`
          });
        } else if (customDuration > 0 && (start > customDuration || end > customDuration)) {
          feedback.push({
            lineNum: idx + 1,
            valid: false,
            text: `Line ${idx + 1}: Exceeds audio duration (${formatTime(customDuration)})`
          });
        } else {
          feedback.push({
            lineNum: idx + 1,
            valid: true,
            text: `Line ${idx + 1}: ${formatTime(start)} ➜ ${formatTime(end)} (Remove ${formatTime(end - start)})`
          });
          valids.push([start, end]);
        }
      } catch (e) {
        feedback.push({
          lineNum: idx + 1,
          valid: false,
          text: `Line ${idx + 1}: Failed to parse timestamps`
        });
      }
    });

    setValidationFeedback(feedback);
    setValidatedIntervals(valids);
  };

  // Debounced input validation
  const handleIntervalsChange = (e) => {
    const txt = e.target.value;
    setIntervalsText(txt);
    validateIntervals(txt);
  };

  // Load JSON interval template
  const handleLoadJson = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target.result);
        if (!Array.isArray(data)) throw new Error("Must be JSON array");
        const lines = data.map(item => `${item.start} -> ${item.end}`).join('\n');
        setIntervalsText(lines);
        validateIntervals(lines);
      } catch (err) {
        alert("Failed to parse JSON file: " + err.message);
      }
    };
    reader.readAsText(file);
    e.target.value = null; // Reset file input
  };

  // Save current intervals to JSON file
  const handleSaveJson = () => {
    const rawLines = intervalsText.split('\n').map(l => l.trim()).filter(l => l.length > 0);
    const jsonArr = [];
    
    rawLines.forEach(line => {
      let parts = null;
      for (const delim of ['->', ',', '-']) {
        const split = line.split(delim);
        if (split.length === 2) {
          parts = split.map(p => p.trim());
          break;
        }
      }
      if (!parts) {
        const split = line.split(/\s+/);
        if (split.length === 2) parts = split;
      }
      if (parts && parts.length === 2) {
        try {
          const start = parseTimeToSeconds(parts[0]);
          const end = parseTimeToSeconds(parts[1]);
          if (start !== null && end !== null && !isNaN(start) && !isNaN(end) && start < end) {
            jsonArr.push({
              start: formatTime(start),
              end: formatTime(end)
            });
          }
        } catch(e) {}
      }
    });

    const blob = new Blob([JSON.stringify(jsonArr, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${metadata?.filename ? metadata.filename.replace('.wav', '') : 'intervals'}_waste.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Run the full waste removal pipeline
  const handleRemoveWaste = async () => {
    if (!selectedFile || isPolling) return;
    
    // Check if validation has errors
    const hasErrors = validationFeedback.some(item => !item.valid);
    if (hasErrors) {
      alert("Please resolve validation errors first!");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/remove-waste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filepath: selectedFile,
          waste_intervals: validatedIntervals
        })
      });
      if (res.ok) {
        setIsPolling(true);
      } else {
        const err = await res.json();
        alert(`Error starting pipeline: ${err.detail}`);
      }
    } catch (e) {
      alert(`Network error starting pipeline: ${e.message}`);
    }
  };

  return (
    <div style={styles.appContainer}>
      {/* 1. Header Branding */}
      <header style={styles.header}>
        <div style={styles.headerBranding}>
          <span style={styles.logoText}>TECHPHOTONS SOLUTION PVT. LTD.</span>
        </div>
        <div style={styles.headerSubtitle}>
          YouTube Audio Dataset Downloader & Processor v2.0
        </div>
      </header>

      {/* 2. Main Dashboard Grid */}
      <main style={styles.mainGrid}>
        
        {/* LEFT COLUMN: Downloader & File Explorer */}
        <section style={styles.leftCol}>
          
          {/* YouTube Audio Download Panel */}
          <div style={styles.panelCard}>
            <h2 style={styles.panelTitle}>YOUTUBE AUDIO DOWNLOAD</h2>
            <div style={styles.formRow}>
              <input 
                type="text"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="Enter YouTube Video URL..."
                style={styles.urlInput}
                disabled={isPolling}
              />
              <button 
                onClick={handleDownload}
                style={{
                  ...styles.primaryBtn,
                  opacity: (isPolling || !youtubeUrl.trim()) ? 0.6 : 1,
                  cursor: (isPolling || !youtubeUrl.trim()) ? 'not-allowed' : 'pointer'
                }}
                disabled={isPolling || !youtubeUrl.trim()}
              >
                Download
              </button>
            </div>
            
            {/* Download/Processing progress indicators */}
            <div style={styles.progressContainer}>
              <div style={styles.progressBarBg}>
                <div 
                  style={{
                    ...styles.progressBarFill, 
                    width: `${taskStatus.progress * 100}%`,
                    backgroundColor: taskStatus.status === 'error' ? 'var(--accent-red)' : 'var(--accent-cyan)'
                  }} 
                />
              </div>
              <div style={styles.progressLabelRow}>
                <span style={styles.progressLabel}>{taskStatus.message}</span>
                {taskStatus.progress > 0 && (
                  <span style={styles.progressPct}>{Math.round(taskStatus.progress * 100)}%</span>
                )}
              </div>
            </div>
          </div>

          {/* Local files explorer */}
          <div style={{...styles.panelCard, flex: 1, display: 'flex', flexDirection: 'column'}}>
            <h2 style={styles.panelTitle}>GENERATED & WAV FILES</h2>
            <div style={styles.explorerList}>
              {filesList.length === 0 ? (
                <div style={styles.emptyExplorer}>No WAV files found in outputs.</div>
              ) : (
                filesList.map((filename, i) => (
                  <div 
                    key={i}
                    onClick={() => loadFile(filename)}
                    style={{
                      ...styles.explorerRow,
                      backgroundColor: selectedFile && selectedFile.includes(filename) ? '#1E1E2A' : 'transparent',
                      color: selectedFile && selectedFile.includes(filename) ? 'var(--accent-cyan)' : 'var(--text-primary)',
                    }}
                  >
                    🎵 {filename}
                  </div>
                ))
              )}
            </div>
          </div>
        </section>

        {/* RIGHT COLUMN: Audio visualizer & Waste Intervals Slicer */}
        <section style={styles.rightCol}>
          
          {/* HTML5 stream audio player (hidden) */}
          {selectedFile && (
            <audio 
              ref={audioRef}
              src={`${API_BASE}/api/audio/stream?filepath=${encodeURIComponent(selectedFile)}`}
              onTimeUpdate={handleTimeUpdate}
              onEnded={handleAudioEnded}
              preload="auto"
            />
          )}

          {/* Player controls, visualization & Metadata */}
          <div style={styles.panelCard}>
            {/* Metadata headers */}
            <div style={styles.metaFrame}>
              <div style={styles.metaRowColFull}>
                <span style={styles.metaTitle}>FILE NAME</span>
                <span style={styles.metaValue}>{metadata ? metadata.filename : '-'}</span>
              </div>
              <div style={styles.metaRowCol}>
                <span style={styles.metaTitle}>DURATION</span>
                <span style={styles.metaValue}>{metadata ? formatTime(metadata.duration) : '00:00'}</span>
              </div>
              <div style={styles.metaRowCol}>
                <span style={styles.metaTitle}>SAMPLE RATE</span>
                <span style={styles.metaValue}>{metadata ? metadata.sample_rate : '-'}</span>
              </div>
              <div style={styles.metaRowCol}>
                <span style={styles.metaTitle}>CHANNELS</span>
                <span style={styles.metaValue}>{metadata ? metadata.channels : '-'}</span>
              </div>
              <div style={styles.metaRowCol}>
                <span style={styles.metaTitle}>FILE SIZE</span>
                <span style={styles.metaValue}>{metadata ? metadata.file_size : '-'}</span>
              </div>
            </div>

            {/* Waveform Visualizer canvas */}
            <h3 style={styles.canvasTitle}>WAVEFORM VISUALIZER & TRACKER</h3>
            <canvas 
              ref={canvasRef}
              width={650}
              height={120}
              onClick={handleCanvasInteraction}
              style={styles.waveformCanvas}
            />

            {/* Time stamps & Audio Buttons */}
            <div style={styles.playerButtonsRow}>
              <div style={styles.timeTracker}>
                <span style={styles.currentTimeText}>{formatTime(currentTime)}</span>
                <span style={styles.totalTimeText}> / {formatTime(duration)}</span>
              </div>
              
              <div style={styles.controlsBtnGroup}>
                <button 
                  onClick={togglePlay}
                  style={{...styles.playerBtn, backgroundColor: isPlaying ? 'var(--accent-blue)' : 'var(--border-color)'}}
                  disabled={!selectedFile}
                >
                  {isPlaying ? '⏸ Pause' : '▶ Play'}
                </button>
                <button 
                  onClick={handleStop}
                  style={styles.playerBtn}
                  disabled={!selectedFile}
                >
                  ⏹ Stop
                </button>
              </div>
            </div>
          </div>

          {/* Slicing input, validation & next filename */}
          <div style={{...styles.panelCard, flex: 1, display: 'flex', flexDirection: 'column'}}>
            <div style={styles.slicerTitleRow}>
              <h2 style={styles.panelTitle}>WASTE INTERVALS TO REMOVE</h2>
              <div style={styles.filenameDisplayBox}>
                <span style={styles.filenameDisplayLabel}>NEXT HINDI FILENAME</span>
                <span style={styles.filenameDisplayValue}>{nextHindiFilename}</span>
              </div>
            </div>

            <div style={styles.slicerLayout}>
              {/* Left slicer column: Text Editor */}
              <div style={styles.slicerLeft}>
                <textarea 
                  value={intervalsText}
                  onChange={handleIntervalsChange}
                  placeholder="Enter timestamps of waste audio to remove, one per line:&#10;00:00:00,00:01:30&#10;00:05:10,00:06:20"
                  style={styles.intervalsTextbox}
                  disabled={isPolling}
                />
                
                <div style={styles.jsonLoadSaveRow}>
                  <label style={styles.loadJsonLabel}>
                    📂 Load JSON
                    <input 
                      type="file" 
                      accept=".json"
                      onChange={handleLoadJson} 
                      style={{display: 'none'}} 
                      disabled={isPolling}
                    />
                  </label>
                  
                  <button 
                    onClick={handleSaveJson}
                    style={styles.saveJsonBtn}
                    disabled={isPolling || !intervalsText.trim()}
                  >
                    💾 Save JSON
                  </button>
                </div>
              </div>

              {/* Right slicer column: Feedback & Remove button */}
              <div style={styles.slicerRight}>
                <div style={styles.validationFeedbackList}>
                  {validationFeedback.length === 0 ? (
                    <div style={styles.emptyValidation}>No waste intervals entered yet.</div>
                  ) : (
                    validationFeedback.map((item, i) => (
                      <div 
                        key={i} 
                        style={{
                          ...styles.validationRow, 
                          color: item.valid ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}
                      >
                        {item.valid ? '✔' : '❌'} {item.text}
                      </div>
                    ))
                  )}
                </div>

                <button 
                  onClick={handleRemoveWaste}
                  style={{
                    ...styles.dangerActionBtn,
                    opacity: (isPolling || !selectedFile) ? 0.6 : 1,
                    cursor: (isPolling || !selectedFile) ? 'not-allowed' : 'pointer'
                  }}
                  disabled={isPolling || !selectedFile}
                >
                  🚫 Remove Waste
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* 3. Scrolling status logs console panel */}
      <footer style={styles.logsConsolePanel}>
        <h3 style={styles.consoleTitle}>STATUS LOGS</h3>
        <div style={styles.logsConsoleOutput}>
          {taskStatus.logs.map((log, idx) => {
            let color = 'var(--text-secondary)';
            if (log.includes('[SUCCESS]')) color = 'var(--accent-green)';
            if (log.includes('[WARNING]')) color = 'var(--accent-orange)';
            if (log.includes('[ERROR]')) color = 'var(--accent-red)';
            
            return (
              <div key={idx} style={{...styles.logLine, color}}>
                {log}
              </div>
            );
          })}
          <div ref={logsEndRef} />
        </div>
      </footer>

      {/* Pipeline Success Modal Dialog */}
      {showSuccessModal && (
        <div style={styles.modalOverlay}>
          <div style={styles.modalCard}>
            <div style={styles.modalHeader}>
              <span style={styles.modalHeaderIcon}>✔️</span>
              <h3 style={styles.modalHeaderTitle}>Pipeline Process Complete</h3>
            </div>
            
            <div style={styles.modalBody}>
              <div style={styles.modalFieldRow}>
                <span style={styles.modalFieldLabel}>Cleaned File:</span>
                <span style={styles.modalFieldValue}>{taskStatus.result?.cleaned_file}</span>
              </div>
              <div style={styles.modalFieldRow}>
                <span style={styles.modalFieldLabel}>Split Files Created:</span>
                <span style={styles.modalFieldValue}>{taskStatus.result?.split_files_created}</span>
              </div>
              <div style={styles.modalFieldRow}>
                <span style={styles.modalFieldLabel}>Output Folder:</span>
                <span style={styles.modalFieldValue}>{taskStatus.result?.split_folder}</span>
              </div>
            </div>

            <div style={styles.modalFooter}>
              <button 
                onClick={() => {
                  setShowSuccessModal(false);
                  fetchFiles();
                }}
                style={styles.modalCloseBtn}
              >
                Close & Refresh
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Inline CSS Styles object for maximum responsiveness and custom dark theme
const styles = {
  appContainer: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    width: '100vw',
    backgroundColor: 'var(--bg-main)',
    overflow: 'hidden'
  },
  header: {
    height: '55px',
    backgroundColor: 'var(--bg-darker)',
    borderBottom: '1px solid var(--border-color)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0 20px',
    flexShrink: 0
  },
  headerBranding: {
    display: 'flex',
    alignItems: 'center'
  },
  logoText: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: 'var(--accent-cyan)',
    letterSpacing: '1px'
  },
  headerSubtitle: {
    fontSize: '11px',
    color: 'var(--text-secondary)'
  },
  mainGrid: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '1fr 1.6fr',
    gap: '12px',
    padding: '12px',
    overflow: 'hidden'
  },
  leftCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    overflow: 'hidden'
  },
  rightCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    overflow: 'hidden'
  },
  panelCard: {
    backgroundColor: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    borderRadius: '6px',
    padding: '15px',
    display: 'flex',
    flexDirection: 'column'
  },
  panelTitle: {
    fontSize: '12px',
    fontWeight: 'bold',
    color: 'var(--text-primary)',
    marginBottom: '10px',
    letterSpacing: '0.5px'
  },
  formRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '12px'
  },
  urlInput: {
    flex: 1,
    height: '35px',
    backgroundColor: 'var(--bg-darker)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    padding: '0 10px',
    fontSize: '13px',
    outline: 'none'
  },
  primaryBtn: {
    height: '35px',
    padding: '0 15px',
    backgroundColor: 'var(--accent-blue)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontWeight: 'bold',
    fontSize: '12px',
    transition: 'var(--transition-fast)'
  },
  progressContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px'
  },
  progressBarBg: {
    height: '6px',
    backgroundColor: 'var(--bg-darker)',
    borderRadius: '3px',
    overflow: 'hidden'
  },
  progressBarFill: {
    height: '100%',
    width: '0%',
    transition: 'width 0.2s ease'
  },
  progressLabelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '10px'
  },
  progressLabel: {
    color: 'var(--text-secondary)'
  },
  progressPct: {
    color: 'var(--accent-cyan)',
    fontWeight: 'bold'
  },
  explorerList: {
    flex: 1,
    backgroundColor: 'var(--bg-darker)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: '6px',
    overflowY: 'auto'
  },
  emptyExplorer: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    padding: '30px 10px',
    fontSize: '12px',
    fontStyle: 'italic'
  },
  explorerRow: {
    height: '32px',
    display: 'flex',
    alignItems: 'center',
    padding: '0 10px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '12px',
    marginBottom: '4px',
    transition: 'var(--transition-fast)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  metaFrame: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '10px',
    backgroundColor: 'var(--bg-darker)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: '12px',
    marginBottom: '15px'
  },
  metaRowColFull: {
    gridColumn: 'span 4',
    display: 'flex',
    flexDirection: 'column'
  },
  metaRowCol: {
    display: 'flex',
    flexDirection: 'column'
  },
  metaTitle: {
    fontSize: '9px',
    fontWeight: 'bold',
    color: 'var(--text-secondary)'
  },
  metaValue: {
    fontSize: '12px',
    fontWeight: 'bold',
    color: 'var(--text-primary)',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis'
  },
  canvasTitle: {
    fontSize: '10px',
    fontWeight: 'bold',
    color: 'var(--text-secondary)',
    marginBottom: '5px'
  },
  waveformCanvas: {
    backgroundColor: '#121216',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    width: '100%',
    cursor: 'pointer',
    marginBottom: '10px'
  },
  playerButtonsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  },
  timeTracker: {
    fontFamily: 'var(--font-code)',
    fontSize: '12px'
  },
  currentTimeText: {
    color: 'var(--accent-cyan)',
    fontWeight: 'bold'
  },
  totalTimeText: {
    color: 'var(--text-secondary)'
  },
  controlsBtnGroup: {
    display: 'flex',
    gap: '10px'
  },
  playerBtn: {
    height: '32px',
    padding: '0 15px',
    backgroundColor: 'var(--border-color)',
    color: 'var(--text-primary)',
    border: 'none',
    borderRadius: '4px',
    fontWeight: 'bold',
    fontSize: '11px',
    cursor: 'pointer',
    transition: 'var(--transition-fast)'
  },
  slicerTitleRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '10px'
  },
  filenameDisplayBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end'
  },
  filenameDisplayLabel: {
    fontSize: '9px',
    color: 'var(--text-secondary)',
    fontWeight: 'bold'
  },
  filenameDisplayValue: {
    fontSize: '12px',
    color: 'var(--accent-cyan)',
    fontWeight: 'bold'
  },
  slicerLayout: {
    flex: 1,
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
    overflow: 'hidden'
  },
  slicerLeft: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    overflow: 'hidden'
  },
  intervalsTextbox: {
    flex: 1,
    backgroundColor: 'var(--bg-darker)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-code)',
    fontSize: '12px',
    padding: '10px',
    outline: 'none',
    resize: 'none'
  },
  jsonLoadSaveRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px'
  },
  loadJsonLabel: {
    height: '32px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'var(--border-color)',
    color: 'var(--text-primary)',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'var(--transition-fast)'
  },
  saveJsonBtn: {
    height: '32px',
    backgroundColor: 'var(--border-color)',
    color: 'var(--text-primary)',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'var(--transition-fast)'
  },
  slicerRight: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    overflow: 'hidden'
  },
  validationFeedbackList: {
    flex: 1,
    backgroundColor: 'var(--bg-darker)',
    border: '1px solid var(--border-color)',
    borderRadius: '4px',
    padding: '8px',
    overflowY: 'auto'
  },
  emptyValidation: {
    textAlign: 'center',
    color: 'var(--text-secondary)',
    padding: '20px 10px',
    fontSize: '11px',
    fontStyle: 'italic'
  },
  validationRow: {
    fontSize: '11px',
    marginBottom: '4px',
    lineHeight: '1.4'
  },
  dangerActionBtn: {
    height: '35px',
    backgroundColor: 'var(--accent-red)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontWeight: 'bold',
    fontSize: '12px',
    transition: 'var(--transition-fast)'
  },
  logsConsolePanel: {
    height: '120px',
    backgroundColor: 'var(--bg-darker)',
    borderTop: '1px solid var(--border-color)',
    display: 'flex',
    flexDirection: 'column',
    padding: '10px 15px',
    flexShrink: 0
  },
  consoleTitle: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
    marginBottom: '4px',
    fontWeight: 'bold'
  },
  logsConsoleOutput: {
    flex: 1,
    overflowY: 'auto',
    fontFamily: 'var(--font-code)',
    fontSize: '11px',
    lineHeight: '1.4'
  },
  logLine: {
    marginBottom: '2px'
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    width: '100vw',
    height: '100vh',
    backgroundColor: 'rgba(0,0,0,0.7)',
    backdropFilter: 'blur(3px)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 9999
  },
  modalCard: {
    width: '400px',
    backgroundColor: 'var(--bg-card)',
    border: '1px solid var(--border-color)',
    borderRadius: '8px',
    padding: '20px',
    boxShadow: '0 4px 24px rgba(0,0,0,0.5)'
  },
  modalHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '15px',
    borderBottom: '1px solid var(--border-color)',
    paddingBottom: '10px'
  },
  modalHeaderIcon: {
    fontSize: '20px'
  },
  modalHeaderTitle: {
    fontSize: '15px',
    fontWeight: 'bold',
    color: 'var(--text-primary)'
  },
  modalBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    marginBottom: '20px'
  },
  modalFieldRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  },
  modalFieldLabel: {
    fontSize: '10px',
    color: 'var(--text-secondary)',
    fontWeight: 'bold'
  },
  modalFieldValue: {
    fontSize: '13px',
    color: 'var(--accent-cyan)',
    fontWeight: 'bold',
    wordBreak: 'break-all'
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end'
  },
  modalCloseBtn: {
    height: '32px',
    padding: '0 15px',
    backgroundColor: 'var(--accent-blue)',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    fontWeight: 'bold',
    fontSize: '12px',
    cursor: 'pointer'
  }
};
