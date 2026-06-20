import { useTranslation } from 'react-i18next'

const LANGS = [
  { code: 'es', flag: '🇲🇽', label: 'Español' },
  { code: 'en', flag: '🇺🇸', label: 'English' },
]

export function LangSwitcher() {
  const { i18n } = useTranslation()

  const change = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('lang', code)
  }

  return (
    <div className="flex gap-1">
      {LANGS.map(({ code, flag }) => (
        <button
          key={code}
          onClick={() => change(code)}
          className={`text-lg px-1 rounded ${i18n.language === code ? 'ring-2 ring-indigo-400' : 'opacity-50 hover:opacity-100'}`}
          title={code}
        >
          {flag}
        </button>
      ))}
    </div>
  )
}
