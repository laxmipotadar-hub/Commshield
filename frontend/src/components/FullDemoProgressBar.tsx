// File: frontend/src/components/FullDemoProgressBar.tsx
import React from 'react';
import { useFullDemo, DEMO_SECTIONS } from '../context/FullDemoContext';
import {
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  RotateCcw,
  Sparkles,
  X,
  FileText,
  Sliders,
} from 'lucide-react';

export const FullDemoProgressBar: React.FC = () => {
  const {
    isFullDemoActive,
    currentStepIndex,
    currentStep,
    totalSteps,
    completedSteps,
    isPlaying,
    playbackSpeed,
    timeRemaining,
    explanationMode,
    nextStep,
    prevStep,
    goToStep,
    togglePlayPause,
    setSpeed,
    toggleExplanationMode,
    stopFullDemo,
    openFinalReport,
    restartDemo,
  } = useFullDemo();

  if (!isFullDemoActive) return null;

  const currentStepNum = currentStepIndex + 1;
  const progressPct = Math.round((currentStepNum / totalSteps) * 100);

  return (
    <div className="w-full bg-[#070e1b] border-b border-cyan-500/40 px-4 py-2.5 shadow-2xl flex flex-col gap-2 z-50 text-slate-100 font-sans select-none animate-fadeIn">
      {/* Top Row: Brand & Status, Current Stage, and Action Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        {/* Left: Brand Badge & Step Number */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gradient-to-r from-cyan-950 to-blue-950 border border-cyan-500/60 text-cyan-300 font-mono text-xs font-bold shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
            <span className="tracking-wider">COMMSHIELD FULL SYSTEM DEMO</span>
          </div>

          <div className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono font-bold text-white shadow-xs">
            STEP <span className="text-cyan-400">{String(currentStepNum).padStart(2, '0')}</span> OF {totalSteps}
          </div>

          <span className="text-xs font-mono font-bold text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700/60">
            {progressPct}% COMPLETE
          </span>
        </div>

        {/* Center: Current Stage Title */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400 font-medium">Stage {currentStep.sectionIndex}/7:</span>
          <span className="text-xs font-bold text-cyan-300 font-mono tracking-wide">
            {currentStep.sectionTitle}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-xs font-bold text-white tracking-wide truncate max-w-[280px]">
            {currentStep.stepTitle}
          </span>
        </div>

        {/* Right: Playback, Mode & Navigation Controls */}
        <div className="flex items-center gap-2">
          {/* Mode Toggle: Simple vs Technical */}
          <button
            onClick={toggleExplanationMode}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono font-bold border transition-all ${
              explanationMode === 'technical'
                ? 'bg-blue-600/30 border-blue-400 text-blue-300 shadow-sm'
                : 'bg-emerald-600/30 border-emerald-400 text-emerald-300 shadow-sm'
            }`}
            title="Toggle between Simple and Technical Explanations"
          >
            <Sliders className="w-3 h-3" />
            <span>{explanationMode === 'technical' ? 'Technical' : 'Simple'}</span>
          </button>

          {/* Speed Selector */}
          <button
            onClick={() => setSpeed(playbackSpeed === 1 ? 2 : 1)}
            className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-500 text-xs font-mono text-slate-300"
            title="Toggle Demo Speed"
          >
            {playbackSpeed}x
          </button>

          {/* Prev Step */}
          <button
            onClick={prevStep}
            disabled={currentStepIndex === 0}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 hover:text-white transition-colors"
            title="Previous Step"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          {/* Play / Pause with Countdown */}
          <button
            onClick={togglePlayPause}
            className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-mono font-bold border transition-colors shadow-sm ${
              isPlaying
                ? 'bg-amber-600/30 border-amber-500 text-amber-300'
                : 'bg-emerald-600/30 border-emerald-500 text-emerald-300'
            }`}
            title={isPlaying ? 'Pause Demo' : 'Resume Auto-Play'}
          >
            {isPlaying ? (
              <>
                <Pause className="w-3.5 h-3.5 fill-current" />
                <span>{timeRemaining}s</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Play</span>
              </>
            )}
          </button>

          {/* Next Step */}
          <button
            onClick={nextStep}
            disabled={currentStepIndex >= totalSteps - 1}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 hover:text-white transition-colors"
            title="Next Step"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {/* View Report Button */}
          <button
            onClick={openFinalReport}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-purple-900/40 border border-purple-500/60 hover:bg-purple-800/50 text-purple-300 text-xs font-mono font-semibold transition-colors"
            title="Open Demonstration Report"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Report</span>
          </button>

          {/* Restart */}
          <button
            onClick={restartDemo}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Restart Full Demo"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          {/* Exit Demo */}
          <button
            onClick={stopFullDemo}
            className="p-1.5 rounded-lg bg-rose-950/40 border border-rose-700/60 hover:bg-rose-900/60 text-rose-300 hover:text-white transition-colors"
            title="Exit Full Demo"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Row: 7 Segmented Progress Bar */}
      <div className="grid grid-cols-7 gap-1.5 pt-0.5">
        {DEMO_SECTIONS.map((sec) => {
          const [startStep, endStep] = sec.stepRange;
          const sectionStepCount = endStep - startStep + 1;
          const isSectionCurrent = currentStepNum >= startStep && currentStepNum <= endStep;
          const isSectionPast = currentStepNum > endStep;

          return (
            <div
              key={sec.index}
              onClick={() => goToStep(startStep - 1)}
              className={`flex flex-col gap-1 p-1.5 rounded-lg cursor-pointer transition-all border ${
                isSectionCurrent
                  ? 'bg-cyan-950/60 border-cyan-500/80 ring-1 ring-cyan-500/40 shadow-sm'
                  : isSectionPast
                  ? 'bg-slate-900/80 border-slate-700/80 hover:border-slate-600'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center justify-between text-[10px] font-mono leading-none">
                <span className={`font-bold truncate ${isSectionCurrent ? 'text-cyan-300' : isSectionPast ? 'text-slate-300' : 'text-slate-500'}`}>
                  {sec.index}. {sec.title}
                </span>
                <span className="text-slate-500 font-semibold">{startStep}-{endStep}</span>
              </div>

              {/* Multi-segment tick bar for steps in section */}
              <div className="grid grid-cols-6 gap-1 h-1.5 w-full">
                {Array.from({ length: sectionStepCount }).map((_, sIdx) => {
                  const stepNum = startStep + sIdx;
                  const isDone = completedSteps.has(stepNum);
                  const isCur = stepNum === currentStepNum;

                  return (
                    <div
                      key={stepNum}
                      className={`h-full rounded-sm transition-all ${
                        isCur
                          ? 'bg-cyan-400 animate-pulse shadow-[0_0_6px_#22d3ee]'
                          : isDone
                          ? 'bg-emerald-500'
                          : isSectionPast
                          ? 'bg-slate-600'
                          : 'bg-slate-800'
                      }`}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
