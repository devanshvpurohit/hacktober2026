import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Cpu, ChevronLeft, Play, Wrench, Download, RefreshCw,
  CheckCircle, XCircle, AlertTriangle, Info, Loader2,
  Code2, Cpu as CircuitIcon, Package, FileText, Zap, Terminal
} from 'lucide-react'
import Editor from '@monaco-editor/react'
import {
  getProject, generateProject, validateProject,
  compileProject, repairProject, simulateProject,
  downloadProject, getErrorMessage
} from '../utils/api'
import { CircuitEditor } from '../components/CircuitEditor'
import type { Project } from '../types'
import {
  STATUS_LABELS, STATUS_CLASS, SIM_LABELS, SIM_CLASS,
  isRunning, formatDate, formatINR
} from '../utils/helpers'

type Tab = 'overview' | 'firmware' | 'diagram' | 'validation' | 'compile' | 'simulate' | 'bom' | 'repair'

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [opLoading, setOpLoading] = useState<string | null>(null)
  const [compileResult, setCompileResult] = useState<any>(null)
  const [simResult, setSimResult] = useState<any>(null)

  const load = useCallback(async () => {
    if (!id) return
    try {
      const p = await getProject(id)
      setProject(p)
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  // Poll while operations are running
  useEffect(() => {
    if (!project || !isRunning(project.status)) return
    const timer = setInterval(load, 3000)
    return () => clearInterval(timer)
  }, [project?.status, load])

  const runOp = async (opName: string, fn: () => Promise<any>, tab?: Tab) => {
    setOpLoading(opName)
    try {
      const result = await fn()
      await load()
      if (tab) setActiveTab(tab)
      return result
    } catch (err) {
      toast.error(getErrorMessage(err))
      await load()
    } finally {
      setOpLoading(null)
    }
  }

  const handleGenerate = () => runOp('generate', () => generateProject(id!), 'firmware')
  const handleValidate = () => runOp('validate', () => validateProject(id!), 'validation')
  const handleCompile = () =>
    runOp('compile', async () => {
      const r = await compileProject(id!)
      setCompileResult(r)
      if (r.success) toast.success('Compilation succeeded!')
      else toast.error('Compilation failed — check logs')
      return r
    }, 'compile')
  const handleRepair = () =>
    runOp('repair', async () => {
      const r = await repairProject(id!)
      setCompileResult(r)
      if (r.compile_success) toast.success('Repair successful!')
      else toast.error(`Repair attempt ${r.attempt_number} failed`)
      return r
    }, 'repair')
  const handleSimulate = () =>
    runOp('simulate', async () => {
      const r = await simulateProject(id!)
      setSimResult(r)
      return r
    }, 'simulate')

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="flex items-center gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 spinner" />
          Loading project...
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">Project not found</p>
          <Link to="/" className="btn-primary">← Home</Link>
        </div>
      </div>
    )
  }

  const canGenerate = project.spec != null && !isRunning(project.status)
  const canCompile = project.firmware_code != null && !isRunning(project.status)
  const canRepair = project.compilation_success === false && project.repair_attempts.length < 3
  const canSimulate = project.compilation_success === true || project.firmware_code != null

  const tabs: { id: Tab; label: string; icon: React.ElementType; show: boolean }[] = [
    { id: 'overview',   label: 'Overview',   icon: Info,        show: true },
    { id: 'firmware',   label: 'Firmware',   icon: Code2,       show: !!project.firmware_code },
    { id: 'diagram',    label: 'Diagram',    icon: CircuitIcon, show: !!project.diagram_json },
    { id: 'validation', label: 'Validation', icon: CheckCircle, show: !!project.validation_result },
    { id: 'compile',    label: 'Compile',    icon: Terminal,    show: !!project.compilation_log },
    { id: 'simulate',   label: 'Simulate',   icon: Play,        show: true },
    { id: 'bom',        label: 'BOM',        icon: Package,     show: !!project.bom },
    { id: 'repair',     label: 'Repair',     icon: Wrench,      show: project.repair_attempts.length > 0 },
  ]

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-3">
          <div className="flex items-center gap-3 mb-3">
            <Link to="/" className="text-gray-500 hover:text-gray-300 transition-colors">
              <ChevronLeft className="w-5 h-5" />
            </Link>
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h1 className="font-bold text-white text-lg truncate">{project.name}</h1>
            <span className={STATUS_CLASS[project.status]}>
              {isRunning(project.status) && <Loader2 className="w-3.5 h-3.5 spinner inline mr-1" />}
              {STATUS_LABELS[project.status]}
            </span>
            <span className={SIM_CLASS[project.simulation_status]}>
              {SIM_LABELS[project.simulation_status]}
            </span>
            <div className="flex-1" />
            {/* Actions */}
            <button onClick={load} className="btn-secondary text-sm py-1.5" title="Refresh">
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            {canGenerate && (
              <button
                className="btn-primary text-sm py-1.5"
                onClick={handleGenerate}
                disabled={!!opLoading}
              >
                {opLoading === 'generate' ? <Loader2 className="w-4 h-4 spinner" /> : <Zap className="w-4 h-4" />}
                Generate
              </button>
            )}
            {canCompile && (
              <button
                className="btn-primary text-sm py-1.5"
                onClick={handleCompile}
                disabled={!!opLoading}
              >
                {opLoading === 'compile' ? <Loader2 className="w-4 h-4 spinner" /> : <Terminal className="w-4 h-4" />}
                Compile
              </button>
            )}
            {canRepair && (
              <button
                className="btn-secondary text-sm py-1.5 text-yellow-400 border-yellow-800"
                onClick={handleRepair}
                disabled={!!opLoading}
              >
                {opLoading === 'repair' ? <Loader2 className="w-4 h-4 spinner" /> : <Wrench className="w-4 h-4" />}
                Repair ({3 - project.repair_attempts.length} left)
              </button>
            )}
            <button
              className="btn-secondary text-sm py-1.5"
              onClick={() => downloadProject(id!)}
              title="Export ZIP"
            >
              <Download className="w-4 h-4" /> Export
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 overflow-x-auto">
            {tabs.filter(t => t.show).map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-800'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full">
        {activeTab === 'overview' && <OverviewTab project={project} onValidate={handleValidate} opLoading={opLoading} />}
        {activeTab === 'firmware' && <FirmwareTab project={project} />}
        {activeTab === 'diagram' && <DiagramTab project={project} />}
        {activeTab === 'validation' && <ValidationTab project={project} />}
        {activeTab === 'compile' && <CompileTab project={project} result={compileResult} />}
        {activeTab === 'simulate' && <SimulateTab project={project} result={simResult} onSimulate={handleSimulate} opLoading={opLoading} />}
        {activeTab === 'bom' && <BOMTab project={project} />}
        {activeTab === 'repair' && <RepairTab project={project} />}
      </main>
    </div>
  )
}

// ── Tab components ────────────────────────────────────────────────────────────

function OverviewTab({ project, onValidate, opLoading }: { project: Project; onValidate: () => void; opLoading: string | null }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-4">
        <div className="forge-card p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Project Description</h3>
          <p className="text-gray-200 leading-relaxed">{project.description}</p>
          {project.spec?.behavior && (
            <p className="text-sm text-gray-400 mt-2">{project.spec.behavior}</p>
          )}
        </div>

        <div className="forge-card p-5">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">User Request</h3>
          <p className="text-gray-300 text-sm italic leading-relaxed">"{project.user_request}"</p>
        </div>

        {project.error_message && (
          <div className="forge-card p-4 border-red-900">
            <div className="flex items-start gap-2">
              <XCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-semibold text-red-400 mb-1">Error</p>
                <p className="text-sm text-gray-400">{project.error_message}</p>
              </div>
            </div>
          </div>
        )}

        {project.spec && (
          <>
            {/* Components */}
            <div className="forge-card p-5">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Components ({project.spec.components.length})
              </h3>
              <div className="space-y-2">
                {project.spec.components.map(c => (
                  <div key={c.instance_id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                    <span className="text-gray-200 text-sm">{c.name}</span>
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-gray-600 font-mono">{c.catalog_id}</span>
                      <span className="text-xs bg-gray-800 px-2 py-0.5 rounded text-gray-400">×{c.quantity}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Pin Assignments */}
            {project.spec.pin_assignments.length > 0 && (
              <div className="forge-card p-5">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Pin Assignments</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-gray-600 border-b border-gray-800">
                        <th className="text-left py-2">Component</th>
                        <th className="text-left py-2">Pin</th>
                        <th className="text-left py-2">GPIO</th>
                        <th className="text-left py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {project.spec.pin_assignments.map((pa, i) => (
                        <tr key={i} className="border-b border-gray-800/50 last:border-0">
                          <td className="py-2 text-gray-300">{pa.component_instance}</td>
                          <td className="py-2 text-cyan-400 font-mono">{pa.component_pin}</td>
                          <td className="py-2 text-yellow-400 font-mono">GPIO{pa.gpio_pin}</td>
                          <td className="py-2 text-gray-500 text-xs">{pa.description}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Acceptance Criteria */}
            {project.spec.acceptance_criteria.length > 0 && (
              <div className="forge-card p-5">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Acceptance Criteria</h3>
                <ul className="space-y-1.5">
                  {project.spec.acceptance_criteria.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                      <CheckCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Warnings */}
            {project.spec.warnings.length > 0 && (
              <div className="forge-card p-5 border-yellow-900/50">
                <h3 className="text-sm font-semibold text-yellow-400 uppercase tracking-wider mb-3">⚠ Warnings</h3>
                <ul className="space-y-1.5">
                  {project.spec.warnings.map((w, i) => (
                    <li key={i} className="text-sm text-yellow-300/80">{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}
      </div>

      {/* Sidebar */}
      <div className="space-y-4">
        <div className="forge-card p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Status</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Board</span>
              <span className="text-cyan-400 font-mono">{project.spec?.board ?? '—'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Project</span>
              <span className={STATUS_CLASS[project.status]}>{STATUS_LABELS[project.status]}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Simulation</span>
              <span className={SIM_CLASS[project.simulation_status]}>{SIM_LABELS[project.simulation_status]}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Compilation</span>
              <span className={project.compilation_success === true ? 'text-green-400' : project.compilation_success === false ? 'text-red-400' : 'text-gray-600'}>
                {project.compilation_success === true ? '✓ Success' : project.compilation_success === false ? '✗ Failed' : 'Not compiled'}
              </span>
            </div>
          </div>
        </div>

        {project.spec?.libraries && project.spec.libraries.length > 0 && (
          <div className="forge-card p-4">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Libraries</h3>
            <ul className="space-y-1">
              {project.spec.libraries.map((lib, i) => (
                <li key={i} className="text-xs font-mono text-cyan-300 bg-gray-800 px-2 py-1 rounded">{lib}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="forge-card p-4">
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Metadata</h3>
          <div className="space-y-1 text-xs text-gray-600">
            <div className="font-mono">{project.id}</div>
            <div>Created: {formatDate(project.created_at)}</div>
            <div>Updated: {formatDate(project.updated_at)}</div>
          </div>
        </div>

        {project.spec && (
          <button
            className="btn-secondary w-full justify-center text-sm"
            onClick={onValidate}
            disabled={!!opLoading}
          >
            {opLoading === 'validate' ? <Loader2 className="w-4 h-4 spinner" /> : <CheckCircle className="w-4 h-4" />}
            Run Validation
          </button>
        )}
      </div>
    </div>
  )
}

function FirmwareTab({ project }: { project: Project }) {
  if (!project.firmware_code) {
    return <EmptyState icon={Code2} message="Firmware not yet generated. Click Generate above." />
  }
  return (
    <div className="h-[70vh] forge-card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
        <span className="text-sm text-gray-400 font-mono">sketch.ino</span>
        <span className="text-xs text-gray-600">{project.firmware_code.length} chars</span>
      </div>
      <Editor
        height="calc(100% - 41px)"
        language="cpp"
        value={project.firmware_code}
        theme="vs-dark"
        options={{
          readOnly: true,
          fontSize: 13,
          minimap: { enabled: false },
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          fontFamily: 'JetBrains Mono, Fira Code, monospace',
        }}
      />
    </div>
  )
}

function DiagramTab({ project }: { project: Project }) {
  if (!project.diagram_json) {
    return <EmptyState icon={CircuitIcon} message="Diagram not yet generated." />
  }
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider flex items-center gap-2">
            <CircuitIcon className="w-4 h-4 text-cyan-400" />
            Interactive Circuit Editor (Wokwi-Compatible)
          </h3>
          <span className="text-xs text-gray-500">
            Click & drag components to rearrange • Drag canvas to pan • Scroll to zoom
          </span>
        </div>
        <CircuitEditor
          diagram={project.diagram_json}
          pinAssignments={project.spec?.pin_assignments || []}
        />
      </div>

      <div className="forge-card overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
          <span className="text-sm text-gray-400 font-mono">diagram.json</span>
          <span className="text-xs text-gray-600">{project.diagram_json.connections?.length ?? 0} connections</span>
        </div>
        <Editor
          height="300px"
          language="json"
          value={JSON.stringify(project.diagram_json, null, 2)}
          theme="vs-dark"
          options={{ readOnly: true, fontSize: 12, minimap: { enabled: false }, fontFamily: 'JetBrains Mono, monospace' }}
        />
      </div>
    </div>
  )
}

function ValidationTab({ project }: { project: Project }) {
  const v = project.validation_result
  if (!v) return <EmptyState icon={CheckCircle} message="Run validation from the Overview tab." />
  return (
    <div className="space-y-4">
      <div className={`forge-card p-5 ${v.valid ? 'border-green-900/50' : 'border-red-900/50'}`}>
        <div className="flex items-center gap-3">
          {v.valid
            ? <CheckCircle className="w-6 h-6 text-green-400" />
            : <XCircle className="w-6 h-6 text-red-400" />
          }
          <div>
            <p className={`font-semibold ${v.valid ? 'text-green-400' : 'text-red-400'}`}>
              {v.valid ? 'All Validation Checks Passed' : 'Validation Failed'}
            </p>
            <p className="text-sm text-gray-500">
              {v.errors.length} error(s), {v.warnings.length} warning(s)
            </p>
          </div>
        </div>
      </div>
      {v.errors.length > 0 && (
        <div className="forge-card p-5">
          <h3 className="text-sm font-semibold text-red-400 mb-3">Errors</h3>
          <div className="space-y-2">
            {v.errors.map((e, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <XCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-mono text-red-300 text-xs">[{e.code}] </span>
                  <span className="text-gray-300">{e.message}</span>
                  {e.field && <span className="text-gray-600 text-xs ml-2">({e.field})</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {v.warnings.length > 0 && (
        <div className="forge-card p-5">
          <h3 className="text-sm font-semibold text-yellow-400 mb-3">Warnings</h3>
          <div className="space-y-2">
            {v.warnings.map((w, i) => (
              <div key={i} className="flex items-start gap-2 text-sm">
                <AlertTriangle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-mono text-yellow-300 text-xs">[{w.code}] </span>
                  <span className="text-gray-300">{w.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CompileTab({ project, result }: { project: Project; result: any }) {
  const log = project.compilation_log
  const displayResult = result || (log ? { success: project.compilation_success } : null)
  return (
    <div className="space-y-4">
      {displayResult && (
        <div className={`forge-card p-4 ${displayResult.success ? 'border-green-900/50' : 'border-red-900/50'}`}>
          <div className="flex items-center gap-2">
            {displayResult.success
              ? <CheckCircle className="w-5 h-5 text-green-400" />
              : <XCircle className="w-5 h-5 text-red-400" />
            }
            <span className={`font-semibold ${displayResult.success ? 'text-green-400' : 'text-red-400'}`}>
              {displayResult.success ? 'Compilation Succeeded' : 'Compilation Failed'}
            </span>
            {displayResult.exit_code !== undefined && (
              <span className="text-xs text-gray-600 ml-auto">exit code: {displayResult.exit_code}</span>
            )}
          </div>
        </div>
      )}
      {log ? (
        <div className="forge-card overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-800 text-sm text-gray-400 font-mono">Compiler Output</div>
          <pre className="terminal-bg max-h-[60vh] overflow-auto text-xs whitespace-pre-wrap">{log}</pre>
        </div>
      ) : (
        <EmptyState icon={Terminal} message="No compilation output yet. Click Compile above." />
      )}
    </div>
  )
}

function SimulateTab({ project, result, onSimulate, opLoading }: { project: Project; result: any; onSimulate: () => void; opLoading: string | null }) {
  return (
    <div className="space-y-4">
      <div className="forge-card p-5">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Simulation</h3>
        <p className="text-gray-400 text-sm mb-4">
          Simulation status: <span className={SIM_CLASS[project.simulation_status]}>{SIM_LABELS[project.simulation_status]}</span>
        </p>
        <button
          className="btn-primary"
          onClick={onSimulate}
          disabled={!!opLoading || !project.firmware_code}
        >
          {opLoading === 'simulate' ? <Loader2 className="w-4 h-4 spinner" /> : <Play className="w-4 h-4" />}
          {opLoading === 'simulate' ? 'Running...' : 'Start Simulation'}
        </button>
      </div>

      {result && result.mode === 'manual' && (
        <div className="forge-card p-5 border-yellow-900/50">
          <h3 className="text-sm font-semibold text-yellow-400 mb-3">⚠ Manual Wokwi Simulation Required</h3>
          <p className="text-sm text-gray-400 mb-4">{result.message}</p>
          <ol className="space-y-2">
            {result.manual_steps?.map((step: string, i: number) => (
              <li key={i} className="text-sm text-gray-300">{step}</li>
            ))}
          </ol>
          <a
            href="https://wokwi.com/"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary mt-4 inline-flex"
          >
            Open Wokwi →
          </a>
        </div>
      )}

      {result && result.mode !== 'manual' && result.stdout && (
        <div className="forge-card overflow-hidden">
          <div className="px-4 py-2 border-b border-gray-800 text-sm text-gray-400">Simulation Output</div>
          <pre className="terminal-bg max-h-96 overflow-auto text-xs whitespace-pre-wrap">{result.stdout}</pre>
        </div>
      )}

      {/* Manual Wokwi Instructions always shown */}
      <div className="forge-card p-5">
        <h3 className="text-sm font-semibold text-cyan-400 mb-3">Manual Wokwi Simulation (Always Available)</h3>
        <ol className="space-y-2 text-sm text-gray-400">
          <li>1. Open <a href="https://wokwi.com/" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">wokwi.com</a></li>
          <li>2. Create a new ESP32 project</li>
          <li>3. Use the <strong className="text-gray-300">Diagram</strong> tab to copy your <code>diagram.json</code></li>
          <li>4. Use the <strong className="text-gray-300">Firmware</strong> tab to copy your <code>sketch.ino</code></li>
          <li>5. Click ▶ Play to simulate</li>
          <li>6. Or export the ZIP and upload files manually</li>
        </ol>
        <button
          className="btn-secondary mt-3 text-sm"
          onClick={() => downloadProject(project.id)}
        >
          <Download className="w-4 h-4" /> Download Project ZIP
        </button>
      </div>
    </div>
  )
}

function BOMTab({ project }: { project: Project }) {
  const bom = project.bom
  if (!bom) return <EmptyState icon={Package} message="BOM is generated automatically after planning." />
  return (
    <div className="space-y-4">
      <div className="forge-card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Bill of Materials</h3>
          <span className="text-cyan-400 font-bold">{formatINR(bom.total_inr)} total</span>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-600 border-b border-gray-800">
              <th className="text-left py-2">Component</th>
              <th className="text-right py-2">Qty</th>
              <th className="text-right py-2">Unit (INR)</th>
              <th className="text-right py-2">Subtotal (INR)</th>
            </tr>
          </thead>
          <tbody>
            {bom.lines.map((line, i) => (
              <tr key={i} className="border-b border-gray-800/50 last:border-0">
                <td className="py-2 text-gray-200">{line.name}</td>
                <td className="py-2 text-right text-gray-400">{line.quantity}</td>
                <td className="py-2 text-right text-gray-400">{formatINR(line.unit_price_inr)}</td>
                <td className="py-2 text-right text-cyan-400">{formatINR(line.subtotal_inr)}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-gray-700">
              <td colSpan={3} className="py-2 font-semibold text-gray-300">Total</td>
              <td className="py-2 text-right font-bold text-cyan-400">{formatINR(bom.total_inr)}</td>
            </tr>
          </tbody>
        </table>
        <p className="text-xs text-gray-600 mt-4">{bom.note}</p>
      </div>
    </div>
  )
}

function RepairTab({ project }: { project: Project }) {
  if (project.repair_attempts.length === 0) {
    return <EmptyState icon={Wrench} message="No repair attempts yet. Repair is triggered when compilation fails." />
  }
  return (
    <div className="space-y-4">
      {project.repair_attempts.map(attempt => (
        <div
          key={attempt.attempt_number}
          className={`forge-card p-5 ${attempt.compile_success ? 'border-green-900/50' : 'border-red-900/50'}`}
        >
          <div className="flex items-center gap-2 mb-3">
            {attempt.compile_success
              ? <CheckCircle className="w-5 h-5 text-green-400" />
              : <XCircle className="w-5 h-5 text-red-400" />
            }
            <span className="font-semibold text-gray-200">Repair Attempt #{attempt.attempt_number}</span>
            <span className="text-xs text-gray-600 ml-auto">{formatDate(attempt.timestamp)}</span>
          </div>
          <div className="text-sm text-gray-400 space-y-1">
            <p><span className="text-gray-600">Diagnosis:</span> {attempt.diagnosis}</p>
            <p><span className="text-gray-600">Action:</span> {attempt.patch_description}</p>
            <p><span className="text-gray-600">Files:</span> {attempt.files_affected.join(', ')}</p>
            {attempt.error_after && (
              <p><span className="text-red-500">Error after repair:</span> {attempt.error_after}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

function EmptyState({ icon: Icon, message }: { icon: React.ElementType; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-64 text-gray-600">
      <Icon className="w-10 h-10 mb-3" />
      <p className="text-sm">{message}</p>
    </div>
  )
}
