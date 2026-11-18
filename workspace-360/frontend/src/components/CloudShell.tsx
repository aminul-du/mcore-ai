"use client";
import { useEffect, useRef } from 'react';
import 'xterm/css/xterm.css';

export default function CloudShell() {
  const terminalRef = useRef<HTMLDivElement>(null);
  const term = useRef<any>(null);

  useEffect(() => {
    if (!terminalRef.current || term.current) return;
    
    // Dynamic import to prevent SSR issues with self/window
    Promise.all([
      import('xterm'),
      import('xterm-addon-fit')
    ]).then(([{ Terminal }, { FitAddon }]) => {
      term.current = new Terminal({
        theme: {
          background: '#0b1017',
          foreground: '#edf2fa',
          cursor: '#4285f4'
        },
        fontFamily: 'ui-monospace, monospace',
        fontSize: 14,
        cursorBlink: true
      });
      
      const fitAddon = new FitAddon();
      term.current.loadAddon(fitAddon);
      term.current.open(terminalRef.current);
      fitAddon.fit();
      
      term.current.writeln('\x1b[1;36m[MCORE Matrix Core]\x1b[0m Cloud Shell Initialized.');
      term.current.writeln('Authorized Access L1-L5 layers report their health directly from the Matrix Core.');
      term.current.write('\r\n$ ');

      term.current.onData((e: string) => {
        if (e === '\r') {
          term.current?.write('\r\n$ ');
        } else if (e === '\x7f') {
          term.current?.write('\b \b');
        } else {
          term.current?.write(e);
        }
      });

      const handleResize = () => fitAddon.fit();
      window.addEventListener('resize', handleResize);
    });

    return () => {
      term.current?.dispose();
      term.current = null;
    };
  }, []);

  return (
    <div className="flex flex-col h-full bg-[#0b1017] rounded-lg border border-[#303a4c] overflow-hidden">
      <div className="bg-[#191f2b] border-b border-[#303a4c] px-4 py-2 flex justify-between items-center text-sm">
        <span className="font-semibold text-[#edf2fa]">debian@mcore-ais-001 ~</span>
        <span className="text-[#34a853] flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#34a853] animate-pulse"></span> Connected via TLS/QUIC
        </span>
      </div>
      <div ref={terminalRef} className="flex-1 p-2 overflow-hidden" />
    </div>
  );
}
