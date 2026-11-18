"use client";
import { useState } from "react";
import { Play, Pause, ChevronLeft, ChevronRight } from "lucide-react";
import { useWorkspaceStore } from "../app/store";

export default function AudioToolbar() {
  const { audioPlaying, setAudioPlaying, playbackSpeed, setPlaybackSpeed } = useWorkspaceStore();

  const cycleSpeed = () => {
    const speeds = [1.0, 1.2, 1.5, 2.0];
    const nextIdx = (speeds.indexOf(playbackSpeed) + 1) % speeds.length;
    setPlaybackSpeed(speeds[nextIdx]);
  };

  return (
    <div className="fixed top-20 right-6 z-50 bg-[#191f2b] border border-[#303a4c] shadow-lg rounded-full px-4 py-2 flex items-center gap-4 transition-all hover:border-[#4285f4]">
      <div className="flex items-center gap-2">
        <button className="p-1.5 hover:bg-[#303a4c] rounded-full transition-colors text-[#aab5c6]">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button 
          className="p-2 bg-[#4285f4] hover:bg-[#3367d6] text-white rounded-full transition-colors"
          onClick={() => setAudioPlaying(!audioPlaying)}
        >
          {audioPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
        <button className="p-1.5 hover:bg-[#303a4c] rounded-full transition-colors text-[#aab5c6]">
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
      
      <div className="w-px h-6 bg-[#303a4c]"></div>
      
      <button 
        onClick={cycleSpeed}
        className="text-sm font-mono font-medium text-[#edf2fa] hover:text-[#4285f4] min-w-[3rem] text-center"
      >
        {playbackSpeed.toFixed(1)}x
      </button>

      <div className="absolute -bottom-6 right-2 text-[10px] text-[#aab5c6] font-mono opacity-50 pointer-events-none">
        ShorbornoAI TTS Engine
      </div>
    </div>
  );
}
