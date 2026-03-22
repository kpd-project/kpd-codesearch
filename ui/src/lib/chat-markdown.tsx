import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';
import { cn } from '@/lib/utils';

/** Ссылки в ответах чата и в просмотре лога — единое оформление. */
export const chatMarkdownComponents: Components = {
    a: ({ className, href, children, ...props }) => (
        <a
            href={href}
            className={cn('underline underline-offset-2', className)}
            target="_blank"
            rel="noopener noreferrer"
            {...props}
        >
            {children}
        </a>
    ),
};

const proseBase =
    'prose prose-neutral max-w-none break-words [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_strong]:font-semibold [&_code]:rounded-md [&_code]:bg-muted/80 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.9em]';

export function ChatMarkdownBody({ content, variant }: { content: string; variant: 'user' | 'assistant' }) {
    return (
        <div
            className={cn(
                proseBase,
                variant === 'user'
                    ? 'text-secondary-foreground dark:prose-invert'
                    : 'text-foreground dark:prose-invert',
            )}
        >
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={chatMarkdownComponents}>
                {content}
            </ReactMarkdown>
        </div>
    );
}
