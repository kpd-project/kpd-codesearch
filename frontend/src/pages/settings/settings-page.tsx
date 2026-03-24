import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { SystemInfoSection } from "@/components/settings/system-info-section";
import { RuntimeSection } from "@/components/settings/runtime-section";
import { SettingsHeader } from "@/components/settings/settings-header";

export default function SettingsPage() {
  return (
    <div className="h-screen flex flex-col bg-background">
      <SettingsHeader />

      <ScrollArea className="flex-1">
        <div className="max-w-3xl mx-auto p-6 space-y-8">
          <SystemInfoSection />
          <Separator />
          <RuntimeSection />
        </div>
      </ScrollArea>
    </div>
  );
}