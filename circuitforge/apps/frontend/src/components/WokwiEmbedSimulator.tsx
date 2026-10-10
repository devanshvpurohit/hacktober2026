import { useState, useEffect, useRef } from 'react'
import { Play, Square, RotateCcw, ExternalLink, Loader2, Terminal as TerminalIcon } from 'lucide-react'

interface WokwiEmbedSimulatorProps {
  diagram: any
  firmware: string
  projectName: string
  projectId: string
}

export default function WokwiEmbedSimulator({ diagram, firmware, projectName, projectId }: WokwiEmbedSimulatorProps) {
  const [isRunning, setIsRunning] = useState(false)
  const [serialOutput, setSerialOutput] = useState<string[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Create a project bundle for Wokwi
  const createWokwiProject = () => {
    const diagramJson = JSON.stringify(diagram, null, 2)
    const wokwiToml = `[wokwi]
version = 1
firmware = 'sketch.ino'
elf = '.pio/build/esp32dev/firmware.elf'
`

    return {
      'diagram.json': diagramJson,
      'sketch.ino': firmware,
      'wokwi.toml': wokwiToml,
    }
  }

  const handleStartSimulation = async () => {
    setIsLoading(true)
    setSerialOutput(['Starting simulation...', ''])
    
    try {
      // Use Wokwi's embed API
      const project = createWokwiProject()
      
      // Simulate by posting message to backend to run simulation
      const response = await fetch(`/api/projects/${projectId}/simulate`, {
        method: 'POST',
      })
      
      const result = await response.json()
      
      if (result.simulation_status === 'manual' || result.mode === 'manual') {
        setSerialOutput([
          'Wokwi CLI not available.',
          'Opening Wokwi in a new tab for simulation...',
          '',
          'You can also:',
          '1. Install Wokwi CLI from https://docs.wokwi.com/wokwi-ci/getting-started',
          '2. Or use the embedded simulator below',
        ])
        // Open Wokwi in new tab
        window.open('https://wokwi.com/projects/new/esp32', '_blank')
      } else {
        setSerialOutput([
          'Simulation started!',
          '--- Serial Output ---',
          result.stdout || 'No output',
        ])
        setIsRunning(true)
      }
    } catch (error) {
      setSerialOutput(['Error starting simulation:', String(error)])
    } finally {
      setIsLoading(false)
    }
  }

  const handleStopSimulation = () => {
    setIsRunning(false)
    setSerialOutput(prev => [...prev, '', '--- Simulation Stopped ---'])
  }

  const handleResetSimulation = () => {
    setSerialOutput([])
    setIsRunning(false)
  }

  // Create Wokwi embed URL
  const getWokwiEmbedUrl = () => {
    // Encode project data
    const projectData = encodeURIComponent(JSON.stringify({
      version: 1,
      author: 'CircuitForge AI',
      editor: 'wokwi',
      parts: diagram.parts || [],
      connections: diagram.connections || [],
    }))
    
    // For embedded simulation, we'll use a data URL approach
    return `https://wokwi.com/projects/new/esp32`
  }

  return (
    <div className="space-y-4">
      {/* Control Panel */}
      <div className="forge-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-cyan-400 mb-1">
              🔌 In-App Circuit Simulator
            </h3>
            <p className="text-sm text-gray-400">
              Test your circuit directly in the browser
            </p>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={handleStartSimulation}
              disabled={isRunning || isLoading}
              className="btn-primary text-sm flex items-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              Start
            </button>
            
            <button
              onClick={handleStopSimulation}
              disabled={!isRunning}
              className="btn-secondary text-sm flex items-center gap-2"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
            
            <button
              onClick={handleResetSimulation}
              className="btn-secondary text-sm flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </button>
            
            <a
              href={getWokwiEmbedUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-sm flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              Open in Wokwi
            </a>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
            <span className="text-gray-400">
              Status: {isRunning ? 'Running' : 'Stopped'}
            </span>
          </div>
        </div>
      </div>

      {/* Serial Monitor */}
      <div className="forge-card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-gray-900">
          <div className="flex items-center gap-2">
            <TerminalIcon className="w-4 h-4 text-cyan-400" />
            <span className="text-sm text-gray-400 font-mono">Serial Monitor</span>
          </div>
          <span className="text-xs text-gray-600">115200 baud</span>
        </div>
        
        <div className="bg-black p-4 font-mono text-xs text-green-400 h-64 overflow-y-auto">
          {serialOutput.length === 0 ? (
            <div className="text-gray-600">Waiting for simulation to start...</div>
          ) : (
            serialOutput.map((line, i) => (
              <div key={i} className="leading-relaxed">
                {line}
              </div>
            ))
          )}
          {isRunning && (
            <div className="mt-2 text-cyan-400 animate-pulse">█</div>
          )}
        </div>
      </div>

      {/* Circuit Visualization */}
      <div className="forge-card p-5">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Circuit Diagram
        </h4>
        <div className="bg-gray-900 rounded-lg p-6 min-h-[400px] flex items-center justify-center border-2 border-dashed border-gray-700">
          <div className="text-center">
            <div className="text-4xl mb-4">🔌</div>
            <p className="text-gray-400 mb-4">
              Interactive circuit visualization
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl">
              {diagram.parts?.slice(0, 8).map((part: any, i: number) => (
                <div
                  key={i}
                  className="bg-gray-800 rounded-lg p-3 border border-gray-700 hover:border-cyan-600 transition-colors"
                >
                  <div className="text-2xl mb-2">
                    {part.type.includes('led') && '💡'}
                    {part.type.includes('button') && '🔘'}
                    {part.type.includes('resistor') && '⚡'}
                    {part.type.includes('dht') && '🌡️'}
                    {part.type.includes('servo') && '⚙️'}
                    {part.type.includes('ultrasonic') && '📡'}
                    {part.type.includes('buzzer') && '🔔'}
                    {part.type.includes('lcd') && '📺'}
                    {part.type.includes('esp32') && '🖥️'}
                    {!part.type.match(/led|button|resistor|dht|servo|ultrasonic|buzzer|lcd|esp32/) && '📦'}
                  </div>
                  <div className="text-xs text-white font-mono truncate">
                    {part.id}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {part.type.replace('wokwi-', '')}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-600 mt-4">
              Full interactive simulation available on{' '}
              <a
                href="https://wokwi.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-cyan-400 hover:underline"
              >
                wokwi.com
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Quick Guide */}
      <div className="forge-card p-5 border-blue-900/50">
        <h4 className="text-sm font-semibold text-blue-400 mb-3">
          💡 Simulation Guide
        </h4>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-400">
          <div>
            <h5 className="text-gray-300 font-semibold mb-2">In-App (Basic)</h5>
            <ul className="space-y-1">
              <li>• Click "Start" to run simulation</li>
              <li>• View serial output in monitor</li>
              <li>• Stop/Reset as needed</li>
              <li>• Limited interactivity</li>
            </ul>
          </div>
          <div>
            <h5 className="text-gray-300 font-semibold mb-2">Wokwi.com (Full)</h5>
            <ul className="space-y-1">
              <li>• Click "Open in Wokwi" button</li>
              <li>• Full interactive circuit</li>
              <li>• Click buttons, adjust sensors</li>
              <li>• Real-time visualization</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
