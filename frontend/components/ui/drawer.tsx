"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

export interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

function Drawer({ open, onClose, title, children, className }: DrawerProps) {
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  React.useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-300",
          open ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        )}
      />

      {/* Sliding panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={cn(
          "fixed right-0 top-0 z-50 h-full w-full max-w-md border-l border-[rgba(255,255,255,0.1)] bg-[#0d0d14] shadow-2xl",
          "transform transition-transform duration-300 ease-in-out",
          open ? "translate-x-0" : "translate-x-full",
          className
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.1)] px-6 py-4">
          {title && (
            <h2 className="text-base font-semibold text-white">{title}</h2>
          )}
          <button
            onClick={onClose}
            className={cn(
              "ml-auto rounded-lg p-1.5 text-white/50 transition-colors hover:bg-[rgba(255,255,255,0.06)] hover:text-white",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
            )}
            aria-label="Close drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="h-[calc(100%-65px)] overflow-y-auto px-6 py-4">
          {children}
        </div>
      </div>
    </>
  );
}

export { Drawer };
