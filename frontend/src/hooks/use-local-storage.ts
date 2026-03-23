import {
    createStorage,
    readStorageValue,
    type UseStorageOptions,
    type UseStorageReturnValue,
} from '@/hooks/create-storage';

export type { UseStorageOptions, UseStorageReturnValue };

/** Синхронизация с localStorage (логика по мотивам @mantine/hooks/use-local-storage). */
export const useLocalStorage = createStorage('localStorage', 'useLocalStorage');

const readFromLocal = readStorageValue('localStorage');

export function readLocalStorageValue<T>(options: UseStorageOptions<T>): T {
    return readFromLocal<T>(options);
}
