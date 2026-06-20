import { createContext, useCallback, useContext, useState } from 'react'

interface ConfirmOptions { title?: string; message: string; confirmText?: string; danger?: boolean }

const ConfirmContext = createContext<(opts: ConfirmOptions) => Promise<boolean>>(() => Promise.resolve(false))
export const useConfirm = () => useContext(ConfirmContext)

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<(ConfirmOptions & { resolve: (v: boolean) => void }) | null>(null)

  const confirm = useCallback((opts: ConfirmOptions) => {
    return new Promise<boolean>(resolve => setState({ ...opts, resolve }))
  }, [])

  const close = (value: boolean) => { state?.resolve(value); setState(null) }

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {state && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-sm w-full mx-4">
            {state.title && <h3 className="font-bold mb-2">{state.title}</h3>}
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">{state.message}</p>
            <div className="flex justify-end gap-2">
              <button onClick={() => close(false)} className="px-4 py-1.5 text-sm border dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700">Cancel</button>
              <button onClick={() => close(true)} className={`px-4 py-1.5 text-sm rounded text-white ${state.danger ? 'bg-red-600 hover:bg-red-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
                {state.confirmText || 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </ConfirmContext.Provider>
  )
}
