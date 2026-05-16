"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import { seedTutorial } from "@/lib/api";
import { TUTORIAL_STEPS } from "./tutorial-steps";

type SeedingStatus = "idle" | "loading" | "ready" | "error";

interface TutorialContextValue {
  active: boolean;
  stepIndex: number;
  seedingStatus: SeedingStatus;
  start: () => Promise<void>;
  next: () => void;
  prev: () => void;
  stop: () => void;
}

const TutorialContext = createContext<TutorialContextValue | null>(null);

export function TutorialProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [active, setActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [seedingStatus, setSeedingStatus] = useState<SeedingStatus>("idle");

  const start = useCallback(async () => {
    setSeedingStatus("loading");
    try {
      await seedTutorial();
      setStepIndex(0);
      setActive(true);
      setSeedingStatus("ready");
    } catch {
      setSeedingStatus("error");
    }
  }, []);

  const stop = useCallback(() => {
    setActive(false);
    if (stepIndex === TUTORIAL_STEPS.length - 1) {
      localStorage.setItem("kos:tutorial:completed", "true");
    }
  }, [stepIndex]);

  const next = useCallback(() => {
    setStepIndex((current) => {
      if (current >= TUTORIAL_STEPS.length - 1) {
        localStorage.setItem("kos:tutorial:completed", "true");
        setActive(false);
        return current;
      }
      return current + 1;
    });
  }, []);

  const prev = useCallback(() => {
    setStepIndex((current) => Math.max(0, current - 1));
  }, []);

  useEffect(() => {
    if (!active) return;
    const step = TUTORIAL_STEPS[stepIndex];
    if (step?.navigateTo) {
      router.push(step.navigateTo);
    }
  }, [active, router, stepIndex]);

  return (
    <TutorialContext.Provider value={{ active, stepIndex, seedingStatus, start, next, prev, stop }}>
      {children}
    </TutorialContext.Provider>
  );
}

export function useTutorial(): TutorialContextValue {
  const ctx = useContext(TutorialContext);
  if (!ctx) throw new Error("useTutorial must be used inside TutorialProvider");
  return ctx;
}
