import { AreaChart, Area, ResponsiveContainer, Tooltip } from 'recharts'

interface Props {
  label: string
  icon: string
  value: number | null
  unit: string
  color: string
  history: number[]
}

export default function SensorCard({ label, icon, value, unit, color, history }: Props) {
  const data = history.map((v) => ({ v }))

  return (
    <div className="bg-gh-card border border-gh-border rounded-2xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-gh-muted text-sm font-medium uppercase tracking-wide">{label}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <div className="flex items-end gap-1">
        <span className="text-5xl font-bold tabular-nums leading-none">
          {value !== null ? value.toFixed(1) : '--'}
        </span>
        <span className="text-gh-muted text-lg mb-1">{unit}</span>
      </div>
      <div className="h-12">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 2 }}>
            <defs>
              <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke={color}
              strokeWidth={2}
              fill={`url(#grad-${label})`}
              dot={false}
              isAnimationActive={false}
            />
            <Tooltip
              contentStyle={{ background: '#0f1f0f', border: '1px solid #1e3a1e', borderRadius: 8, fontSize: 12 }}
              formatter={(v: number) => [`${v.toFixed(1)}${unit}`, label]}
              labelFormatter={() => ''}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
