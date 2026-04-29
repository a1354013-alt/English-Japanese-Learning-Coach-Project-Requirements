import { createI18n } from 'vue-i18n'
import zhTW from './zh-TW.json'
import en from './en.json'

const savedLocale =
  typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
    ? window.localStorage.getItem('locale') || 'zh-TW'
    : 'zh-TW'

const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: savedLocale,
  fallbackLocale: 'en',
  messages: {
    'zh-TW': zhTW,
    en,
  },
})

export default i18n
