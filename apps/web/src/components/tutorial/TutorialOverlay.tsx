"use client";

import { useCallback, useEffect, useState, type CSSProperties } from "react";
import { createPortal } from "react-dom";

import { useTutorial } from "./TutorialProvider";
import { TutorialPopup } from "./TutorialPopup";
import { TUTORIAL_STEPS } from "./tutorial-steps";

const POPUP_WIDTH = 400;
const POPUP_HEIGHT = 230;
const GAP = 16;
const MARGIN = 16;

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function popupPosition(rect: DOMRect, position = "bottom") {
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  let left = rect.left + rect.width / 2 - POPUP_WIDTH / 2;
  let top = rect.bottom + GAP;

  if (position === "top") {
    top = rect.top - POPUP_HEIGHT - GAP;
  } else if (position === "left") {
    left = rect.left - POPUP_WIDTH - GAP;
    top = rect.top + rect.height / 2 - POPUP_HEIGHT / 2;
  } else if (position === "right") {
    left = rect.right + GAP;
    top = rect.top + rect.height / 2 - POPUP_HEIGHT / 2;
  }

  return {
    left: clamp(left, MARGIN, viewportWidth - POPUP_WIDTH - MARGIN),
    top: clamp(top, MARGIN, viewportHeight - POPUP_HEIGHT - MARGIN),
  };
}

export function TutorialOverlay() {
  const { active, stepIndex, next, prev, stop } = useTutorial();
  const [mounted, setMounted] = useState(false);
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null);
  const [popupStyle, setPopupStyle] = useState<CSSProperties>({});
  const step = TUTORIAL_STEPS[stepIndex];

  useEffect(() => {
    setMounted(true);
  }, []);

  const recompute = useCallback(() => {
    if (!active || !step?.target) {
      setTargetRect(null);
      setPopupStyle({});
      return;
    }
    const target = document.querySelector(step.target);
    if (!(target instanceof HTMLElement)) {
      setTargetRect(null);
      setPopupStyle({});
      return;
    }
    const rect = target.getBoundingClientRect();
    setTargetRect(rect);
    setPopupStyle(popupPosition(rect, step.position));
  }, [active, step]);

  useEffect(() => {
    if (!active) return;
    recompute();

    const target = step?.target ? document.querySelector(step.target) : null;
    const observer = new ResizeObserver(() => recompute());
    if (target instanceof HTMLElement) observer.observe(target);

    window.addEventListener("resize", recompute);
    window.addEventListener("scroll", recompute, true);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", recompute);
      window.removeEventListener("scroll", recompute, true);
    };
  }, [active, recompute, step]);

  useEffect(() => {
    if (!active || !step?.target) return;
    const target = document.querySelector(step.target);
    if (!(target instanceof HTMLElement)) return;

    const previousOutline = target.style.outline;
    const previousOutlineOffset = target.style.outlineOffset;
    const previousZIndex = target.style.zIndex;
    target.style.outline = "2px solid rgb(96 165 250)";
    target.style.outlineOffset = "3px";
    target.style.zIndex = "70";
    return () => {
      target.style.outline = previousOutline;
      target.style.outlineOffset = previousOutlineOffset;
      target.style.zIndex = previousZIndex;
    };
  }, [active, step]);

  useEffect(() => {
    if (!active) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        stop();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [active, stop]);

  if (!mounted || !active || !step) return null;

  const centered = !targetRect;
  const popup = (
    <div className="fixed inset-0 z-[80] pointer-events-none">
      {targetRect ? (
        <>
          <div
            className="fixed bg-black/70 pointer-events-none"
            style={{ left: 0, top: 0, width: "100vw", height: targetRect.top }}
          />
          <div
            className="fixed bg-black/70 pointer-events-none"
            style={{
              left: 0,
              top: targetRect.bottom,
              width: "100vw",
              height: `calc(100vh - ${targetRect.bottom}px)`,
            }}
          />
          <div
            className="fixed bg-black/70 pointer-events-none"
            style={{ left: 0, top: targetRect.top, width: targetRect.left, height: targetRect.height }}
          />
          <div
            className="fixed bg-black/70 pointer-events-none"
            style={{
              left: targetRect.right,
              top: targetRect.top,
              width: `calc(100vw - ${targetRect.right}px)`,
              height: targetRect.height,
            }}
          />
        </>
      ) : null}
      <div
        className="pointer-events-auto fixed"
        style={
          centered
            ? { left: "50%", top: "50%", transform: "translate(-50%, -50%)" }
            : popupStyle
        }
      >
        <TutorialPopup step={step} stepIndex={stepIndex} onNext={next} onPrev={prev} onStop={stop} />
      </div>
    </div>
  );

  return createPortal(popup, document.body);
}
