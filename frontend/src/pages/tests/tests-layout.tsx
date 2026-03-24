import { useLocation, useNavigate } from "react-router-dom";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { VectorSearchTest } from "./vector-search-test";
import { ChunkFileTest } from "./chunk-file-test";

const TEST_TABS = [
  { value: "vector-search", label: "Поиск по векторам" },
  { value: "file-chunks", label: "Чанки файла" },
];

function getActiveTest(pathname: string): string {
  if (pathname.includes("file-chunks")) return "file-chunks";
  if (pathname.includes("vector-search")) return "vector-search";
  return "vector-search";
}

export function TestsLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeTest = getActiveTest(location.pathname);

  return (
    <Tabs
      value={activeTest}
      onValueChange={(v) => navigate(`/tests/${v}`)}
      className="h-full flex flex-col"
    >
      <div className="border-b border-border bg-background shrink-0 px-4">
        <TabsList className="h-9 bg-transparent p-0 gap-0 border-0">
          {TEST_TABS.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              className="h-9 rounded-none px-4 py-0 text-sm border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent"
            >
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </div>

      <TabsContent value="vector-search" className="flex-1 m-0 min-h-0 overflow-auto">
        <VectorSearchTest />
      </TabsContent>
      <TabsContent value="file-chunks" className="flex-1 m-0 min-h-0 overflow-hidden">
        <ChunkFileTest />
      </TabsContent>
    </Tabs>
  );
}
