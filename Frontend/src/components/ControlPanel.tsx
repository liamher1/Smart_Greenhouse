import { useState } from 'react'
import { sendActuation } from '../api'

const DEVICE_ID = 'esp32-gh-01'

interface Actuator {
  key: 'pump' | 'fan' | 'light'
  label: string
  icon: string
  onAction: string
  offAction: string
}

const ACTUATORS: Actuator[] = [
  { key: 'pump',  label: 'Pump',  icon: '💧', onAction: 'PUMP_ON',  offAction: 'PUMP_OFF' },
  { key: 'fan',   label: 'Fan',   icon: '🌀', onAction: 'FAN_ON',   offAction: 'FAN_OFF'  },
  { key: 'light', label: 'Light', icon: '💡', onAction: 'LIGHT_ON', offAction: 'LIGHT_OFF' },
]

export default function ControlPanel() {
  const [states, setStates] = useState({ pump: false, fan: false, light: false })
  const [loading, setLoading] = useState({ pump: false, fan: false, light: false })

  async function toggle(a: Actuator) {
    const isOn = states[a.key]
    const action = isOn ? a.offAction : a.onAction
    setStates((s) => ({ ...s, [a.key]: !isOn }))
    setLoading((l) => ({ ...l, [a.key]: true }))
    try {
      await sendActuation(DEVICE_ID, action)
    } catch {
      setStates((s) => ({ ...s, [a.key]: isOn }))
    } finally {
      setLoading((l) => ({ ...l, [a.key]: false }))
    }
  }

  return (
    <div className="bg-gh-card border border-gh-border rounded-2xl p-5">
      <h2 className="text-gh-muted text-sm font-medium uppercase tracking-wide mb-4">Control Panel</h2>
      <div className="grid grid-cols-3 gap-4">
        {ACTUATORS.map((a) => {
          const on = states[a.key]
          const busy = loading[a.key]
          return (
            <button
              key={a.key}
              onClick={() => toggle(a)}
              disabled={busy}
              className={`
                flex flex-col items-center gap-3 p-4 rounded-xl border transition-all duration-200
                ${on
                  ? 'bg-gh-accent/10 border-gh-accent shadow-[0_0_20px_rgba(74,222,128,0.15)]'
                  : 'bg-gh-bg border-gh-border hover:border-gh-muted'
                }
                ${busy ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}
              `}
            >
              <span className="text-3xl">{a.icon}</span>
              <span className="text-sm font-medium">{a.label}</span>
              <span
                className={`text-xs font-semibold px-3 py-1 rounded-full ${
                  on ? 'bg-gh-accent text-black' : 'bg-gh-border text-gh-muted'
                }`}
              >
                {busy ? '...' : on ? 'ON' : 'OFF'}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
