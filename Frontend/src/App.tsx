import { useEffect, useRef, useState } from 'react'
import { fetchLatestVision, fetchTelemetryHistory } from './api'
import SensorCard from './components/SensorCard'
import ControlPanel from './components/ControlPanel'
import CameraPanel from './components/CameraPanel'
import PlantStageCard from './components/PlantStageCard'
import type { TelemetryReading, VisionReading } from './types'

const DEVICE_ID = 'esp32-gh-01'
const VISION_DEVICE_ID = 'rpi-gh-01'
const WS_URL = `ws://${window.location.hostname}:${window.location.port || 8000}/ws/telemetry`

export default function App() {
  const [latest, setLatest] = useState<TelemetryReading | null>(null)
  const [history, setHistory] = useState<TelemetryReading[]>([])
  const [vision, setVision] = useState<VisionReading | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    fetchTelemetryHistory(DEVICE_ID, 40).then(setHistory)
    fetchLatestVision(VISION_DEVICE_ID).then(setVision)
  }, [])

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        setTimeout(connect, 3000)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (e) => {
        const data: TelemetryReading = JSON.parse(e.data)
        setLatest(data)
        setHistory((prev) => [...prev.slice(-39), data])
      }
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const current = latest ?? history[history.length - 1] ?? null

  return (
    <div className="min-h-screen bg-gh-bg p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Smart Greenhouse</h1>
          <p className="text-gh-muted text-sm mt-0.5">Strawberry Monitor — {DEVICE_ID}</p>
        </div>
        <div className="flex items-center gap-2 bg-gh-card border border-gh-border rounded-full px-4 py-2">
          <div className={`w-2 h-2 rounded-full live-dot ${connected ? 'bg-gh-accent' : 'bg-red-500'}`} />
          <span className="text-sm text-gh-muted">{connected ? 'Live' : 'Offline'}</span>
        </div>
      </div>

      {/* Sensor Cards */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <SensorCard
          label="Temperature"
          icon="🌡"
          value={current?.temperature ?? null}
          unit="°C"
          color="#fb923c"
          history={history.map((r) => r.temperature)}
        />
        <SensorCard
          label="Humidity"
          icon="💧"
          value={current?.humidity ?? null}
          unit="%"
          color="#60a5fa"
          history={history.map((r) => r.humidity)}
        />
        <SensorCard
          label="Soil Moisture"
          icon="🪴"
          value={current?.soil_moisture ?? null}
          unit="%"
          color="#a3e635"
          history={history.map((r) => r.soil_moisture ?? 0)}
        />
      </div>

      {/* Control Panel */}
      <div className="mb-4">
        <ControlPanel />
      </div>

      {/* Camera + Plant Stage */}
      <div className="grid grid-cols-2 gap-4">
        <CameraPanel vision={vision} onResult={setVision} />
        <PlantStageCard vision={vision} />
      </div>

      {/* Footer */}
      <div className="mt-6 text-center text-xs text-gh-muted">
        {current
          ? `Last reading: ${new Date(current.timestamp).toLocaleString()}`
          : 'Waiting for sensor data...'}
      </div>
    </div>
  )
}
