import { describe, expect, it } from 'vitest'
import en from '@/i18n/en.json'
import zhTW from '@/i18n/zh-TW.json'

type LocaleNode = string | number | boolean | null | LocaleNode[] | LocaleMap
type LocaleMap = {
  [key: string]: LocaleNode
}

const flattenKeys = (value: LocaleNode, prefix = ''): string[] => {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) =>
      flattenKeys(item, prefix ? `${prefix}.${index}` : String(index)),
    )
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, child]) =>
      flattenKeys(child, prefix ? `${prefix}.${key}` : key),
    )
  }
  return prefix ? [prefix] : []
}

const flattenStrings = (
  value: LocaleNode,
  prefix = '',
): Array<{ key: string; value: string }> => {
  if (Array.isArray(value)) {
    return value.flatMap((item, index) =>
      flattenStrings(item, prefix ? `${prefix}.${index}` : String(index)),
    )
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, child]) =>
      flattenStrings(child, prefix ? `${prefix}.${key}` : key),
    )
  }
  return typeof value === 'string' && prefix ? [{ key: prefix, value }] : []
}

describe('i18n locale completeness', () => {
  it('keeps Traditional Chinese keys aligned with English', () => {
    const englishKeys = flattenKeys(en)
    const zhTWKeys = new Set(flattenKeys(zhTW))
    const missingKeys = englishKeys.filter((key) => !zhTWKeys.has(key))

    expect(missingKeys).toEqual([])
  })

  it('does not leave placeholder question marks in Traditional Chinese labels', () => {
    const placeholderEntries = flattenStrings(zhTW).filter(({ value }) =>
      /\?{2,}/.test(value),
    )

    expect(placeholderEntries).toEqual([])
  })
})
