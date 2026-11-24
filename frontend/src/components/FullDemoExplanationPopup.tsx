// File: frontend/src/components/FullDemoExplanationPopup.tsx
import React from 'react';
import { useFullDemo } from '../context/FullDemoContext';
import {
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Pause,
  Play,
  Sparkles,
} from 'lucide-react';

export const FullDemoExplanationPopup: React.FC = () => {
  const {
    isFullDemoActive,
    currentStepIndex,
    currentStep,
    totalSteps,
    isPlaying,
    timeRemaining,
    explanationMode,
    isExplanationOpen,
    toggleExplanationMode,
    toggleExplanationOpen,
    togglePlayPause,
    nextStep,
    prevStep,
  } = useFullDemo();

  if (!isFullDemoActive) return null;

  const currentStepNum = currentStepIndex + 1;
  const explanation =
    explanationMode === 'technical'
      ? currentStep.technicalExplanation
      : currentStep.simpleExplanation;

  // Minimized Floating Pill
  if (!isExplanationOpen) {
    return (
      <button
        onClick={toggleExplanationOpen}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-[#0a1628]/95 border border-cyan-500/80 text-cyan-300 font-mono text-xs font-bold shadow-2xl backdrop-blur-xl hover:bg-cyan-950/80 transition-all animate-bounce-subtle"
      >
        <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
        <span>Explanation: Step {currentStepNum}/26</span>
        <Maximize2 className="w-3.5 h-3.5 ml-1 text-slate-400" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 max-w-[calc(100vw-2rem)] bg-[#0a1628]/95 border border-cyan-500/60 rounded-2xl shadow-2xl backdrop-blur-xl text-slate-100 font-sans overflow-hidden flex flex-col animate-slideUp">
      {/* Header Bar */}
      <div className="px-4 py-3 bg-[#0d1e38] border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
          <span className="font-mono text-xs font-bold text-white uppercase tracking-wider">
            STEP {String(currentStepNum).padStart(2, '0')}: {currentStep.stepTitle}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Mode Pill Toggle */}
          <button
            onClick={toggleExplanationMode}
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border transition-colors ${
              explanationMode === 'technical'
                ? 'bg-blue-600/30 border-blue-400 text-blue-300'
                : 'bg-emerald-600/30 border-emerald-400 text-emerald-300'
            }`}
            title="Toggle between Simple and Technical Explanations"
          >
            {explanationMode === 'technical' ? 'Tech Mode' : 'Simple Mode'}
          </button>

          {/* Minimize Button */}
          <button
            onClick={toggleExplanationOpen}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Minimize Explanation"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Content Body: 4 Structured Sections */}
      <div className="p-4 flex flex-col gap-3 font-mono text-xs max-h-[380px] overflow-y-auto pr-2">
        {/* 1. What is Happening? */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
            <span className="text-cyan-500">▶</span> WHAT IS HAPPENING?
          </span>
          <p className="text-slate-200 text-xs leading-relaxed font-sans bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
            {explanation.whatIsHappening}
          </p>
        </div>

        {/* 2. What is CommShield Doing? */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1">
            <span className="text-blue-500">⚙</span> WHAT IS COMMSHIELD DOING?
          </span>
          <p className="text-slate-200 text-xs leading-relaxed font-sans bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
            {explanation.whatCommShieldIsDoing}
          </p>
        </div>

        {/* 3. Why Does This Matter? */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
            <span className="text-amber-500">★</span> WHY DOES THIS MATTER?
          </span>
          <p className="text-slate-200 text-xs leading-relaxed font-sans bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
            {explanation.whyDoesThisMatter}
          </p>
        </div>

        {/* 4. What Should You Notice? */}
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
            <span className="text-emerald-500">👁</span> WHAT SHOULD YOU NOTICE?
          </span>
          <p className="text-slate-200 text-xs leading-relaxed font-sans bg-slate-900/60 p-2 rounded-lg border border-slate-800/80">
            {explanation.whatShouldYouNotice}
          </p>
        </div>
      </div>

      {/* Footer Controls */}
      <div className="px-4 py-2.5 bg-[#0d1e38] border-t border-slate-800 flex items-center justify-between">
        <button
          onClick={prevStep}
          disabled={currentStepIndex === 0}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed border border-slate-700 text-xs font-mono text-slate-300 hover:text-white transition-colors"
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          <span>Prev</span>
        </button>

        <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
          <button
            onClick={togglePlayPause}
            className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-cyan-400 font-bold border border-slate-700 transition-colors"
          >
            {isPlaying ? (
              <>
                <Pause className="w-3 h-3 fill-current" />
                <span>Pause ({timeRemaining}s)</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 fill-current" />
                <span>Resume</span>
              </>
            )}
          </button>
        </div>

        <button
          onClick={nextStep}
          disabled={currentStepIndex >= totalSteps - 1}
          className="flex items-center gap-1 px-3 py-1 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-xs font-mono font-bold text-white shadow-md transition-colors"
        >
          <span>Next</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
