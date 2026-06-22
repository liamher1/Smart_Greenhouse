export interface TelemetryReading {
  id: string
  device_id: string
  temperature: number
  humidity: number
  soil_moisture: number | null
  water_level: number | null
  timestamp: string
}

export interface VisionReading {
  id: string
  device_id: string
  stage: 'Green' | 'WhitePink' | 'Red'
  green_pct: number
  white_pink_pct: number
  red_pct: number
  confidence: number
  image_filename: string | null
  timestamp: string
}

export type ActuatorState = {
  PUMP_ON: boolean
  FAN_ON: boolean
  LIGHT_ON: boolean
}
