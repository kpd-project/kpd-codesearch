import { Link } from "react-router-dom";
import { ArrowLeft, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SettingsHeader() {
  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <Link to="/">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Назад
          </Button>
        </Link>
        <h1 className="text-xl font-semibold flex items-center gap-2">
          <Settings className="w-5 h-5" />
          Настройки
        </h1>
      </div>
    </header>
  );
}