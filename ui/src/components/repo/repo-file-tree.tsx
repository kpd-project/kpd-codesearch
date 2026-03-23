import { useState } from 'react';
import { Collapsible } from '@base-ui/react/collapsible';
import { ChevronRight, Folder, FolderOpen, FileCode, File, FileX } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { FileTreeNode, SkipReason } from '@/types/repo';

export type FileTreeFilter = 'all' | 'indexed' | 'skipped';

export interface RepoFileTreeProps {
    nodes: FileTreeNode[];
    selected?: string | null;
    onSelect?: (path: string, node: FileTreeNode) => void;
    filter?: FileTreeFilter;
    className?: string;
    /** Отступ на уровень вложенности в пикселях (default 16) */
    treeIndent?: number;
}

const SKIP_REASON_LABEL: Record<SkipReason, string> = {
    ignored_directory: 'Игнор-директория',
    ignored_name: 'Игнор по имени',
    ignored_extension: 'Игнор-расширение',
    gitignore: '.gitignore',
    unsupported_extension: 'Не поддерживается чанкером',
    node_modules_path: 'node_modules',
};

function matchesFilter(node: FileTreeNode, filter: FileTreeFilter): boolean {
    if (filter === 'all') return true;
    if (filter === 'indexed') return node.indexed === true;
    if (filter === 'skipped') return node.indexed === false;
    return true;
}

/** Проверяем, есть ли в поддереве хотя бы один узел, проходящий фильтр. */
function subtreeMatchesFilter(node: FileTreeNode, filter: FileTreeFilter): boolean {
    if (filter === 'all') return true;
    if (node.type === 'file') return matchesFilter(node, filter);
    if (node.indexed === false && filter === 'skipped') return true;
    if (node.children) {
        return node.children.some((c) => subtreeMatchesFilter(c, filter));
    }
    return false;
}

function FileIcon({ node }: { node: FileTreeNode }) {
    if (node.indexed === true) {
        return <FileCode className="w-3.5 h-3.5 shrink-0 text-emerald-600 dark:text-emerald-400" />;
    }
    if (node.indexed === false) {
        return <FileX className="w-3.5 h-3.5 shrink-0 text-muted-foreground/50" />;
    }
    return <File className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />;
}

interface TreeNodeProps {
    node: FileTreeNode;
    depth: number;
    selected: string | null | undefined;
    onSelect: ((path: string, node: FileTreeNode) => void) | undefined;
    filter: FileTreeFilter;
    treeIndent: number;
}

function TreeNode({ node, depth, selected, onSelect, filter, treeIndent }: TreeNodeProps) {
    const [open, setOpen] = useState(depth === 0);

    if (!subtreeMatchesFilter(node, filter)) return null;

    const indent = depth * treeIndent;

    if (node.type === 'dir') {
        const isIgnored = node.indexed === false;
        const children = node.children ?? [];
        const visibleChildren = children.filter((c) => subtreeMatchesFilter(c, filter));

        if (isIgnored) {
            // Заглушка игнорируемой директории — не раскрывается
            const label = (
                <div
                    className="flex items-center gap-1.5 py-0.5 px-1 rounded text-muted-foreground/40 select-none"
                    style={{ paddingLeft: indent + 4 }}
                >
                    <Folder className="w-3.5 h-3.5 shrink-0" />
                    <span className="font-mono text-xs truncate">{node.name}</span>
                </div>
            );
            if (node.skip_reason) {
                return (
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger render={<div />} className="block w-full">
                                {label}
                            </TooltipTrigger>
                            <TooltipContent>{SKIP_REASON_LABEL[node.skip_reason] ?? node.skip_reason}</TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                );
            }
            return label;
        }

        return (
            <Collapsible.Root open={open} onOpenChange={setOpen}>
                <Collapsible.Trigger
                    className="flex w-full items-center gap-1 py-0.5 px-1 rounded text-left hover:bg-muted/60 transition-colors select-none cursor-pointer"
                    style={{ paddingLeft: indent + 4 }}
                    render={<button type="button" />}
                >
                    <ChevronRight
                        className={cn(
                            'w-3 h-3 shrink-0 text-muted-foreground transition-transform duration-150',
                            open && 'rotate-90',
                        )}
                    />
                    {open ? (
                        <FolderOpen className="w-3.5 h-3.5 shrink-0 text-amber-500" />
                    ) : (
                        <Folder className="w-3.5 h-3.5 shrink-0 text-amber-500" />
                    )}
                    <span className="font-mono text-xs truncate">{node.name}</span>
                    {visibleChildren.length > 0 && (
                        <span className="ml-auto font-mono text-[10px] text-muted-foreground/50 shrink-0 pr-1">
                            {visibleChildren.length}
                        </span>
                    )}
                </Collapsible.Trigger>
                <Collapsible.Panel>
                    {visibleChildren.map((child) => (
                        <TreeNode
                            key={child.path}
                            node={child}
                            depth={depth + 1}
                            selected={selected}
                            onSelect={onSelect}
                            filter={filter}
                            treeIndent={treeIndent}
                        />
                    ))}
                </Collapsible.Panel>
            </Collapsible.Root>
        );
    }

    // file
    const isSelected = selected === node.path;
    const isIndexed = node.indexed === true;

    const onClickHandler = () => {
        if (onSelect) onSelect(node.path, node);
    };

    const row = (
        <button
            type="button"
            onClick={onClickHandler}
            className={cn(
                'flex w-full items-center gap-1.5 py-0.5 px-1 rounded text-left font-mono text-xs transition-colors',
                isSelected
                    ? 'bg-primary/15 text-foreground'
                    : isIndexed
                    ? 'hover:bg-muted/60 text-foreground'
                    : 'hover:bg-muted/40 text-muted-foreground/60 cursor-default',
            )}
            style={{ paddingLeft: indent + 4 }}
            disabled={!isIndexed}
        >
            <FileIcon node={node} />
            <span className="truncate">{node.name}</span>
        </button>
    );

    if (!isIndexed && node.skip_reason) {
        return (
            <TooltipProvider>
                <Tooltip>
                    <TooltipTrigger render={<div />} className="block w-full">
                        {row}
                    </TooltipTrigger>
                    <TooltipContent>{SKIP_REASON_LABEL[node.skip_reason] ?? node.skip_reason}</TooltipContent>
                </Tooltip>
            </TooltipProvider>
        );
    }

    return row;
}

export function RepoFileTree({
    nodes,
    selected,
    onSelect,
    filter = 'all',
    className,
    treeIndent = 20,
}: RepoFileTreeProps) {
    if (nodes.length === 0) {
        return <div className={cn('py-8 text-center text-muted-foreground text-xs', className)}>Файлы не найдены</div>;
    }

    return (
        <div className={cn('py-1', className)}>
            {nodes.map((node) => (
                <TreeNode
                    key={node.path}
                    node={node}
                    depth={0}
                    selected={selected}
                    onSelect={onSelect}
                    filter={filter}
                    treeIndent={treeIndent}
                />
            ))}
        </div>
    );
}
