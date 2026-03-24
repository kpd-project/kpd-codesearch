import { createStorage, readStorageValue, type UseStorageOptions } from '@/hooks/create-storage';

export const useSessionStorage = createStorage('sessionStorage', 'useSessionStorage');

const readFromSession = readStorageValue('sessionStorage');

export function readSessionStorageValue<T>(options: UseStorageOptions<T>): T {
    return readFromSession<T>(options);
}
