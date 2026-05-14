"use client";

import useSWR from "swr";
import { getChat, listChats } from "@/lib/api";

export function useChats(params?: { provider?: string; q?: string }) {
  const { data, error, isLoading, mutate } = useSWR(["chats", params], () => listChats(params), {
    refreshInterval: 0,
  });
  return { chats: data ?? [], error, isLoading, mutate };
}

export function useChat(id: string) {
  const { data, error, isLoading, mutate } = useSWR(["chat", id], () => getChat(id));
  return { chat: data, error, isLoading, mutate };
}
