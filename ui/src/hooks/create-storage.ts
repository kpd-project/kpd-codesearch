import { useCallback, useEffect, useState } from 'react';
import { useWindowEvent } from '@/hooks/use-window-event';

export type StorageType = 'localStorage' | 'sessionStorage';

export interface UseStorageOptions<T> {
    key: string;
    defaultValue?: T;
    /** true — прочитать storage после mount (удобно при SSR). false — синхронное чтение при первом рендере. */
    getInitialValueInEffect?: boolean;
    /** Синхронизация между вкладками и внутри вкладки (CustomEvent). */
    sync?: boolean;
    serialize?: (value: T) => string;
    deserialize?: (value: string | undefined) => T;
}

function serializeJSON<T>(value: T, hookName: string): string {
    try {
        return JSON.stringify(value);
    } catch {
        throw new Error(`use-local-storage (${hookName}): failed to serialize value`);
    }
}

function deserializeJSON(value: string | undefined): unknown {
    try {
        return value != null && value !== '' ? JSON.parse(value) : value;
    } catch {
        return value;
    }
}

function createStorageHandler(type: StorageType) {
    const getItem = (key: string) => {
        try {
            return window[type].getItem(key);
        } catch {
            console.warn(`use-local-storage: cannot read ${type}`);
            return null;
        }
    };

    const setItem = (key: string, value: string) => {
        try {
            window[type].setItem(key, value);
        } catch {
            console.warn(`use-local-storage: cannot write ${type}`);
        }
    };

    const removeItem = (key: string) => {
        try {
            window[type].removeItem(key);
        } catch {
            console.warn(`use-local-storage: cannot remove ${type}`);
        }
    };

    return { getItem, setItem, removeItem };
}

/** Имя CustomEvent для синхронизации в рамках одной вкладки (как у Mantine, но свой префикс). */
const LOCAL_EVENT_NAME = 'kpd-codesearch-local-storage';
const SESSION_EVENT_NAME = 'kpd-codesearch-session-storage';

export type UseStorageReturnValue<T> = [
    T,
    (val: T | ((prevState: T) => T)) => void,
    () => void,
];

export function createStorage(type: StorageType, hookName: string) {
    const eventName = type === 'localStorage' ? LOCAL_EVENT_NAME : SESSION_EVENT_NAME;
    const { getItem, setItem, removeItem } = createStorageHandler(type);

    return function useStorage<T>({
        key,
        defaultValue,
        getInitialValueInEffect = true,
        sync = true,
        deserialize = deserializeJSON as (v: string | undefined) => T,
        serialize = (value: T) => serializeJSON(value, hookName),
    }: UseStorageOptions<T>): UseStorageReturnValue<T> {
        const readStorageValue = useCallback(
            (skipStorage?: boolean): T => {
                let blocked: boolean;
                try {
                    blocked =
                        typeof window === 'undefined' ||
                        !(type in window) ||
                        window[type] === null ||
                        !!skipStorage;
                } catch {
                    blocked = true;
                }

                if (blocked) {
                    return defaultValue as T;
                }

                const storageValue = getItem(key);
                return storageValue !== null ? deserialize(storageValue) : (defaultValue as T);
            },
            [key, defaultValue, deserialize],
        );

        const [value, setValue] = useState<T>(() => readStorageValue(getInitialValueInEffect));

        const setStorageValue = useCallback(
            (val: T | ((prevState: T) => T)) => {
                if (val instanceof Function) {
                    setValue((current) => {
                        const result = val(current);
                        setItem(key, serialize(result));
                        queueMicrotask(() => {
                            window.dispatchEvent(
                                new CustomEvent(eventName, { detail: { key, value: result } }),
                            );
                        });
                        return result;
                    });
                } else {
                    setItem(key, serialize(val));
                    window.dispatchEvent(new CustomEvent(eventName, { detail: { key, value: val } }));
                    setValue(val);
                }
            },
            [key, serialize],
        );

        const removeStorageValue = useCallback(() => {
            removeItem(key);
            setValue(defaultValue as T);
            window.dispatchEvent(
                new CustomEvent(eventName, { detail: { key, value: defaultValue } }),
            );
        }, [key, defaultValue]);

        useWindowEvent('storage', (event) => {
            const e = event as StorageEvent;
            if (!sync) return;
            if (e.storageArea === window[type] && e.key === key) {
                setValue(deserialize(e.newValue ?? undefined));
            }
        });

        useWindowEvent(eventName, (event) => {
            const e = event as CustomEvent<{ key: string; value: T }>;
            if (!sync) return;
            if (e.detail?.key === key) {
                setValue(e.detail.value);
            }
        });

        useEffect(() => {
            if (defaultValue !== undefined && value === undefined) {
                setStorageValue(defaultValue);
            }
        }, [defaultValue, value, setStorageValue]);

        useEffect(() => {
            const val = readStorageValue();
            if (val !== undefined) {
                setStorageValue(val);
            }
            // как в Mantine: только смена key; иначе цикл при нестабильных колбэках
            // eslint-disable-next-line react-hooks/exhaustive-deps -- sync read on key change
        }, [key]);

        const out = value === undefined ? (defaultValue as T) : value;
        return [out, setStorageValue, removeStorageValue];
    };
}

export function readStorageValue(type: StorageType) {
    const { getItem } = createStorageHandler(type);

    return function read<T>({
        key,
        defaultValue,
        deserialize = deserializeJSON as (v: string | undefined) => T,
    }: UseStorageOptions<T>): T {
        let blocked: boolean;
        try {
            blocked = typeof window === 'undefined' || !(type in window) || window[type] === null;
        } catch {
            blocked = true;
        }

        if (blocked) {
            return defaultValue as T;
        }

        const storageValue = getItem(key);
        return storageValue !== null ? deserialize(storageValue) : (defaultValue as T);
    };
}
