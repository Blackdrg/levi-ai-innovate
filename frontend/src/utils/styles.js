import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Standard utility for combining CSS classes with tailwind-merge and clsx.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
