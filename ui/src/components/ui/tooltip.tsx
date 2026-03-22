import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip"

import { cn } from "@/lib/utils"

function TooltipProvider({
  delay = 200,
  ...props
}: TooltipPrimitive.Provider.Props) {
  return (
    <TooltipPrimitive.Provider
      data-slot="tooltip-provider"
      delay={delay}
      {...props}
    />
  )
}

function Tooltip({ ...props }: TooltipPrimitive.Root.Props) {
  return <TooltipPrimitive.Root data-slot="tooltip" {...props} />
}

function TooltipTrigger({
  className,
  ...props
}: TooltipPrimitive.Trigger.Props) {
  return (
    <TooltipPrimitive.Trigger
      data-slot="tooltip-trigger"
      type="button"
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded-md text-muted-foreground outline-none hover:bg-muted hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50",
        className
      )}
      {...props}
    />
  )
}

function TooltipContent({
  className,
  side = "top",
  sideOffset = 6,
  ...props
}: TooltipPrimitive.Popup.Props & {
  side?: TooltipPrimitive.Positioner.Props["side"]
  sideOffset?: TooltipPrimitive.Positioner.Props["sideOffset"]
}) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Positioner
        side={side}
        sideOffset={sideOffset}
        className="z-100"
      >
        <TooltipPrimitive.Popup
          data-slot="tooltip-content"
          className={cn(
            "z-100 max-w-xs rounded-md border border-border bg-popover px-3 py-2 text-xs text-popover-foreground shadow-md",
            "data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95",
            "data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
            className
          )}
          {...props}
        />
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  )
}

export { TooltipProvider, Tooltip, TooltipTrigger, TooltipContent }
