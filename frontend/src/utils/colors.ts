const PRIMEVUE_SEVERITIES = [
  'success',
  'info',
  'warning',
  'danger',
  'secondary',
  'contrast',
]

function hashString(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash = hash & hash // Convert to 32bit integer
  }
  return Math.abs(hash)
}

export function getCohortColor(cohortName: string): string {
  if (cohortName === '—') return 'secondary'

  const hash = hashString(cohortName)
  const index = hash % PRIMEVUE_SEVERITIES.length
  return PRIMEVUE_SEVERITIES[index]
}
