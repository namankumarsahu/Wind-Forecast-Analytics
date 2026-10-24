import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "../services/api";

const FIVE_MIN = 5 * 60 * 1000;

export const useConfig = () => useQuery({ queryKey: ["config"], queryFn: api.config, staleTime: Infinity });

export const useOverview = (start: string | undefined, end: string | undefined) =>
  useQuery({
    queryKey: ["overview", start, end],
    queryFn: () => api.overview(start!, end!),
    enabled: !!start && !!end,
    staleTime: FIVE_MIN,
    placeholderData: keepPreviousData,
  });

export const usePeriods = (date: string | undefined) =>
  useQuery({
    queryKey: ["periods", date],
    queryFn: () => api.periods(date!),
    enabled: !!date,
    staleTime: FIVE_MIN,
    placeholderData: keepPreviousData,
  });

export const useAccuracy = (start: string | undefined, end: string | undefined) =>
  useQuery({
    queryKey: ["accuracy", start, end],
    queryFn: () => api.accuracy(start!, end!),
    enabled: !!start && !!end,
    staleTime: FIVE_MIN,
    placeholderData: keepPreviousData,
  });
