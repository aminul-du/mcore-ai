"use client";
import { useState } from "react";
import { Mic, Send } from "lucide-react";

export default function VoicePanel() {
  const [stdout, setStdout] = useState("Bangla-first local transcription active (Unicode U+0980–U+09FF enforced).");

  return (
    <div className="flex flex-col h-full bg-[#191f2b] rounded-xl border border-[#303a4c] p-5">
      <h2 className="font-bold text-lg mb-4">বাংলা ভয়েস / প্রম্পট → Gemini CLI</h2>
      <textarea 
        className="w-full bg-[#0d121a] text-[#edf2fa] border border-[#303a4c] rounded-lg p-3 font-[ui-monospace,monospace] min-h-[120px] resize-y focus:border-[#4285f4] outline-none" 
        placeholder="বাংলায় বলুন বা লিখুন (যেমন: আমার সোনার বাংলা)..."
      />
      <div className="flex items-center gap-3 mt-4">
        <select className="bg-[#0d121a] border border-[#303a4c] rounded-lg p-2 text-sm outline-none focus:border-[#4285f4]">
          <option value="bn">বাংলা — Bangladesh (bn-BD Primary)</option>
          <option value="en">English (en)</option>
        </select>
        <button className="flex items-center gap-2 bg-[#006a4e] text-white px-4 py-2 rounded-lg font-semibold hover:bg-[#008a66] transition-colors">
          <Mic className="w-4 h-4"/> বাংলায় বলুন
        </button>
        <button className="flex items-center gap-2 bg-[#4285f4] text-white px-4 py-2 rounded-lg font-semibold hover:bg-[#3367d6] transition-colors">
          <Send className="w-4 h-4"/> Send
        </button>
      </div>
      <div className="mt-4 p-3 bg-[#0b1017] border border-[#303a4c] rounded-lg font-mono text-sm text-[#aab5c6] flex-1 overflow-auto">
        {stdout}
      </div>
    </div>
  );
}
