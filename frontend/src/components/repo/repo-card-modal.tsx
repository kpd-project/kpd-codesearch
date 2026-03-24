import { useEffect, useMemo, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogFooter, DialogClose, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Loader2, Sparkles, Trash2 } from 'lucide-react';
import type { Repo } from '@/types/repo';

interface RepoCardUpdatePayload {
    display_name: string | null;
    relative_path: string | null;
    short_description: string;
    description: string;
}

interface RepoCardModalProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    repo: Repo | null;
    describing: string | null;
    onRemove: (name: string) => Promise<boolean>;
    onDescribe: (name: string) => void;
    onSave: (name: string, payload: RepoCardUpdatePayload) => Promise<void>;
}

export function RepoCardModal({
    open,
    onOpenChange,
    repo,
    describing,
    onRemove,
    onDescribe,
    onSave,
}: RepoCardModalProps) {
    const [isRemoving, setIsRemoving] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [displayName, setDisplayName] = useState('');
    const [relativePath, setRelativePath] = useState('');
    const [shortDescription, setShortDescription] = useState('');
    const [description, setDescription] = useState('');
    const [dirty, setDirty] = useState({
        displayName: false,
        relativePath: false,
        shortDescription: false,
        description: false,
    });
    const [hydratedRepoName, setHydratedRepoName] = useState<string | null>(null);
    const identifierPattern = /^[A-Za-z0-9_-]+$/;

    useEffect(() => {
        if (!open) return;
        if (!repo) {
            setDisplayName('');
            setRelativePath('');
            setShortDescription('');
            setDescription('');
            setDirty({
                displayName: false,
                relativePath: false,
                shortDescription: false,
                description: false,
            });
            setHydratedRepoName(null);
            return;
        }

        // Гидратируем форму при первом открытии или смене репозитория.
        if (hydratedRepoName !== repo.name) {
            setDisplayName(repo.display_name ?? '');
            setRelativePath(repo.relative_path ?? '');
            setShortDescription(repo.short_description ?? '');
            setDescription((repo.full_description ?? repo.description) ?? '');
            setDirty({
                displayName: false,
                relativePath: false,
                shortDescription: false,
                description: false,
            });
            setHydratedRepoName(repo.name);
            return;
        }

        // При синхронизации обновляем только "не тронутые" поля.
        if (!dirty.displayName) setDisplayName(repo.display_name ?? '');
        if (!dirty.relativePath) setRelativePath(repo.relative_path ?? '');
        if (!dirty.shortDescription) setShortDescription(repo.short_description ?? '');
        if (!dirty.description) setDescription((repo.full_description ?? repo.description) ?? '');
    }, [open, repo, hydratedRepoName, dirty]);

    const canSave = useMemo(() => {
        if (!repo) return false;
        if (isSaving || isRemoving) return false;
        return true;
    }, [repo, isSaving, isRemoving]);

    const handleClose = (newOpen: boolean) => {
        onOpenChange(newOpen);
        if (!newOpen) {
            setIsRemoving(false);
        }
    };

    const handleRemove = async () => {
        if (!repo) return;
        setIsRemoving(true);
        const removed = await onRemove(repo.name);
        if (removed) {
            handleClose(false);
        } else {
            setIsRemoving(false);
        }
    };

    const handleSave = async () => {
        if (!repo) return;
        setIsSaving(true);
        try {
            await onSave(repo.name, {
                display_name: displayName.trim() ? displayName.trim() : null,
                relative_path: relativePath.trim() ? relativePath.trim() : null,
                short_description: shortDescription.trim(),
                description: description.trim(),
            });
            setDirty({
                displayName: false,
                relativePath: false,
                shortDescription: false,
                description: false,
            });
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent
                showCloseButton={false}
                className="w-[calc(100%-2rem)] max-h-[85vh] overflow-y-auto sm:max-w-3xl md:max-w-4xl"
            >
                <DialogHeader>
                    <DialogTitle>Карточка репозитория</DialogTitle>
                </DialogHeader>

                {!repo ? (
                    <div className="text-sm text-muted-foreground">Репозиторий не найден.</div>
                ) : (
                    <div className="space-y-5">
                        <div className="space-y-2">
                            <Label htmlFor="repo-identifier-readonly">Идентификатор</Label>
                            <Input
                                id="repo-identifier-readonly"
                                value={repo.name}
                                readOnly
                                className="mt-1 font-mono"
                            />
                            {identifierPattern.test(repo.name) ? (
                                <p className="text-xs text-muted-foreground">
                                    Формат корректный: английские буквы, цифры, "_" и "-", без пробелов.
                                </p>
                            ) : (
                                <p className="text-xs text-destructive">
                                    Некорректный формат идентификатора. Разрешены только английские буквы, цифры, "_" и
                                    "-", без пробелов.
                                </p>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="repo-name-editable">Название</Label>
                            <Input
                                id="repo-name-editable"
                                value={displayName}
                                onChange={(e) => {
                                    setDisplayName(e.target.value);
                                    setDirty((prev) => ({ ...prev, displayName: true }));
                                }}
                                className="mt-1"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="repo-relative-path-editable">
                                Относительный путь (от system base path)
                            </Label>
                            <Input
                                id="repo-relative-path-editable"
                                value={relativePath}
                                onChange={(e) => {
                                    setRelativePath(e.target.value);
                                    setDirty((prev) => ({ ...prev, relativePath: true }));
                                }}
                                placeholder="например: my-frontend"
                                className="mt-1 font-mono"
                            />
                            <p className="text-xs text-muted-foreground">
                                Полный путь для индексации формируется как base_path + этот относительный путь.
                            </p>
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between gap-3">
                                <Label>Описание</Label>
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => onDescribe(repo.name)}
                                    disabled={describing === repo.name}
                                    title="Сгенерировать описание"
                                >
                                    {describing === repo.name ? (
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                    ) : (
                                        <Sparkles className="w-4 h-4 text-primary mr-2" />
                                    )}
                                    Сгенерировать
                                </Button>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="repo-short-description-editable">Короткое описание</Label>
                                <Textarea
                                    id="repo-short-description-editable"
                                    value={shortDescription}
                                    onChange={(e) => {
                                        setShortDescription(e.target.value);
                                        setDirty((prev) => ({ ...prev, shortDescription: true }));
                                    }}
                                    rows={2}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="repo-description-editable">Полное описание</Label>
                                <Textarea
                                    id="repo-description-editable"
                                    value={description}
                                    onChange={(e) => {
                                        setDescription(e.target.value);
                                        setDirty((prev) => ({ ...prev, description: true }));
                                    }}
                                    rows={6}
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <Label>Метаданные коллекции (Qdrant)</Label>
                            <pre className="text-xs whitespace-pre-wrap wrap-break-word rounded-lg bg-muted/40 border border-border/60 p-3 max-h-[30vh] overflow-auto">
                                {JSON.stringify(repo.collection_metadata ?? {}, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}

                <DialogFooter>
                    <div className="flex w-full items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                            <Button
                                variant="destructive"
                                size="sm"
                                onClick={handleRemove}
                                disabled={!repo || isRemoving || isSaving}
                                title="Удалить"
                            >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Удалить
                            </Button>
                        </div>

                        <div className="flex items-center gap-2">
                            <Button onClick={handleSave} disabled={!canSave}>
                                {isSaving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                                        Сохранение…
                                    </>
                                ) : (
                                    'Сохранить'
                                )}
                            </Button>
                            <DialogClose render={<Button variant="outline">Закрыть</Button>} disabled={isSaving} />
                        </div>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
