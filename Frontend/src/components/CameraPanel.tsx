import { useState } from 'react'
import { triggerCapture } from '../api'
import type { VisionReading } from '../types'

const VISION_DEVICE_ID = 'rpi-gh-01'

interface Props {
  vision: VisionReading | null
  onResult: (v: VisionReading) => void
}

export default function CameraPanel({ vision, onResult }: Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCapture() {
    setLoading(true)
    setError(null)
    try {
      const result = await triggerCapture(VISION_DEVICE_ID)
      onResult(result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Capture failed')
    } finally {
      setLoading(false)
    }
  }

  const imageUrl = vision?.image_filename ? `/images/${vision.image_filename}` : null

  return (
    <div className="bg-gh-card border border-gh-border rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-gh-muted text-sm font-medium uppercase tracking-wide">Camera</span>
        <span className="text-2xl">📷</span>
      </div>

      <div className="relative aspect-video bg-gh-bg rounded-xl overflow-hidden border border-gh-border">
        {imageUrl ? (
          <img src={imageUrl} alt="Latest capture" className="w-full h-full object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gh-muted text-sm">
            No snapshot yet
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center gap-2">
            <div className="w-8 h-8 border-2 border-gh-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gh-accent">Capturing...</span>
          </div>
        )}
      </div>

      {error && (
        <p className="text-red-400 text-xs">{error}</p>
      )}

      {vision && (
        <p className="text-xs text-gh-muted">
          Last capture: {new Date(vision.timestamp).toLocaleString()}
        </p>
      )}

      <button
        onClick={handleCapture}
        disabled={loading}
        className="
          w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200
          bg-gh-accent text-black hover:brightness-110
          disabled:opacity-50 disabled:cursor-not-allowed
          shadow-[0_0_20px_rgba(74,222,128,0.2)]
        "
      >
        {loading ? 'Analyzing...' : 'Capture & Analyze'}
      </button>
    </div>
  )
}
