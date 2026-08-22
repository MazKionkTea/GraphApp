import { memo } from "react";
import { Handle, Position } from "@xyflow/react";
import { clsx } from "clsx";

type Data = { label: string; icon?: string | null; color?: string | null; selected?: boolean };

export const MindMapNodeComponent = memo(({ data, selected }: any) => {
  const color = data.color || "#58a6ff";
  return (
    <div
      className={clsx(
        "rounded-lg px-3 py-2 min-w-[120px] text-center transition-shadow",
        "bg-bg-elevated border-2",
        selected ? "shadow-lg" : "hover:shadow-md"
      )}
      style={{ borderColor: selected ? color : "#30363d" }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, width: 6, height: 6 }} />
      <Handle type="source" position={Position.Right} style={{ background: color, width: 6, height: 6 }} />
      <div className="flex items-center gap-1.5 justify-center">
        {data.icon && <span className="text-base leading-none">{data.icon}</span>}
        <span className="text-[12.5px] font-medium text-fg">{data.label || "Node"}</span>
      </div>
    </div>
  );
});

MindMapNodeComponent.displayName = "MindMapNodeComponent";
