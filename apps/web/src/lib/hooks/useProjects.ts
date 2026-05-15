"use client";

import useSWR from "swr";

import {
  getProject,
  listInterviewStories,
  listProjects,
  listResumeBulletSets,
} from "@/lib/api";
import type { ProjectOut } from "@/types";

export function useProjects(params?: { status?: string; skill?: string; limit?: number }) {
  const { data, error, isLoading, mutate } = useSWR(["projects", params], () =>
    listProjects({ limit: 100, ...params })
  );
  return {
    projects: (data?.items ?? []) as ProjectOut[],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}

export function useProject(id: string) {
  const { data, error, isLoading, mutate } = useSWR(["project", id], () => getProject(id));
  return { project: data, error, isLoading, mutate };
}

export function useResumeBulletSets(projectId: string) {
  const { data, error, isLoading, mutate } = useSWR(["bullet-sets", projectId], () =>
    listResumeBulletSets(projectId)
  );
  return { bulletSets: data ?? [], error, isLoading, mutate };
}

export function useInterviewStories(projectId: string, questionType?: string) {
  const { data, error, isLoading, mutate } = useSWR(["stories", projectId, questionType], () =>
    listInterviewStories(projectId, { question_type: questionType })
  );
  return { stories: data ?? [], error, isLoading, mutate };
}
