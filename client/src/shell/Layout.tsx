import { TopBar } from "./TopBar";
import { Navigator } from "./Navigator";
import { Canvas } from "./Canvas";
import { Properties } from "./Properties";
import { StatusBar } from "./StatusBar";
import { useAppStore } from "../store/useAppStore";

export function Layout() {
  const mode = useAppStore((s) => s.mode);

  return (
    <div className="h-screen w-screen flex flex-col bg-bg-base text-fg overflow-hidden">
      <TopBar />
      <div className="flex-1 grid grid-cols-[280px_1fr_320px] overflow-hidden min-h-0">
        <Navigator mode={mode} />
        <Canvas mode={mode} />
        <Properties mode={mode} />
      </div>
      <StatusBar mode={mode} />
    </div>
  );
}
