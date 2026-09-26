import * as React from "react";

import { cn } from "@/lib/utils";

interface CheckboxToggleProps extends Omit<React.ComponentProps<"input">, "type" | "onChange"> {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function CheckboxToggle({ className, checked, onCheckedChange, ...props }: CheckboxToggleProps) {
  return (
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onCheckedChange(e.target.checked)}
      className={cn(
        "size-4 rounded border-input text-primary accent-current outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
}

export { CheckboxToggle };
