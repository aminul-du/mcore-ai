"use client";

import React, { useEffect, useRef, useCallback } from "react";
import { Play, Pause, ChevronLeft, ChevronRight } from "lucide-react";
import { useWorkspaceStore, PlaybackSpeed } from "../app/store";

export default function AudioToolbar() {
  const {
    activeTab,
    audioPlaying,
    setAudioPlaying,
    playbackSpeed,
    setPlaybackSpeed,
    currentSentenceIndex,
    setCurrentSentenceIndex,
    sentences,
    setSentences,
    nextSentence,
    prevSentence,
  } = useWorkspaceStore();

  const synthRef = useRef<SpeechSynthesisUtterance | null>(null);
  const isPlayingRef = useRef<boolean>(audioPlaying);
  isPlayingRef.current = audioPlaying;

  const playbackSpeedRef = useRef<PlaybackSpeed>(playbackSpeed);
  playbackSpeedRef.current = playbackSpeed;

  const currentIndexRef = useRef<number>(currentSentenceIndex);
  currentIndexRef.current = currentSentenceIndex;

  // 1. Multilingual DOM Sentence Parser & Segmenter
  useEffect(() => {
    const timer = setTimeout(() => {
      const container = document.querySelector("main.content") || document.body;
      if (!container) return;

      const extracted: string[] = [];
      const textNodes: { node: Text; text: string }[] = [];

      // Multilingual sentence splitter (Latin .!? and Bengali Dari । ॥)
      const sentenceRegex = new RegExp('[^.!?।॥\\n]+(?:[.!?।॥]+["\']?|\\n+|$)', 'gm');

      const walker = document.createTreeWalker(
        container,
        NodeFilter.SHOW_TEXT,
        {
          acceptNode: (node) => {
            const parent = node.parentElement;
            if (!parent) return NodeFilter.FILTER_REJECT;
            const tag = parent.tagName.toLowerCase();
            // Skip non-reading or interactive controls
            if (['script', 'style', 'button', 'input', 'textarea', 'pre', 'code'].includes(tag)) {
              return NodeFilter.FILTER_REJECT;
            }
            if (parent.closest('#mcore-audio-toolbar') || parent.closest('.fixed')) {
              return NodeFilter.FILTER_REJECT;
            }
            return (node.textContent && node.textContent.trim().length > 3)
              ? NodeFilter.FILTER_ACCEPT
              : NodeFilter.FILTER_REJECT;
          },
        }
      );

      let curr: Node | null;
      while ((curr = walker.nextNode())) {
        textNodes.push({ node: curr as Text, text: curr.textContent || '' });
      }

      let globalIdx = 0;
      textNodes.forEach(({ node, text }) => {
        const matches = text.match(sentenceRegex);
        if (!matches || matches.length === 0) return;

        const frag = document.createDocumentFragment();
        matches.forEach((sentence) => {
          const trimmed = sentence.trim();
          if (trimmed.length > 2) {
            extracted.push(trimmed);
            const span = document.createElement('span');
            span.id = 'tts-seg-' + globalIdx;
            span.className = 'tts-reading-seg transition-all duration-200';
            span.textContent = sentence;
            frag.appendChild(span);
            globalIdx++;
          } else {
            frag.appendChild(document.createTextNode(sentence));
          }
        });

        if (node.parentNode) {
          node.parentNode.replaceChild(frag, node);
        }
      });

      setSentences(extracted);
    }, 150);

    return () => clearTimeout(timer);
  }, [activeTab, setSentences]);

  // 2. DOM Highlight & Auto-scroll Synchronizer
  useEffect(() => {
    // Clear all existing highlights
    document.querySelectorAll('.tts-reading-seg').forEach((el) => {
      el.classList.remove('bg-blue-500/25', 'text-blue-300', 'ring-1', 'ring-blue-400', 'rounded', 'px-1', 'font-medium');
    });

    const activeEl = document.getElementById('tts-seg-' + currentSentenceIndex);
    if (activeEl) {
      activeEl.classList.add('bg-blue-500/25', 'text-blue-300', 'ring-1', 'ring-blue-400', 'rounded', 'px-1', 'font-medium');
      activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [currentSentenceIndex]);

  // 3. Dual-Engine Speech Synthesis
  const speakCurrent = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    window.speechSynthesis.cancel();

    const idx = currentIndexRef.current;
    const currentSentences = useWorkspaceStore.getState().sentences;
    if (!currentSentences || !currentSentences[idx]) {
      setAudioPlaying(false);
      return;
    }

    const text = currentSentences[idx];
    const isBengali = /[\u0980-\u09FF]/.test(text);

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = playbackSpeedRef.current;
    utterance.lang = isBengali ? 'bn-BD' : 'en-US';

    utterance.onend = () => {
      if (isPlayingRef.current) {
        nextSentence();
      }
    };

    utterance.onerror = (e) => {
      if (e.error !== 'canceled' && isPlayingRef.current) {
        nextSentence();
      }
    };

    synthRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  }, [nextSentence, setAudioPlaying]);

  // Playback state observer
  useEffect(() => {
    if (audioPlaying) {
      speakCurrent();
    } else {
      if (typeof window !== 'undefined' && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    }
  }, [audioPlaying, currentSentenceIndex, speakCurrent]);

  const cycleSpeed = () => {
    const speeds: PlaybackSpeed[] = [1.0, 1.2, 1.5, 2.0];
    const nextIdx = (speeds.indexOf(playbackSpeed) + 1) % speeds.length;
    const newSpeed = speeds[nextIdx];
    setPlaybackSpeed(newSpeed);
    if (audioPlaying) {
      speakCurrent();
    }
  };

  const handlePrev = () => {
    prevSentence();
    if (audioPlaying) {
      speakCurrent();
    }
  };

  const handleNext = () => {
    nextSentence();
    if (audioPlaying) {
      speakCurrent();
    }
  };

  return (
    <div
      id="mcore-audio-toolbar"
      className="fixed top-20 right-6 z-50 bg-[#191f2b] border border-[#303a4c] shadow-lg rounded-full px-4 py-2 flex items-center gap-4 transition-all hover:border-[#4285f4]"
      role="region"
      aria-label="Audio Control Reading Toolbar"
    >
      <div className="flex items-center gap-2">
        <button
          onClick={handlePrev}
          disabled={currentSentenceIndex === 0}
          className="p-1.5 hover:bg-[#303a4c] rounded-full transition-colors text-[#aab5c6] disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer"
          aria-label="Previous sentence"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <button
          className="p-2 bg-[#4285f4] hover:bg-[#3367d6] text-white rounded-full transition-colors active:scale-95 shadow-sm cursor-pointer"
          onClick={() => setAudioPlaying(!audioPlaying)}
          aria-label={audioPlaying ? "Pause reading" : "Play reading"}
        >
          {audioPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />}
        </button>
        <button
          onClick={handleNext}
          disabled={currentSentenceIndex >= sentences.length - 1}
          className="p-1.5 hover:bg-[#303a4c] rounded-full transition-colors text-[#aab5c6] disabled:opacity-30 disabled:hover:bg-transparent cursor-pointer"
          aria-label="Next sentence"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      <div className="w-px h-6 bg-[#303a4c]"></div>

      <button
        onClick={cycleSpeed}
        className="text-sm font-mono font-medium text-[#edf2fa] hover:text-[#4285f4] min-w-[3rem] text-center px-1.5 py-0.5 rounded bg-[#1e2738] transition-colors cursor-pointer"
        aria-label={`Playback speed: ${playbackSpeed}x`}
      >
        {playbackSpeed.toFixed(1)}x
      </button>

      {sentences.length > 0 && (
        <span className="text-[11px] font-mono text-[#aab5c6] border-l border-[#303a4c] pl-3">
          {currentSentenceIndex + 1}/{sentences.length}
        </span>
      )}

      <div className="absolute -bottom-6 right-2 text-[10px] text-[#aab5c6] font-mono opacity-60 pointer-events-none">
        ShorbornoAI TTS Engine
      </div>
    </div>
  );
}
