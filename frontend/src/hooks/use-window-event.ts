import { useEffect, useRef } from 'react';

/**
 * Подписка на событие window; актуальный listener через ref (без лишних переподписок).
 * Идея как в @mantine/hooks/use-window-event.
 */
export function useWindowEvent(
    type: string,
    listener: (event: Event) => void,
    options?: boolean | AddEventListenerOptions,
) {
    const listenerRef = useRef(listener);

    useEffect(() => {
        listenerRef.current = listener;
    }, [listener]);

    useEffect(() => {
        const handler = (e: Event) => listenerRef.current(e);
        window.addEventListener(type, handler, options);
        return () => window.removeEventListener(type, handler, options);
    }, [type, options]);
}
