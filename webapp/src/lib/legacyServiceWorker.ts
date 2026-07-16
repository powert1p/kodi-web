const LEGACY_FLUTTER_CACHES = new Set([
  'flutter-app-cache',
  'flutter-temp-cache',
  'flutter-app-manifest',
])

/** Снимает старый root-scope Flutter SW, не затрагивая текущий `/app/` PWA. */
export async function retireLegacyFlutterServiceWorker(): Promise<void> {
  if (!('serviceWorker' in navigator)) return

  const registrations = await navigator.serviceWorker.getRegistrations()
  await Promise.all(
    registrations
      .filter((registration) => new URL(registration.scope).pathname === '/')
      .map((registration) => registration.unregister()),
  )

  if (!('caches' in globalThis)) return
  const cacheNames = await globalThis.caches.keys()
  await Promise.all(
    cacheNames
      .filter((name) => LEGACY_FLUTTER_CACHES.has(name))
      .map((name) => globalThis.caches.delete(name)),
  )
}
