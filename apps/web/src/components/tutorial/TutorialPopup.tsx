"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { TUTORIAL_STEPS, type TutorialStep } from "./tutorial-steps";

interface TutorialPopupProps {
  step: TutorialStep;
  stepIndex: number;
  onNext: () => void;
  onPrev: () => void;
  onStop: () => void;
}

export function TutorialPopup({
  step,
  stepIndex,
  onNext,
  onPrev,
  onStop,
}: TutorialPopupProps) {
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === TUTORIAL_STEPS.length - 1;

  return (
    <div className="min-w-[300px] max-w-[400px] rounded-xl border border-gray-800 bg-gray-900 text-gray-100 shadow-2xl">
      <div className="border-b border-gray-800 px-4 py-3">
        <p className="text-xs font-medium uppercase text-gray-500">
          Step {stepIndex + 1} of {TUTORIAL_STEPS.length} <span className="text-gray-700">·</span>{" "}
          {step.title}
        </p>
      </div>
      <div className="px-4 py-4 text-sm leading-6 text-gray-300">{step.body}</div>
      <div className="flex items-center justify-between gap-2 border-t border-gray-800 px-4 py-3">
        {isFirst ? (
          <span />
        ) : (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onPrev}
            leftIcon={<ArrowLeft size={14} />}
          >
            Back
          </Button>
        )}
        <div className="flex items-center gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={onStop}>
            Stop Tour
          </Button>
          <Button
            type="button"
            variant="primary"
            size="sm"
            onClick={onNext}
            rightIcon={!isLast ? <ArrowRight size={14} /> : undefined}
          >
            {isLast ? "Explore" : "Next"}
          </Button>
        </div>
      </div>
    </div>
  );
}
