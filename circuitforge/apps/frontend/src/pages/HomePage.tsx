import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Cpu, Zap, Thermometer, Radio, Volume2, ArrowRight, Loader2 } from 'lucide-react'
import { createProject, planProject, getErrorMessage } from '../utils/api'

const EXAMPLES = [
  {
    icon: Thermometer,
    title: 'Temperature Monitor',
    text: 'Create an ESP32-based temperature monitor using a DHT22 sensor. Turn on an LED when the temperature exceeds 30 degrees Celsius.',
    color: 'text-orange-400',
  },
  {
    icon: Radio,
    title: 'Distance Warning',
    text: 'Build an ultrasonic distance sensor system with ESP32 and HC-SR04. Activate a buzzer when an object comes within 20cm.',
    color: 'text-blue-400',
  },
  {
    icon: Zap,
    title: 'LED Controller',
    text: 'Create an ESP32 project with a push button to toggle an LED. Add a potentiometer to control LED brightness via PWM.',
    color: 'text-yellow-400',
  },
  {
    icon: Volume2,
    title: 'Alert System',
    text: 'Make an ESP32 project that reads a DHT22 sensor and sounds a buzzer when temperature exceeds 35°C or humidity exceeds 80%.',
    color: 'text-red-400',
  },
]

export default function HomePage() {
  const navigate = useNavigate()
  const [request, setRequest] = useState('')
  const [loading, setLoading] = useState(false)

  const handleCreate = useCallback(async (text?: string) => {
    const req = (text ?? request).trim()
    if (!req || req.length < 10) {
      toast.error('Please describe your IoT project (at least 10 characters)')
      return
    }
    setLoading(true)
    try {
      const project = await createProject(req)
      toast.success('Project created! Starting AI planning...')
      // Immediately trigger planning
      await planProject(project.id)
      navigate(`/project/${project.id}`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [request, navigate])

  return (
    <div className="min-h-screen circuit-bg flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-cyan-600 flex items-center justify-center">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-white">CircuitForge <span className="text-cyan-400">AI</span></span>
          <div className="flex-1" />
          <a href="/setup" className="text-sm text-gray-400 hover:text-cyan-400 transition-colors">
            System Setup
          </a>
          <a href="/projects" className="text-sm text-gray-400 hover:text-cyan-400 transition-colors ml-4">
            Projects
          </a>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <div className="text-center mb-12 max-w-2xl">
          <div className="inline-flex items-center gap-2 bg-cyan-900/30 border border-cyan-800 rounded-full px-4 py-1.5 mb-6 text-sm text-cyan-400">
            <span className="w-2 h-2 rounded-full bg-cyan-400 pulse-dot inline-block" />
            Local-First · AI-Powered · Privacy Preserving
          </div>
          <h1 className="text-5xl font-bold text-white mb-4 leading-tight">
            Describe your IoT idea.<br />
            <span className="text-cyan-400">We build the circuit.</span>
          </h1>
          <p className="text-gray-400 text-lg leading-relaxed">
            From natural language to validated circuits, Arduino firmware, and Wokwi simulations —
            all locally on your machine.
          </p>
        </div>

        {/* Input */}
        <div className="w-full max-w-3xl">
          <div className="forge-card p-6 glow-cyan">
            <label className="block text-sm font-medium text-gray-400 mb-3">
              Describe your IoT project
            </label>
            <textarea
              className="forge-input resize-none text-base leading-relaxed mb-4"
              rows={4}
              value={request}
              onChange={e => setRequest(e.target.value)}
              placeholder="Create an ESP32-based temperature monitor using a DHT22 sensor. Turn on an LED when temperature exceeds 30°C..."
              disabled={loading}
              onKeyDown={e => {
                if (e.key === 'Enter' && e.metaKey) handleCreate()
              }}
            />
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-600">
                {request.length} chars · ⌘+Enter to submit
              </span>
              <button
                className="btn-primary text-base px-6 py-3"
                onClick={() => handleCreate()}
                disabled={loading || request.trim().length < 10}
              >
                {loading ? (
                  <><Loader2 className="w-5 h-5 spinner" /> Planning with AI...</>
                ) : (
                  <><Zap className="w-5 h-5" /> Build Circuit</>
                )}
              </button>
            </div>
          </div>

          {/* Examples */}
          <div className="mt-6">
            <p className="text-xs text-gray-600 mb-3 uppercase tracking-wider">Example projects</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {EXAMPLES.map(ex => (
                <button
                  key={ex.title}
                  className="text-left forge-card p-4 hover:border-gray-700 transition-all group cursor-pointer"
                  onClick={() => { setRequest(ex.text); handleCreate(ex.text) }}
                  disabled={loading}
                >
                  <div className="flex items-start gap-3">
                    <ex.icon className={`w-5 h-5 mt-0.5 ${ex.color} shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-gray-200 group-hover:text-white mb-1 flex items-center gap-1">
                        {ex.title}
                        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity ml-auto" />
                      </div>
                      <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{ex.text}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-700">
        CircuitForge AI · Local-first · No cloud AI · All inference runs on your machine
      </footer>
    </div>
  )
}
