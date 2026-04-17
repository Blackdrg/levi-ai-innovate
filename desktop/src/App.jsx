import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';

function App() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([
    { id: 1, title: 'Open Chrome', type: 'app', command: 'chrome' },
    { id: 2, title: 'Open Notepad', type: 'app', command: 'notepad' },
    { id: 3, title: 'Search local memory', type: 'ai', command: 'search' },
    { id: 4, title: 'Summarize current folder', type: 'ai', command: 'ls | summarize' }
  ]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const handleKeyDown = async (e) => {
    if (e.key === 'ArrowDown') {
      setSelectedIndex((prev) => (prev + 1) % results.length);
    } else if (e.key === 'ArrowUp') {
      setSelectedIndex((prev) => (prev - 1 + results.length) % results.length);
    } else if (e.key === 'Enter') {
      const command = results[selectedIndex].command;
      if (results[selectedIndex].type === 'app') {
        await invoke('execute_system_command', { cmd: command });
      } else {
        // Send to LEVI Backend
        console.log("Sending to LEVI Backend:", command);
      }
      // Hide palette
      await invoke('toggle_palette');
    } else if (e.key === 'Escape') {
      await invoke('toggle_palette');
    }
  };

  return (
    <div className="palette-container">
      <div className="command-box">
        <div className="input-wrapper">
          <span className="levi-logo">💠</span>
          <input
            autoFocus
            placeholder="Search apps, files, or ask LEVI..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div className="results">
          {results.filter(r => r.title.toLowerCase().includes(query.toLowerCase())).map((item, index) => (
            <div 
              key={item.id} 
              className={`result-item ${index === selectedIndex ? 'selected' : ''}`}
              onClick={() => setSelectedIndex(index)}
            >
              <span className="icon">{item.type === 'app' ? '🚀' : '🧠'}</span>
              <span className="title">{item.title}</span>
            </div>
          ))}
        </div>
        <div className="status-bar">
          <div><span className="pulse"></span> LEVI Backend: Online</div>
          <div>ESC to close | ENTER to execute</div>
        </div>
      </div>
    </div>
  );
}

export default App;
