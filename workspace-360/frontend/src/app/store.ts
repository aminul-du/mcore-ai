import { create } from 'zustand'

interface WorkspaceState {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  audioPlaying: boolean;
  setAudioPlaying: (playing: boolean) => void;
  playbackSpeed: number;
  setPlaybackSpeed: (speed: number) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab }),
  audioPlaying: false,
  setAudioPlaying: (playing) => set({ audioPlaying: playing }),
  playbackSpeed: 1.0,
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
}))
