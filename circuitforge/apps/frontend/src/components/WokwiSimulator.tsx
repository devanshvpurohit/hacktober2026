import { useState, useEffect } from 'react'
import { Play, ExternalLink, Copy, Check } from 'lucide-react'

interface WokwiSimulatorProps {
  diagram: any
  firmware: string
  projectName: string
}

export default function WokwiSimulator({ diagram, firmware, projectName }: WokwiSimulatorProps) {
  const [showEmbed, setShowEmbed] = useState(false)
  const [copied, setCopied] = useState(false)
  const [wokwiUrl, setWokwiUrl] = useState<string>('')

  // Generate Wokwi share URL
  useEffect(() => {
    if (!diagram || !firmware) return

    // Encode the project data
    const projectData = {
      version: 1,
      author: 'CircuitForge AI',
      editor: 'wokwi',
      parts: diagram.parts || [],
      connections: diagram.connections || [],
    }

    // Create a shareable URL (this is a simplified version)
    // In production, you'd upload to Wokwi's API
    const encodedDiagram = encodeURIComponent(JSON.stringify(projectData))
    const encodedCode = encodeURIComponent(firmware)
    
    // For now, just link to Wokwi with instructions
    setWokwiUrl('https://wokwi.com/')
  }, [diagram, firmware])

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Wokwi Embed Info */}
      <div className="forge-card p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-cyan-400 mb-1">
              Wokwi Circuit Simulator
            </h3>
            <p className="text-sm text-gray-400">
              Interactive circuit simulation powered by Wokwi
            </p>
          </div>
          <a
            href={wokwiUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary text-sm flex items-center gap-2"
          >
            <ExternalLink className="w-4 h-4" />
            Open in Wokwi
          </a>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
          <button
            onClick={() => copyToClipboard(JSON.stringify(diagram, null, 2), 'diagram')}
            className="btn-secondary justify-center text-sm"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            Copy diagram.json
          </button>
          <button
            onClick={() => copyToClipboard(firmware, 'firmware')}
            className="btn-secondary justify-center text-sm"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            Copy sketch.ino
          </button>
        </div>

        {/* Instructions */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-300 mb-3">
            How to Simulate on Wokwi:
          </h4>
          <ol className="space-y-2 text-sm text-gray-400">
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">1.</span>
              <span>Click "Open in Wokwi" above (or visit <a href="https://wokwi.com" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">wokwi.com</a>)</span>
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">2.</span>
              <span>Create a new ESP32 project or start with a blank project</span>
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">3.</span>
              <span>Copy the diagram.json content (button above) and paste it into the "diagram.json" tab in Wokwi</span>
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">4.</span>
              <span>Copy the sketch.ino content (button above) and paste it into the code editor</span>
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">5.</span>
              <span>Click the green ▶ Play button in Wokwi to start the simulation</span>
            </li>
            <li className="flex gap-2">
              <span className="text-cyan-400 font-mono">6.</span>
              <span>Interact with your circuit - click buttons, adjust sensors, observe outputs!</span>
            </li>
          </ol>
        </div>
      </div>

      {/* Circuit Preview */}
      <div className="forge-card p-5">
        <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Circuit Components ({diagram.parts?.length || 0})
        </h4>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {diagram.parts?.map((part: any, i: number) => (
            <div key={i} className="bg-gray-800 rounded-lg p-3 border border-gray-700">
              <div className="text-xs text-gray-500 mb-1">{part.type}</div>
              <div className="text-sm text-white font-mono truncate">{part.id}</div>
              {part.attrs && Object.keys(part.attrs).length > 0 && (
                <div className="text-xs text-cyan-400 mt-1">
                  {Object.entries(part.attrs).map(([key, value]) => (
                    <span key={key} className="block truncate">
                      {key}: {String(value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Connections Info */}
      {diagram.connections && diagram.connections.length > 0 && (
        <div className="forge-card p-5">
          <h4 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Wire Connections ({diagram.connections.length})
          </h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {diagram.connections.map((conn: any[], i: number) => (
              <div key={i} className="flex items-center gap-3 text-sm bg-gray-800 rounded px-3 py-2">
                <span className="text-gray-400 font-mono flex-1">{conn[0]}</span>
                <div className="flex items-center gap-2">
                  <div
                    className="w-12 h-1 rounded"
                    style={{ backgroundColor: conn[2] || 'green' }}
                  />
                  <span className="text-xs text-gray-600">{conn[2]}</span>
                </div>
                <span className="text-gray-400 font-mono flex-1 text-right">{conn[1]}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Alternative: Local Simulation Info */}
      <div className="forge-card p-5 border-blue-900/50">
        <h4 className="text-sm font-semibold text-blue-400 mb-3">
          ℹ️ Local Simulation (Advanced)
        </h4>
        <p className="text-sm text-gray-400 mb-3">
          For local simulation, you can use Wokwi CLI or compile and upload to real hardware:
        </p>
        <div className="space-y-2 text-sm text-gray-400">
          <div className="flex gap-2">
            <span className="text-blue-400">•</span>
            <span><strong className="text-gray-300">Wokwi CLI:</strong> Install from <a href="https://docs.wokwi.com/wokwi-ci/getting-started" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">docs.wokwi.com</a></span>
          </div>
          <div className="flex gap-2">
            <span className="text-blue-400">•</span>
            <span><strong className="text-gray-300">Arduino CLI:</strong> Use the Compile tab to build firmware</span>
          </div>
          <div className="flex gap-2">
            <span className="text-blue-400">•</span>
            <span><strong className="text-gray-300">Real Hardware:</strong> Upload compiled firmware to your ESP32 board</span>
          </div>
        </div>
      </div>
    </div>
  )
}
