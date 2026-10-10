import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  Cpu, CheckCircle, XCircle, AlertTriangle, ExternalLink, RefreshCw, Loader2
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getSystemStatus, installModel, getErrorMessage } from '../utils/api'
import type { SystemStatus } from '../types'

type StatusBadgeProps = { ok: boolean; label: string; extra?: string; error?: string }

function StatusRow({ ok, label, extra, error }: StatusBadgeProps) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      {ok
        ? <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 shrink-0" />
        : <XCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
      }
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${ok ? 'text-gray-200' : 'text-gray-400'}`}>{label}</span>
          {extra && <span className="text-xs text-gray-500 font-mono">{extra}</span>}
        </div>
        {error && <p className="text-xs text-red-400 mt-0.5">{error}</p>}
      </div>
    </div>
  )
}

export default function SetupPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setStatus(await getSystemStatus())
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 bg-gray-900">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-cyan-400" />
            <span className="font-bold text-white">CircuitForge AI</span>
          </Link>
          <span className="text-gray-600">/</span>
          <span className="text-gray-300">System Setup</span>
          <div className="flex-1" />
          <button onClick={load} className="btn-secondary text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-white mb-2">System Status & Setup</h1>
        <p className="text-gray-400 mb-8">All processing happens locally. No cloud services required.</p>

        {loading ? (
          <div className="flex items-center gap-3 text-gray-500 h-64 justify-center">
            <Loader2 className="w-6 h-6 spinner" /> Checking system...
          </div>
        ) : status ? (
          <div className="space-y-6">
            {/* System Info */}
            <div className="forge-card p-5">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">System</h2>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div><span className="text-gray-600">OS:</span> <span className="text-gray-200">{status.os} / {status.arch}</span></div>
                <div><span className="text-gray-600">Python:</span> <span className="text-gray-200">{status.python}</span></div>
              </div>
            </div>

            {/* Ollama */}
            <div className="forge-card p-5">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Ollama</h2>
              <p className="text-xs text-gray-600 mb-3">Local AI inference engine — required for planning and code generation</p>
              <StatusRow
                ok={status.ollama.available}
                label="Ollama Server"
                extra={status.ollama.version}
                error={status.ollama.error}
              />
              {!status.ollama.available && (
                <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-xs text-gray-400">
                  <p className="font-semibold text-gray-300 mb-1">To install Ollama:</p>
                  <code className="block font-mono text-cyan-400">brew install ollama</code>
                  <code className="block font-mono text-cyan-400 mt-1">ollama serve</code>
                </div>
              )}
            </div>

            {/* Models */}
            <div className="forge-card p-5">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">AI Models</h2>
              <p className="text-xs text-gray-600 mb-3">Models run locally via Ollama</p>

              {status.models.planner && (
                <>
                  <StatusRow
                    ok={status.models.planner.inference_ok}
                    label={`Planner: ${status.models.planner.name}`}
                    extra={status.models.planner.installed ? 'installed' : 'not installed'}
                    error={status.models.planner.error}
                  />
                  {!status.models.planner.installed && (
                    <div className="ml-8 mb-2">
                      <code className="text-xs font-mono text-cyan-400">ollama pull gemma3:1b</code>
                    </div>
                  )}
                </>
              )}

              {status.models.firmware_generator && (
                <>
                  <StatusRow
                    ok={status.models.firmware_generator.inference_ok}
                    label={`Firmware Generator: ${status.models.firmware_generator.name}`}
                    extra={status.models.firmware_generator.installed ? 'installed' : 'not installed'}
                    error={status.models.firmware_generator.error}
                  />
                  {!status.models.firmware_generator.installed && (
                    <div className="ml-8 mb-2">
                      <code className="text-xs font-mono text-cyan-400 break-all">
                        ollama pull hf.co/tapariapurv/Arduino-Coder-0.5B-GGUF-v1:Q4_K_M
                      </code>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Arduino CLI */}
            <div className="forge-card p-5">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Arduino CLI</h2>
              <p className="text-xs text-gray-600 mb-3">Required for actual firmware compilation</p>
              <StatusRow
                ok={status.arduino_cli.available}
                label="Arduino CLI"
                extra={status.arduino_cli.version?.slice(0, 60)}
                error={status.arduino_cli.error}
              />
              <StatusRow
                ok={status.arduino_boards?.esp32_installed ?? false}
                label="ESP32 Board Core (esp32:esp32)"
                error={status.arduino_boards?.error}
              />
              {!status.arduino_cli.available && (
                <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-xs text-gray-400 space-y-1">
                  <p className="font-semibold text-gray-300">To install Arduino CLI:</p>
                  <code className="block font-mono text-cyan-400">brew install arduino-cli</code>
                  <code className="block font-mono text-cyan-400">arduino-cli core update-index</code>
                  <code className="block font-mono text-cyan-400">arduino-cli core install esp32:esp32</code>
                </div>
              )}
              {status.arduino_cli.available && !status.arduino_boards?.esp32_installed && (
                <div className="mt-2 p-2 bg-gray-800/50 rounded text-xs">
                  <code className="font-mono text-cyan-400">arduino-cli core install esp32:esp32</code>
                </div>
              )}
            </div>

            {/* Wokwi CLI */}
            <div className="forge-card p-5">
              <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-1">Wokwi CLI</h2>
              <p className="text-xs text-gray-600 mb-3">Optional — for automated simulation. Manual simulation via wokwi.com is always available.</p>
              <StatusRow
                ok={status.wokwi_cli.available}
                label="Wokwi CLI"
                extra={status.wokwi_cli.version}
                error={status.wokwi_cli.error}
              />
              {!status.wokwi_cli.available && (
                <div className="mt-3 p-3 bg-gray-800/50 rounded-lg text-xs text-gray-400">
                  <p className="text-gray-400">
                    Manual simulation via <a href="https://wokwi.com/" target="_blank" rel="noopener noreferrer" className="text-cyan-400">wokwi.com</a> is always available.
                    For automated simulation, see{' '}
                    <a href="https://docs.wokwi.com/wokwi-ci/cli-usage" target="_blank" rel="noopener noreferrer" className="text-cyan-400">Wokwi CI docs</a>.
                  </p>
                </div>
              )}
            </div>

            {/* Privacy Note */}
            <div className="forge-card p-5 border-cyan-900/30">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-sm font-semibold text-cyan-400 mb-1">Privacy & Local Operation</h3>
                  <ul className="text-xs text-gray-500 space-y-0.5 list-disc list-inside">
                    <li>All AI inference runs locally via Ollama — no cloud LLM APIs used</li>
                    <li>All project data stored in local SQLite + filesystem</li>
                    <li>Arduino CLI compilation is fully local</li>
                    <li>Automated Wokwi simulation may require internet access and authentication</li>
                    <li>Manual Wokwi simulation uses wokwi.com (external service)</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-gray-500">Failed to load system status.</p>
        )}
      </main>
    </div>
  )
}
