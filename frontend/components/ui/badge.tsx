import * as React from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "success" | "error" | "warning";

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-accent/20 text-accent border-accent/30",
  success: "bg-green-500/20 text-green-400 border-green-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  warning: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
};

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2",
        variantClasses[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
