"use client";

const STORAGE_KEY = "kos:search:recents";
const MAX_RECENTS = 8;

export function getRecentSearches(): string[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

export function addRecentSearch(query: string) {
  const trimmed = query.trim();
  if (!trimmed) return;
  const existing = getRecentSearches().filter((q) => q !== trimmed);
  localStorage.setItem(STORAGE_KEY, JSON.stringify([trimmed, ...existing].slice(0, MAX_RECENTS)));
}

export function clearRecentSearches() {
  localStorage.removeItem(STORAGE_KEY);
}
