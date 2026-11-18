"use client";
import { useState } from "react";
import CloudShell from "../components/CloudShell";
import FileManager from "../components/FileManager";
import InfraControlPlane from "../components/InfraControlPlane";
import VoicePanel from "../components/VoicePanel";
import { useWorkspaceStore } from "../app/store";
import { Server, TerminalSquare, UploadCloud, Mic, LayoutDashboard, Shield } from "lucide-react";

export default function WorkspaceHome() {
  const { activeTab, setActiveTab } = useWorkspaceStore();

  const navItems = [
    { id: "overview", label: "Overview", icon: <LayoutDashboard className="w-4 h-4" /> },
    { id: "cloudshell", label: "Cloud Shell", icon: <TerminalSquare className="w-4 h-4" /> },
    { id: "ingestion", label: "Data Ingestion", icon: <UploadCloud className="w-4 h-4" /> },
    { id: "infra", label: "Infra & SSH", icon: <Server className="w-4 h-4" /> },
    { id: "voice", label: "Bangla Voice", icon: <Mic className="w-4 h-4" /> },
  ];

  return (
    <div className="layout-container">
      <aside className="sidebar">
        <div className="brand flex items-center gap-2">
          <Shield className="w-5 h-5 text-[#4285f4]" /> MCORE 360
        </div>
        <nav className="flex-1 mt-4">
          {navItems.map(item => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-6 py-3 text-sm transition-colors border-l-4 ${activeTab === item.id ? "bg-[#4285f41a] border-[#4285f4] text-[#edf2fa]" : "border-transparent text-[#aab5c6] hover:bg-[#191f2b] hover:text-[#edf2fa]"}`}
            >
              {item.icon} {item.label}
            </button>
          ))}
        </nav>
        <div className="p-4 border-t border-[#303a4c] text-xs text-[#aab5c6] font-mono">
          Matrix Core v0.6<br/>
          Secured Tunnel
        </div>
      </aside>

      <div className="main-wrapper">
        <header className="topbar">
          <div className="environment flex items-center gap-2">
             <span className="w-2 h-2 rounded-full bg-[#34a853]"></span> Env: Local Debian L1
          </div>
          <div className="user font-mono bg-[#191f2b] px-3 py-1 rounded-md border border-[#303a4c]">mcoreai</div>
        </header>

        <main className="content">
          {activeTab === "overview" && (
            <div className="workspace-grid">
              <InfraControlPlane />
              <div className="card ai-panel">
                <h2 className="font-bold text-lg mb-2">AI Advisor (Gemini)</h2>
                <p className="text-sm text-[#aab5c6] mb-4">Contextual AI loaded. Awaiting prompt.</p>
                <textarea className="prompt-input flex-1" placeholder="Ask AI Advisor about your infrastructure..."></textarea>
              </div>
            </div>
          )}
          
          {activeTab === "cloudshell" && (
             <div className="h-full">
               <CloudShell />
             </div>
          )}

          {activeTab === "ingestion" && (
             <div className="h-full max-w-4xl mx-auto">
               <FileManager />
             </div>
          )}

          {activeTab === "infra" && (
             <div className="h-full max-w-4xl mx-auto">
               <InfraControlPlane />
             </div>
          )}

          {activeTab === "voice" && (
             <div className="h-full max-w-3xl mx-auto">
               <VoicePanel />
             </div>
          )}
        </main>
      </div>
    </div>
  );
}
