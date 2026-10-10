import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react'
import {
  ZoomIn, ZoomOut, RotateCcw, Move, Info, Zap, CheckCircle2,
  AlertTriangle, Layers, Eye, X, ShieldAlert, Cpu
} from 'lucide-react'

export interface WokwiPart {
  type: string
  id: string
  top: number
  left: number
  attrs?: Record<string, any>
}

export type WokwiConnection = [string, string, string?, string[]?]

export interface DiagramData {
  version?: number
  author?: string
  editor?: string
  parts: WokwiPart[]
  connections: WokwiConnection[]
}

export interface CircuitEditorProps {
  diagram: DiagramData
  pinAssignments?: Array<{
    component_instance: string
    component_pin: string
    gpio_pin: number
    description: string
  }>
  onPartSelect?: (partId: string) => void
  readOnly?: boolean
}

// Pin metadata per component type for accurate physical layout & wire snapping
interface PinDef {
  name: string
  relX: number
  relY: number
  label?: string
  type: 'power' | 'ground' | 'digital' | 'analog' | 'signal'
}

interface ComponentMeta {
  width: number
  height: number
  title: string
  pins: PinDef[]
  render: (part: WokwiPart, isSelected: boolean, isHovered: boolean) => React.ReactNode
}

// Resistor color code calculation
function getResistorBands(valueStr?: string): [string, string, string, string] {
  const val = parseInt(valueStr || '220', 10)
  const colors = [
    '#000000', '#8B4513', '#EF4444', '#F97316', '#FBBF24',
    '#22C55E', '#3B82F6', '#A855F7', '#6B7280', '#FFFFFF'
  ]
  if (val === 220) return [colors[2], colors[2], colors[1], '#D4AF37'] // Red, Red, Brown, Gold
  if (val === 10000 || val === 10) return [colors[1], colors[0], colors[3], '#D4AF37'] // Brown, Black, Orange, Gold
  if (val === 1000) return [colors[1], colors[0], colors[2], '#D4AF37'] // Brown, Black, Red, Gold
  if (val === 330) return [colors[3], colors[3], colors[1], '#D4AF37'] // Orange, Orange, Brown, Gold
  if (val === 470) return [colors[4], colors[7], colors[1], '#D4AF37'] // Yellow, Violet, Brown, Gold
  return [colors[2], colors[2], colors[1], '#D4AF37']
}

// Definitions of supported hardware parts
const COMPONENT_METAS: Record<string, ComponentMeta> = {
  'wokwi-esp32-devkit-v1': {
    width: 170,
    height: 310,
    title: 'ESP32 DevKit V1 (38-pin)',
    pins: [
      // Left header pins (relX = 8, spacing = 14)
      { name: '3V3', relX: 8, relY: 40, label: '3V3', type: 'power' },
      { name: 'EN', relX: 8, relY: 54, label: 'EN', type: 'digital' },
      { name: 'VP', relX: 8, relY: 68, label: 'VP/36', type: 'analog' },
      { name: 'VN', relX: 8, relY: 82, label: 'VN/39', type: 'analog' },
      { name: 'GPIO34', relX: 8, relY: 96, label: 'D34', type: 'digital' },
      { name: 'GPIO35', relX: 8, relY: 110, label: 'D35', type: 'digital' },
      { name: 'GPIO32', relX: 8, relY: 124, label: 'D32', type: 'analog' },
      { name: 'GPIO33', relX: 8, relY: 138, label: 'D33', type: 'analog' },
      { name: 'GPIO25', relX: 8, relY: 152, label: 'D25', type: 'analog' },
      { name: 'GPIO26', relX: 8, relY: 166, label: 'D26', type: 'analog' },
      { name: 'GPIO27', relX: 8, relY: 180, label: 'D27', type: 'digital' },
      { name: 'GPIO14', relX: 8, relY: 194, label: 'D14', type: 'digital' },
      { name: 'GPIO12', relX: 8, relY: 208, label: 'D12', type: 'digital' },
      { name: 'GPIO13', relX: 8, relY: 222, label: 'D13', type: 'digital' },
      { name: 'GND.1', relX: 8, relY: 236, label: 'GND', type: 'ground' },
      { name: 'GND', relX: 8, relY: 236, label: 'GND', type: 'ground' },
      { name: 'GPIO23', relX: 8, relY: 250, label: 'D23', type: 'digital' },
      { name: 'GPIO22', relX: 8, relY: 264, label: 'D22', type: 'digital' },
      { name: 'TX0', relX: 8, relY: 278, label: 'TX0', type: 'digital' },
      { name: 'RX0', relX: 8, relY: 292, label: 'RX0', type: 'digital' },

      // Right header pins (relX = 162, spacing = 14)
      { name: 'VIN', relX: 162, relY: 40, label: 'VIN', type: 'power' },
      { name: 'GND.2', relX: 162, relY: 54, label: 'GND', type: 'ground' },
      { name: 'GPIO13_R', relX: 162, relY: 68, label: 'D13', type: 'digital' },
      { name: 'GPIO12_R', relX: 162, relY: 82, label: 'D12', type: 'digital' },
      { name: 'GPIO14_R', relX: 162, relY: 96, label: 'D14', type: 'digital' },
      { name: 'GPIO27_R', relX: 162, relY: 110, label: 'D27', type: 'digital' },
      { name: 'GPIO26_R', relX: 162, relY: 124, label: 'D26', type: 'digital' },
      { name: 'GPIO25_R', relX: 162, relY: 138, label: 'D25', type: 'digital' },
      { name: 'GPIO33_R', relX: 162, relY: 152, label: 'D33', type: 'digital' },
      { name: 'GPIO32_R', relX: 162, relY: 166, label: 'D32', type: 'digital' },
      { name: 'GPIO15', relX: 162, relY: 180, label: 'D15', type: 'digital' },
      { name: 'GPIO2', relX: 162, relY: 194, label: 'D2', type: 'digital' },
      { name: 'GPIO4', relX: 162, relY: 208, label: 'D4', type: 'digital' },
      { name: 'GPIO16', relX: 162, relY: 222, label: 'D16', type: 'digital' },
      { name: 'GPIO17', relX: 162, relY: 236, label: 'D17', type: 'digital' },
      { name: 'GPIO5', relX: 162, relY: 250, label: 'D5', type: 'digital' },
      { name: 'GPIO18', relX: 162, relY: 264, label: 'D18', type: 'digital' },
      { name: 'GPIO19', relX: 162, relY: 278, label: 'D19', type: 'digital' },
      { name: 'GPIO21', relX: 162, relY: 292, label: 'D21', type: 'digital' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* PCB Board */}
        <rect
          x={0} y={0} width={170} height={310} rx={8}
          fill="#131b2e" stroke={isSelected ? '#22d3ee' : '#334155'}
          strokeWidth={isSelected ? 3 : 1.5}
        />
        {/* Mounting Holes */}
        <circle cx={14} cy={14} r={4.5} fill="#090d16" stroke="#475569" strokeWidth={1} />
        <circle cx={156} cy={14} r={4.5} fill="#090d16" stroke="#475569" strokeWidth={1} />
        <circle cx={14} cy={296} r={4.5} fill="#090d16" stroke="#475569" strokeWidth={1} />
        <circle cx={156} cy={296} r={4.5} fill="#090d16" stroke="#475569" strokeWidth={1} />

        {/* Micro-USB Port */}
        <rect x={65} y={-4} width={40} height={20} rx={3} fill="#94a3b8" stroke="#cbd5e1" strokeWidth={1} />
        <rect x={72} y={2} width={26} height={10} rx={2} fill="#334155" />

        {/* ESP-WROOM-32 RF Shield */}
        <rect x={28} y={34} width={114} height={130} rx={4} fill="#273549" stroke="#64748b" strokeWidth={1.5} />
        {/* Antenna copper trace area */}
        <rect x={36} y={40} width={98} height={26} rx={2} fill="#854d0e" stroke="#ca8a04" strokeWidth={1} />
        <path d="M 44,53 H 126 M 48,46 V 60 M 64,46 V 60 M 80,46 V 60 M 96,46 V 60 M 112,46 V 60" stroke="#fef08a" strokeWidth={1.2} fill="none" />
        <text x={85} y={96} fill="#e2e8f0" fontSize={11} fontWeight="bold" fontFamily="monospace" textAnchor="middle">ESP-WROOM-32</text>
        <text x={85} y={112} fill="#94a3b8" fontSize={8} fontFamily="monospace" textAnchor="middle">Wi-Fi + BT SoC</text>
        <text x={85} y={126} fill="#06b6d4" fontSize={7} fontFamily="monospace" textAnchor="middle">CE 1313</text>

        {/* Tactile Buttons: EN & BOOT */}
        <rect x={24} y={268} width={22} height={22} rx={3} fill="#334155" stroke="#64748b" strokeWidth={1} />
        <circle cx={35} cy={279} r={6} fill="#cbd5e1" />
        <text x={35} y={263} fill="#94a3b8" fontSize={7} fontFamily="monospace" textAnchor="middle">EN</text>

        <rect x={124} y={268} width={22} height={22} rx={3} fill="#334155" stroke="#64748b" strokeWidth={1} />
        <circle cx={135} cy={279} r={6} fill="#cbd5e1" />
        <text x={135} y={263} fill="#94a3b8" fontSize={7} fontFamily="monospace" textAnchor="middle">BOOT</text>

        {/* Status LEDs */}
        <rect x={66} y={274} width={8} height={12} rx={1} fill="#dc2626" />
        <rect x={96} y={274} width={8} height={12} rx={1} fill="#2563eb" />
        <text x={70} y={268} fill="#ef4444" fontSize={6} fontFamily="monospace" textAnchor="middle">PWR</text>
        <text x={100} y={268} fill="#60a5fa" fontSize={6} fontFamily="monospace" textAnchor="middle">D2</text>

        {/* USB-UART Bridge IC */}
        <rect x={66} y={190} width={38} height={32} rx={2} fill="#0f172a" stroke="#475569" strokeWidth={1} />
        <text x={85} y={208} fill="#64748b" fontSize={7} fontFamily="monospace" textAnchor="middle">CP2102</text>

        {/* Brand label */}
        <text x={85} y={242} fill="#38bdf8" fontSize={10} fontWeight="bold" fontFamily="monospace" textAnchor="middle">ESP32 DevKit</text>
      </g>
    ),
  },

  'wokwi-dht22': {
    width: 90,
    height: 120,
    title: 'DHT22 Temp & Humidity Sensor',
    pins: [
      { name: 'VCC', relX: 18, relY: 116, label: 'VCC', type: 'power' },
      { name: 'SDA', relX: 36, relY: 116, label: 'SDA', type: 'signal' },
      { name: 'NC',  relX: 54, relY: 116, label: 'NC',  type: 'signal' },
      { name: 'GND', relX: 72, relY: 116, label: 'GND', type: 'ground' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* Sensor Body */}
        <rect
          x={0} y={0} width={90} height={105} rx={6}
          fill="#f1f5f9" stroke={isSelected ? '#22d3ee' : '#94a3b8'}
          strokeWidth={isSelected ? 3 : 1.5}
        />
        {/* Grill vents */}
        {[18, 30, 42, 54, 66].map((gy, i) => (
          <rect key={i} x={15} y={gy} width={60} height={6} rx={2} fill="#cbd5e1" />
        ))}
        <text x={45} y={88} fill="#334155" fontSize={11} fontWeight="bold" fontFamily="monospace" textAnchor="middle">DHT22</text>
        <text x={45} y={98} fill="#64748b" fontSize={7} fontFamily="monospace" textAnchor="middle">AM2302</text>
        {/* Pins protruding below */}
        {[18, 36, 54, 72].map((px, i) => (
          <line key={i} x1={px} y1={105} x2={px} y2={116} stroke="#cbd5e1" strokeWidth={3} strokeLinecap="round" />
        ))}
      </g>
    ),
  },

  'wokwi-hc-sr04': {
    width: 140,
    height: 80,
    title: 'HC-SR04 Ultrasonic Distance Sensor',
    pins: [
      { name: 'VCC',  relX: 38, relY: 76, label: 'VCC',  type: 'power' },
      { name: 'TRIG', relX: 56, relY: 76, label: 'TRIG', type: 'digital' },
      { name: 'ECHO', relX: 74, relY: 76, label: 'ECHO', type: 'digital' },
      { name: 'GND',  relX: 92, relY: 76, label: 'GND',  type: 'ground' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* Blue PCB */}
        <rect
          x={0} y={0} width={140} height={66} rx={4}
          fill="#1d4ed8" stroke={isSelected ? '#22d3ee' : '#60a5fa'}
          strokeWidth={isSelected ? 3 : 1.5}
        />
        {/* Transmitter Transducer "T" */}
        <circle cx={35} cy={33} r={24} fill="#e2e8f0" stroke="#94a3b8" strokeWidth={2} />
        <circle cx={35} cy={33} r={17} fill="#cbd5e1" />
        <circle cx={35} cy={33} r={8} fill="#64748b" />
        <text x={35} y={37} fill="#ffffff" fontSize={10} fontWeight="bold" fontFamily="monospace" textAnchor="middle">T</text>

        {/* Receiver Transducer "R" */}
        <circle cx={105} cy={33} r={24} fill="#e2e8f0" stroke="#94a3b8" strokeWidth={2} />
        <circle cx={105} cy={33} r={17} fill="#cbd5e1" />
        <circle cx={105} cy={33} r={8} fill="#64748b" />
        <text x={105} y={37} fill="#ffffff" fontSize={10} fontWeight="bold" fontFamily="monospace" textAnchor="middle">R</text>

        {/* Quartz Crystal */}
        <rect x={63} y={14} width={14} height={24} rx={3} fill="#94a3b8" stroke="#cbd5e1" />
        <text x={70} y={50} fill="#bfdbfe" fontSize={8} fontWeight="bold" fontFamily="monospace" textAnchor="middle">HC-SR04</text>

        {/* Protruding Pins */}
        {[38, 56, 74, 92].map((px, i) => (
          <line key={i} x1={px} y1={66} x2={px} y2={76} stroke="#e2e8f0" strokeWidth={3} strokeLinecap="round" />
        ))}
      </g>
    ),
  },

  'wokwi-led': {
    width: 50,
    height: 75,
    title: 'LED Indicator',
    pins: [
      { name: 'A', relX: 18, relY: 72, label: 'A (+)', type: 'digital' },
      { name: 'K', relX: 32, relY: 72, label: 'K (-)', type: 'ground' },
    ],
    render: (part, isSelected) => {
      const color = part.attrs?.color || 'red'
      const colorMap: Record<string, { dome: string; glow: string }> = {
        red: { dome: '#ef4444', glow: '#f87171' },
        green: { dome: '#22c55e', glow: '#4ade80' },
        blue: { dome: '#3b82f6', glow: '#60a5fa' },
        yellow: { dome: '#eab308', glow: '#fde047' },
      }
      const c = colorMap[color] || colorMap.red
      return (
        <g>
          {/* LED Plastic Dome */}
          <path
            d="M 12,38 C 12,18 20,8 25,8 C 30,8 38,18 38,38 Z"
            fill={c.dome} stroke={isSelected ? '#22d3ee' : c.glow}
            strokeWidth={isSelected ? 3 : 1.5}
            fillOpacity={0.88}
          />
          {/* Highlight shine */}
          <path d="M 19,16 C 22,12 25,12 27,15" stroke="#ffffff" strokeWidth={2} strokeLinecap="round" fill="none" opacity={0.6} />
          {/* Base Rim */}
          <rect x={10} y={38} width={30} height={6} rx={1} fill={c.dome} stroke="#7f1d1d" strokeWidth={1} />
          {/* Flat edge on Cathode */}
          <line x1={38} y1={38} x2={38} y2={44} stroke="#450a0a" strokeWidth={2} />
          {/* Anode & Cathode Legs */}
          <line x1={18} y1={44} x2={18} y2={72} stroke="#94a3b8" strokeWidth={2.5} strokeLinecap="round" />
          <line x1={32} y1={44} x2={32} y2={72} stroke="#94a3b8" strokeWidth={2.5} strokeLinecap="round" />
          <text x={25} y={56} fill="#94a3b8" fontSize={7} fontFamily="monospace" textAnchor="middle">
            {color.toUpperCase()}
          </text>
        </g>
      )
    },
  },

  'wokwi-resistor': {
    width: 90,
    height: 40,
    title: 'Through-Hole Resistor',
    pins: [
      { name: '1', relX: 6, relY: 20, label: '1', type: 'signal' },
      { name: '2', relX: 84, relY: 20, label: '2', type: 'signal' },
    ],
    render: (part, isSelected) => {
      const bands = getResistorBands(part.attrs?.value)
      return (
        <g>
          {/* Left Lead */}
          <line x1={6} y1={20} x2={22} y2={20} stroke="#94a3b8" strokeWidth={2.5} strokeLinecap="round" />
          {/* Right Lead */}
          <line x1={68} y1={20} x2={84} y2={20} stroke="#94a3b8" strokeWidth={2.5} strokeLinecap="round" />
          {/* Resistor Ceramic Body */}
          <rect
            x={22} y={10} width={46} height={20} rx={5}
            fill="#fde68a" stroke={isSelected ? '#22d3ee' : '#d97706'}
            strokeWidth={isSelected ? 2.5 : 1.5}
          />
          {/* 4 Color Bands */}
          <rect x={28} y={10} width={4} height={20} fill={bands[0]} />
          <rect x={36} y={10} width={4} height={20} fill={bands[1]} />
          <rect x={44} y={10} width={4} height={20} fill={bands[2]} />
          <rect x={56} y={10} width={4} height={20} fill={bands[3]} />
          {/* Label value */}
          <text x={45} y={38} fill="#d97706" fontSize={8} fontWeight="bold" fontFamily="monospace" textAnchor="middle">
            {part.attrs?.value || '220'}Ω
          </text>
        </g>
      )
    },
  },

  'wokwi-buzzer': {
    width: 70,
    height: 75,
    title: '5V Active Buzzer',
    pins: [
      { name: '1', relX: 25, relY: 70, label: '+ / VCC', type: 'digital' },
      { name: '+', relX: 25, relY: 70, label: '+ / VCC', type: 'digital' },
      { name: '2', relX: 45, relY: 70, label: '- / GND', type: 'ground' },
      { name: '-', relX: 45, relY: 70, label: '- / GND', type: 'ground' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* Cylindrical casing */}
        <circle
          cx={35} cy={35} r={28}
          fill="#1e293b" stroke={isSelected ? '#22d3ee' : '#475569'}
          strokeWidth={isSelected ? 3 : 2}
        />
        {/* Top Sound Aperture */}
        <circle cx={35} cy={35} r={8} fill="#020617" stroke="#64748b" strokeWidth={1} />
        {/* Polarity label */}
        <text x={24} y={24} fill="#ef4444" fontSize={14} fontWeight="bold" textAnchor="middle">+</text>
        <text x={35} y={55} fill="#94a3b8" fontSize={8} fontFamily="monospace" textAnchor="middle">BUZZER</text>
        {/* Leads */}
        <line x1={25} y1={63} x2={25} y2={70} stroke="#94a3b8" strokeWidth={3} strokeLinecap="round" />
        <line x1={45} y1={63} x2={45} y2={70} stroke="#94a3b8" strokeWidth={3} strokeLinecap="round" />
      </g>
    ),
  },

  'wokwi-pushbutton': {
    width: 60,
    height: 60,
    title: 'Tactile Push Button',
    pins: [
      { name: '1l', relX: 6, relY: 18, label: '1L', type: 'digital' },
      { name: '1r', relX: 54, relY: 18, label: '1R', type: 'digital' },
      { name: '2l', relX: 6, relY: 42, label: '2L', type: 'ground' },
      { name: '2r', relX: 54, relY: 42, label: '2R', type: 'ground' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* Switch Base */}
        <rect
          x={10} y={10} width={40} height={40} rx={4}
          fill="#1e293b" stroke={isSelected ? '#22d3ee' : '#475569'}
          strokeWidth={isSelected ? 2.5 : 1.5}
        />
        {/* Metallic Corner Brackets */}
        <rect x={12} y={12} width={6} height={6} fill="#94a3b8" />
        <rect x={42} y={12} width={6} height={6} fill="#94a3b8" />
        <rect x={12} y={42} width={6} height={6} fill="#94a3b8" />
        <rect x={42} y={42} width={6} height={6} fill="#94a3b8" />
        {/* Tactile Button Cap */}
        <circle cx={30} cy={30} r={12} fill="#334155" stroke="#64748b" strokeWidth={1.5} />
        <circle cx={30} cy={30} r={8} fill="#475569" />
        {/* Terminal legs */}
        <line x1={6} y1={18} x2={10} y2={18} stroke="#94a3b8" strokeWidth={2.5} />
        <line x1={50} y1={18} x2={54} y2={18} stroke="#94a3b8" strokeWidth={2.5} />
        <line x1={6} y1={42} x2={10} y2={42} stroke="#94a3b8" strokeWidth={2.5} />
        <line x1={50} y1={42} x2={54} y2={42} stroke="#94a3b8" strokeWidth={2.5} />
      </g>
    ),
  },

  'wokwi-potentiometer': {
    width: 70,
    height: 80,
    title: '10kΩ Rotary Potentiometer',
    pins: [
      { name: 'GND', relX: 18, relY: 76, label: 'GND', type: 'ground' },
      { name: 'SIG', relX: 35, relY: 76, label: 'SIG', type: 'analog' },
      { name: 'VCC', relX: 52, relY: 76, label: 'VCC', type: 'power' },
    ],
    render: (part, isSelected) => (
      <g>
        {/* Metal Body */}
        <rect
          x={10} y={10} width={50} height={52} rx={6}
          fill="#0284c7" stroke={isSelected ? '#22d3ee' : '#38bdf8'}
          strokeWidth={isSelected ? 3 : 1.5}
        />
        {/* Rotary Dial Knob */}
        <circle cx={35} cy={34} r={18} fill="#0f172a" stroke="#cbd5e1" strokeWidth={2} />
        <circle cx={35} cy={34} r={12} fill="#334155" />
        {/* Pointer Indicator Line */}
        <line x1={35} y1={34} x2={35} y2={22} stroke="#f8fafc" strokeWidth={2} strokeLinecap="round" />
        <text x={35} y={58} fill="#f0f9ff" fontSize={7} fontWeight="bold" fontFamily="monospace" textAnchor="middle">10k POT</text>
        {/* Terminal Pins */}
        <line x1={18} y1={62} x2={18} y2={76} stroke="#cbd5e1" strokeWidth={2.5} strokeLinecap="round" />
        <line x1={35} y1={62} x2={35} y2={76} stroke="#cbd5e1" strokeWidth={2.5} strokeLinecap="round" />
        <line x1={52} y1={62} x2={52} y2={76} stroke="#cbd5e1" strokeWidth={2.5} strokeLinecap="round" />
      </g>
    ),
  },
}

// Fallback generic component
const GENERIC_META: ComponentMeta = {
  width: 100,
  height: 70,
  title: 'Hardware Component',
  pins: [
    { name: 'VCC', relX: 20, relY: 66, label: 'VCC', type: 'power' },
    { name: 'SIG', relX: 50, relY: 66, label: 'SIG', type: 'signal' },
    { name: 'GND', relX: 80, relY: 66, label: 'GND', type: 'ground' },
  ],
  render: (part, isSelected) => (
    <g>
      <rect
        x={0} y={0} width={100} height={60} rx={6}
        fill="#1e293b" stroke={isSelected ? '#22d3ee' : '#475569'}
        strokeWidth={isSelected ? 2.5 : 1.5}
      />
      <text x={50} y={30} fill="#f8fafc" fontSize={10} fontWeight="bold" fontFamily="monospace" textAnchor="middle">
        {part.id}
      </text>
      <text x={50} y={45} fill="#94a3b8" fontSize={8} fontFamily="monospace" textAnchor="middle">
        {part.type.replace('wokwi-', '')}
      </text>
      <line x1={20} y1={60} x2={20} y2={66} stroke="#94a3b8" strokeWidth={2} />
      <line x1={50} y1={60} x2={50} y2={66} stroke="#94a3b8" strokeWidth={2} />
      <line x1={80} y1={60} x2={80} y2={66} stroke="#94a3b8" strokeWidth={2} />
    </g>
  ),
}

export function CircuitEditor({
  diagram,
  pinAssignments = [],
  onPartSelect,
  readOnly = false,
}: CircuitEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Canvas Viewport transform (zoom & pan)
  const [zoom, setZoom] = useState(1.0)
  const [pan, setPan] = useState({ x: 80, y: 50 })
  const [isPanning, setIsPanning] = useState(false)
  const panStartRef = useRef({ x: 0, y: 0 })

  // Component Positions State (allows real-time dragging & moving)
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({})
  const [draggingPartId, setDraggingPartId] = useState<string | null>(null)
  const dragOffsetRef = useRef({ x: 0, y: 0 })

  // Interactive Selection State
  const [selectedPartId, setSelectedPartId] = useState<string | null>(null)
  const [hoveredPartId, setHoveredPartId] = useState<string | null>(null)
  const [selectedConnectionIdx, setSelectedConnectionIdx] = useState<number | null>(null)
  const [hoveredConnectionIdx, setHoveredConnectionIdx] = useState<number | null>(null)

  // Initialize and update positions from diagram.parts with readable layout
  useEffect(() => {
    const posMap: Record<string, { x: number; y: number }> = {}
    let nonMcuIndex = 0

    diagram.parts.forEach((p) => {
      // Use existing top/left if set and non-zero
      if (p.left !== undefined && p.top !== undefined && (p.left !== 0 || p.top !== 0)) {
        posMap[p.id] = { x: p.left, y: p.top }
      } else {
        // Auto-layout: Place MCU on left, sensors/actuators spaced nicely on right
        const isEsp = p.type.includes('esp32') || p.type.includes('uno')
        if (isEsp) {
          posMap[p.id] = { x: 50, y: 40 }
        } else {
          const col = Math.floor(nonMcuIndex / 2)
          const row = nonMcuIndex % 2
          posMap[p.id] = {
            x: 320 + col * 180,
            y: 40 + row * 160,
          }
          nonMcuIndex++
        }
      }
    })
    setPositions(posMap)
  }, [diagram])

  // Helper to find exact absolute (x, y) coordinates for a part's pin
  const getPinCoordinate = useCallback(
    (partId: string, pinName: string): { x: number; y: number } | null => {
      const part = diagram.parts.find((p) => p.id === partId)
      if (!part) return null

      const pos = positions[partId] || { x: part.left || 0, y: part.top || 0 }
      const meta = COMPONENT_METAS[part.type] || GENERIC_META

      // Find matching pin by exact name, alias, or case-insensitive
      const cleanTarget = pinName.trim().toUpperCase()
      let pin = meta.pins.find((p) => p.name.toUpperCase() === cleanTarget)

      if (!pin) {
        // Try common aliases: e.g. "GND.1" -> "GND", "+" -> "1", "-" -> "2"
        const baseName = cleanTarget.split('.')[0]
        pin = meta.pins.find((p) => p.name.toUpperCase() === baseName)
      }
      if (!pin) {
        // Fallback to center edge
        return { x: pos.x + meta.width / 2, y: pos.y + meta.height }
      }

      return { x: pos.x + pin.relX, y: pos.y + pin.relY }
    },
    [diagram.parts, positions]
  )

  // Zoom handlers
  const handleZoomIn = () => setZoom((z) => Math.min(z * 1.25, 2.8))
  const handleZoomOut = () => setZoom((z) => Math.max(z / 1.25, 0.4))
  const handleResetView = () => {
    setZoom(1.0)
    setPan({ x: 80, y: 50 })
  }

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault()
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9
    setZoom((z) => Math.max(0.4, Math.min(2.8, z * zoomFactor)))
  }

  // Canvas Pan Handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    // If click is on canvas background, start pan
    if (e.target === containerRef.current || (e.target as HTMLElement).tagName === 'svg') {
      setIsPanning(true)
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      })
    } else if (draggingPartId && !readOnly) {
      // Dragging component
      const currentPos = positions[draggingPartId] || { x: 0, y: 0 }
      const newX = Math.round((e.clientX - pan.x) / zoom - dragOffsetRef.current.x)
      const newY = Math.round((e.clientY - pan.y) / zoom - dragOffsetRef.current.y)
      setPositions((prev) => ({
        ...prev,
        [draggingPartId]: { x: newX, y: newY },
      }))
    }
  }

  const handleMouseUp = () => {
    setIsPanning(false)
    setDraggingPartId(null)
  }

  // Part Drag start
  const handlePartMouseDown = (partId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedPartId(partId)
    setSelectedConnectionIdx(null)
    if (onPartSelect) onPartSelect(partId)

    if (readOnly) return

    const pos = positions[partId] || { x: 0, y: 0 }
    const mouseCanvasX = (e.clientX - pan.x) / zoom
    const mouseCanvasY = (e.clientY - pan.y) / zoom
    dragOffsetRef.current = {
      x: mouseCanvasX - pos.x,
      y: mouseCanvasY - pos.y,
    }
    setDraggingPartId(partId)
  }

  // Wire path generator between two endpoints with smooth cubic Bezier
  const connectionsWithPaths = useMemo(() => {
    return diagram.connections.map((c, idx) => {
      const fromStr = c[0] || ''
      const toStr = c[1] || ''
      const color = c[2] || '#22d3ee'

      const [fromPart, fromPin] = fromStr.split(':')
      const [toPart, toPin] = toStr.split(':')

      const start = getPinCoordinate(fromPart, fromPin)
      const end = getPinCoordinate(toPart, toPin)

      let pathData = ''
      if (start && end) {
        const dx = Math.abs(end.x - start.x)
        const dy = Math.abs(end.y - start.y)
        const controlOffset = Math.max(40, Math.min(160, (dx + dy) * 0.35))

        // Create elegant, non-intersecting curved route
        pathData = `M ${start.x},${start.y} C ${start.x + (end.x > start.x ? controlOffset : -controlOffset)},${start.y} ${end.x - (end.x > start.x ? controlOffset : -controlOffset)},${end.y} ${end.x},${end.y}`
      }

      return {
        idx,
        fromStr,
        toStr,
        fromPart,
        fromPin,
        toPart,
        toPin,
        color,
        start,
        end,
        pathData,
      }
    })
  }, [diagram.connections, getPinCoordinate])

  // Selected Part metadata for the inspector drawer
  const selectedPart = diagram.parts.find((p) => p.id === selectedPartId)
  const selectedMeta = selectedPart ? COMPONENT_METAS[selectedPart.type] || GENERIC_META : null

  // Find pins and connections relevant to the selected part
  const partConnections = useMemo(() => {
    if (!selectedPartId) return []
    return connectionsWithPaths.filter(
      (c) => c.fromPart === selectedPartId || c.toPart === selectedPartId
    )
  }, [selectedPartId, connectionsWithPaths])

  return (
    <div className="relative w-full h-[620px] bg-gray-950 rounded-xl border border-gray-800 overflow-hidden flex flex-col select-none">
      {/* Top Toolbar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-gray-900/90 border-b border-gray-800 z-10">
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold text-gray-300 flex items-center gap-1.5 uppercase tracking-wider">
            <Zap className="w-4 h-4 text-cyan-400" />
            Wokwi Circuit Canvas
          </span>
          <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/70 border border-cyan-800/80 px-2 py-0.5 rounded">
            {diagram.parts.length} Components
          </span>
          <span className="text-[11px] font-mono text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
            {diagram.connections.length} Electrical Wires
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={handleResetView}
            title="Reset View"
            className="p-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 hover:text-white transition"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <div className="w-px h-5 bg-gray-800 mx-1" />
          <span className="text-xs text-gray-500 font-mono px-1">
            {Math.round(zoom * 100)}%
          </span>
        </div>
      </div>

      {/* Main Interactive SVG Canvas */}
      <div
        ref={containerRef}
        className="flex-1 w-full h-full relative cursor-grab active:cursor-grabbing overflow-hidden"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
      >
        <svg
          className="w-full h-full"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(34, 211, 238, 0.08) 1px, transparent 1px)',
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
          }}
        >
          <defs>
            {/* Wire Glow Filter */}
            <filter id="wire-glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            {/* Selected Wire Glow */}
            <filter id="active-glow" x="-30%" y="-30%" width="160%" height="160%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Root Transform Group for Pan & Zoom */}
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* 1. Electrical Wires */}
            {connectionsWithPaths.map((c) => {
              if (!c.pathData) return null
              const isSelected = selectedConnectionIdx === c.idx
              const isHovered = hoveredConnectionIdx === c.idx
              const isPartActive =
                selectedPartId &&
                (c.fromPart === selectedPartId || c.toPart === selectedPartId)

              const strokeWidth = isSelected || isHovered ? 4.5 : isPartActive ? 3.2 : 2.2
              const strokeColor =
                isSelected || isHovered ? '#38bdf8' : isPartActive ? c.color : c.color

              return (
                <g key={c.idx} className="cursor-pointer">
                  {/* Invisible wide hit area for easy clicking */}
                  <path
                    d={c.pathData}
                    fill="none"
                    stroke="transparent"
                    strokeWidth={16}
                    onMouseEnter={() => setHoveredConnectionIdx(c.idx)}
                    onMouseLeave={() => setHoveredConnectionIdx(null)}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedConnectionIdx(c.idx)
                    }}
                  />
                  {/* Glowing backdrop when active */}
                  {(isSelected || isHovered || isPartActive) && (
                    <path
                      d={c.pathData}
                      fill="none"
                      stroke={c.color}
                      strokeWidth={strokeWidth + 4}
                      strokeOpacity={0.4}
                      filter="url(#wire-glow)"
                    />
                  )}
                  {/* Main Wire line */}
                  <path
                    d={c.pathData}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    filter={isSelected ? 'url(#active-glow)' : undefined}
                    onMouseEnter={() => setHoveredConnectionIdx(c.idx)}
                    onMouseLeave={() => setHoveredConnectionIdx(null)}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedConnectionIdx(c.idx)
                    }}
                  />
                  {/* Wire start/end solder joints */}
                  {c.start && (
                    <circle
                      cx={c.start.x}
                      cy={c.start.y}
                      r={isSelected ? 4.5 : 3}
                      fill={strokeColor}
                      stroke="#0f172a"
                      strokeWidth={1}
                    />
                  )}
                  {c.end && (
                    <circle
                      cx={c.end.x}
                      cy={c.end.y}
                      r={isSelected ? 4.5 : 3}
                      fill={strokeColor}
                      stroke="#0f172a"
                      strokeWidth={1}
                    />
                  )}
                </g>
              )
            })}

            {/* 2. Components */}
            {diagram.parts.map((part) => {
              const pos = positions[part.id] || { x: part.left || 0, y: part.top || 0 }
              const meta = COMPONENT_METAS[part.type] || GENERIC_META
              const isSelected = selectedPartId === part.id
              const isHovered = hoveredPartId === part.id

              return (
                <g
                  key={part.id}
                  transform={`translate(${pos.x}, ${pos.y})`}
                  className="cursor-move"
                  onMouseDown={(e) => handlePartMouseDown(part.id, e)}
                  onMouseEnter={() => setHoveredPartId(part.id)}
                  onMouseLeave={() => setHoveredPartId(null)}
                >
                  {/* Selection highlight bounding halo */}
                  {isSelected && (
                    <rect
                      x={-6}
                      y={-6}
                      width={meta.width + 12}
                      height={meta.height + 12}
                      rx={10}
                      fill="none"
                      stroke="#22d3ee"
                      strokeWidth={2}
                      strokeDasharray="6,4"
                      className="animate-pulse"
                    />
                  )}

                  {/* Component Custom Graphic */}
                  {meta.render(part, isSelected, isHovered)}

                  {/* Component Header Label Tag */}
                  <g transform={`translate(${meta.width / 2}, -12)`}>
                    <rect
                      x={-35}
                      y={-12}
                      width={70}
                      height={18}
                      rx={4}
                      fill="#0f172a"
                      stroke={isSelected ? '#22d3ee' : '#334155'}
                      strokeWidth={1}
                    />
                    <text
                      x={0}
                      y={0}
                      fill="#e2e8f0"
                      fontSize={9}
                      fontWeight="bold"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {part.id}
                    </text>
                  </g>

                  {/* Pin Terminals (Interactive Hover Targets & Visual Markers) */}
                  {meta.pins.map((pin) => {
                    // Check if pin is connected to any wire
                    const isConnected = connectionsWithPaths.some(
                      (c) =>
                        (c.fromPart === part.id && c.fromPin.toUpperCase().startsWith(pin.name.toUpperCase())) ||
                        (c.toPart === part.id && c.toPin.toUpperCase().startsWith(pin.name.toUpperCase()))
                    )

                    const pinColor =
                      pin.type === 'power'
                        ? '#ef4444'
                        : pin.type === 'ground'
                        ? '#475569'
                        : pin.type === 'analog'
                        ? '#eab308'
                        : '#38bdf8'

                    return (
                      <g key={pin.name} transform={`translate(${pin.relX}, ${pin.relY})`}>
                        <circle
                          r={isConnected ? 4 : 2.5}
                          fill={pinColor}
                          stroke="#020617"
                          strokeWidth={1}
                        />
                        {/* Pin tooltip on hover */}
                        {isHovered && (
                          <text
                            x={pin.relX > meta.width / 2 ? 8 : -8}
                            y={3}
                            fill="#94a3b8"
                            fontSize={7}
                            fontFamily="monospace"
                            textAnchor={pin.relX > meta.width / 2 ? 'start' : 'end'}
                          >
                            {pin.label || pin.name}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </g>
              )
            })}
          </g>
        </svg>

        {/* Selected Connection Info Banner */}
        {selectedConnectionIdx !== null && (
          <div className="absolute top-4 left-4 bg-gray-900/95 border border-cyan-500/50 rounded-lg p-3 shadow-2xl backdrop-blur max-w-sm z-20 flex items-start justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" /> Wire Connection
              </div>
              <p className="text-xs font-mono text-white mt-1">
                <span className="text-cyan-300">
                  {connectionsWithPaths[selectedConnectionIdx]?.fromStr}
                </span>{' '}
                ↔{' '}
                <span className="text-amber-300">
                  {connectionsWithPaths[selectedConnectionIdx]?.toStr}
                </span>
              </p>
              <div className="flex items-center gap-2 mt-1.5 text-[11px] text-gray-400">
                <span>Color: {connectionsWithPaths[selectedConnectionIdx]?.color}</span>
              </div>
            </div>
            <button
              onClick={() => setSelectedConnectionIdx(null)}
              className="text-gray-500 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Component Inspector Drawer (Right Side) */}
        {selectedPart && selectedMeta && (
          <div className="absolute top-4 right-4 w-72 bg-gray-900/95 border border-gray-700/80 rounded-xl p-4 shadow-2xl backdrop-blur z-20 space-y-3">
            <div className="flex items-start justify-between pb-2 border-b border-gray-800">
              <div>
                <span className="text-[10px] uppercase font-bold text-cyan-400 tracking-wider">
                  Component Inspector
                </span>
                <h4 className="text-sm font-bold text-white font-mono mt-0.5">
                  {selectedPart.id}
                </h4>
              </div>
              <button
                onClick={() => setSelectedPartId(null)}
                className="text-gray-500 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Part Type:</span>
                <span className="text-gray-300 font-mono text-[11px]">
                  {selectedPart.type.replace('wokwi-', '')}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Full Name:</span>
                <span className="text-gray-200">{selectedMeta.title}</span>
              </div>
              {selectedPart.attrs && Object.keys(selectedPart.attrs).length > 0 && (
                <div className="pt-1">
                  <span className="text-gray-500">Attributes:</span>
                  <div className="bg-gray-950 p-1.5 rounded mt-0.5 text-[11px] font-mono text-cyan-300">
                    {JSON.stringify(selectedPart.attrs)}
                  </div>
                </div>
              )}
            </div>

            {/* Active Pin Connections */}
            <div className="pt-2 border-t border-gray-800">
              <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                Active Connections ({partConnections.length})
              </h5>
              {partConnections.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No external wires connected.</p>
              ) : (
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {partConnections.map((c) => {
                    const localPin =
                      c.fromPart === selectedPartId ? c.fromPin : c.toPin
                    const remoteStr =
                      c.fromPart === selectedPartId ? c.toStr : c.fromStr
                    return (
                      <div
                        key={c.idx}
                        className="p-1.5 bg-gray-950 rounded border border-gray-800 text-[11px] font-mono flex items-center justify-between"
                      >
                        <span className="text-cyan-400">{localPin}</span>
                        <span className="text-gray-500">→</span>
                        <span className="text-amber-300 truncate max-w-[110px]">{remoteStr}</span>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Firmware Pin Mapping */}
            {pinAssignments.filter((pa) => pa.component_instance === selectedPart.id).length >
              0 && (
              <div className="pt-2 border-t border-gray-800">
                <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                  Firmware GPIO Map
                </h5>
                <div className="space-y-1">
                  {pinAssignments
                    .filter((pa) => pa.component_instance === selectedPart.id)
                    .map((pa, idx) => (
                      <div
                        key={idx}
                        className="text-[11px] bg-cyan-950/40 border border-cyan-900/60 p-1.5 rounded text-gray-300 flex justify-between"
                      >
                        <span>Pin {pa.component_pin}</span>
                        <span className="font-mono font-bold text-yellow-400">
                          GPIO {pa.gpio_pin}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Bottom Helper Hint */}
        <div className="absolute bottom-2 left-4 text-[11px] text-gray-500 flex items-center gap-3 pointer-events-none">
          <span>
            <strong className="text-gray-400">Drag</strong> components to move
          </span>
          <span>•</span>
          <span>
            <strong className="text-gray-400">Scroll</strong> to zoom
          </span>
          <span>•</span>
          <span>
            <strong className="text-gray-400">Click</strong> wire or part to inspect
          </span>
        </div>
      </div>
    </div>
  )
}
