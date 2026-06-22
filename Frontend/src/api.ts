import type { TelemetryReading, VisionReading } from './types'

const BASE = ''

export async function fetchLatestTelemetry(deviceId: string): Promise<TelemetryReading | null> {
  const res = await fetch(`${BASE}/api/v1/telemetry/latest/${deviceId}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Telemetry fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchTelemetryHistory(deviceId: string, limit = 40): Promise<TelemetryReading[]> {
  const res = await fetch(`${BASE}/api/v1/telemetry/history/${deviceId}?limit=${limit}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchLatestVision(deviceId: string): Promise<VisionReading | null> {
  const res = await fetch(`${BASE}/api/v1/vision/latest/${deviceId}`)
  if (res.status === 404) return null
  if (!res.ok) throw new Error(`Vision fetch failed: ${res.status}`)
  return res.json()
}

export async function triggerCapture(deviceId: string): Promise<VisionReading> {
  const res = await fetch(`${BASE}/api/v1/vision/capture/${deviceId}`, { method: 'POST' })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Capture failed' }))
    throw new Error(err.detail ?? 'Capture failed')
  }
  return res.json()
}

export async function sendActuation(deviceId: string, action: string): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/actuation/${deviceId}/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action }),
  })
  if (!res.ok) throw new Error(`Actuation failed: ${res.status}`)
}
