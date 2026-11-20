import { create } from 'zustand';

export type PlaybackSpeed = 1.0 | 1.2 | 1.5 | 2.0;

export interface WorkspaceState {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  audioPlaying: boolean;
  setAudioPlaying: (playing: boolean) => void;
  playbackSpeed: PlaybackSpeed;
  setPlaybackSpeed: (speed: PlaybackSpeed) => void;
  currentSentenceIndex: number;
  setCurrentSentenceIndex: (index: number) => void;
  sentences: string[];
  setSentences: (sentences: string[]) => void;
  nextSentence: () => void;
  prevSentence: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab, currentSentenceIndex: 0, audioPlaying: false }),
  audioPlaying: false,
  setAudioPlaying: (playing) => set({ audioPlaying: playing }),
  playbackSpeed: 1.0,
  setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),
  currentSentenceIndex: 0,
  setCurrentSentenceIndex: (index) => set({ currentSentenceIndex: index }),
  sentences: [],
  setSentences: (sentences) => set({ sentences, currentSentenceIndex: 0 }),
  nextSentence: () => {
    const { currentSentenceIndex, sentences } = get();
    if (currentSentenceIndex < sentences.length - 1) {
      set({ currentSentenceIndex: currentSentenceIndex + 1 });
    } else {
      set({ audioPlaying: false, currentSentenceIndex: 0 });
    }
  },
  prevSentence: () => {
    const { currentSentenceIndex } = get();
    if (currentSentenceIndex > 0) {
      set({ currentSentenceIndex: currentSentenceIndex - 1 });
    }
  },
}));
