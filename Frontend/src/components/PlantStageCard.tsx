import type { VisionReading } from '../types'

const STAGE_CONFIG = {
  Green:    { color: '#4ade80', label: 'Growing', emoji: '🌱' },
  WhitePink:{ color: '#f9a8d4', label: 'Ripening', emoji: '🌸' },
  Red:      { color: '#f87171', label: 'Ready',   emoji: '🍓' },
}

interface Props {
  vision: VisionReading | null
}

export default function PlantStageCard({ vision }: Props) {
  const cfg = vision ? STAGE_CONFIG[vision.stage] : null

  return (
    <div className="bg-gh-card border border-gh-border rounded-2xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-gh-muted text-sm font-medium uppercase tracking-wide">Plant Stage</span>
        <span className="text-2xl">{cfg?.emoji ?? '🌿'}</span>
      </div>

      {vision && cfg ? (
        <>
          <div className="flex items-center gap-3">
            <div
              className="w-4 h-4 rounded-full flex-shrink-0"
              style={{ backgroundColor: cfg.color, boxShadow: `0 0 12px ${cfg.color}` }}
            />
            <div>
              <div className="text-2xl font-bold">{vision.stage}</div>
              <div className="text-gh-muted text-xs">{cfg.label}</div>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            {[
              { label: 'Green', pct: vision.green_pct, color: '#4ade80' },
              { label: 'White/Pink', pct: vision.white_pink_pct, color: '#f9a8d4' },
              { label: 'Red', pct: vision.red_pct, color: '#f87171' },
            ].map((row) => (
              <div key={row.label} className="flex items-center gap-2">
                <span className="text-xs text-gh-muted w-20">{row.label}</span>
                <div className="flex-1 bg-gh-border rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${row.pct}%`, backgroundColor: row.color }}
                  />
                </div>
                <span className="text-xs tabular-nums w-10 text-right">{row.pct.toFixed(0)}%</span>
              </div>
            ))}
          </div>

          <div className="text-xs text-gh-muted">
            Confidence: {(vision.confidence * 100).toFixed(0)}%
          </div>
        </>
      ) : (
        <div className="text-gh-muted text-sm">No vision data yet</div>
      )}
    </div>
  )
}
