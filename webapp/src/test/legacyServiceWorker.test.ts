import { afterEach, describe, expect, it, vi } from 'vitest'
import { retireLegacyFlutterServiceWorker } from '../lib/legacyServiceWorker'

describe('retireLegacyFlutterServiceWorker', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('снимает только root-scope SW и удаляет только Flutter caches', async () => {
    const unregisterRoot = vi.fn().mockResolvedValue(true)
    const unregisterPwa = vi.fn().mockResolvedValue(true)
    const deleteCache = vi.fn().mockResolvedValue(true)

    vi.stubGlobal('navigator', {
      serviceWorker: {
        getRegistrations: vi.fn().mockResolvedValue([
          { scope: 'https://example.test/', unregister: unregisterRoot },
          { scope: 'https://example.test/app/', unregister: unregisterPwa },
        ]),
      },
    })
    vi.stubGlobal('caches', {
      keys: vi.fn().mockResolvedValue(['flutter-app-cache', 'workbox-precache-v2']),
      delete: deleteCache,
    })

    await retireLegacyFlutterServiceWorker()

    expect(unregisterRoot).toHaveBeenCalledOnce()
    expect(unregisterPwa).not.toHaveBeenCalled()
    expect(deleteCache).toHaveBeenCalledOnce()
    expect(deleteCache).toHaveBeenCalledWith('flutter-app-cache')
  })
})
