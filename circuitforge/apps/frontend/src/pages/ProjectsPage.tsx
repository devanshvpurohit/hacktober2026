import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Cpu, Plus, Trash2, ExternalLink, Clock } from 'lucide-react'
import toast from 'react-hot-toast'
import { listProjects, deleteProject, getErrorMessage } from '../utils/api'
import { STATUS_LABELS, STATUS_CLASS, SIM_LABELS, formatDate } from '../utils/helpers'
import type { ProjectSummary } from '../types'

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      setProjects(await listProjects())
    } catch (err) {
      toast.error(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete project "${name}"? This cannot be undone.`)) return
    try {
      await deleteProject(id)
      toast.success('Project deleted')
      load()
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <header className="border-b border-gray-800 bg-gray-900 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2">
            <Cpu className="w-6 h-6 text-cyan-400" />
            <span className="font-bold text-white">CircuitForge AI</span>
          </Link>
          <span className="text-gray-600">/</span>
          <span className="text-gray-300">Projects</span>
          <div className="flex-1" />
          <Link to="/" className="btn-primary text-sm">
            <Plus className="w-4 h-4" /> New Project
          </Link>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-500">
            Loading projects...
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-24">
            <Cpu className="w-12 h-12 text-gray-700 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-500 mb-2">No projects yet</h3>
            <p className="text-gray-600 mb-6">Describe an IoT project to get started</p>
            <Link to="/" className="btn-primary inline-flex">
              <Plus className="w-4 h-4" /> Create First Project
            </Link>
          </div>
        ) : (
          <div className="grid gap-4">
            {projects.map(p => (
              <div key={p.id} className="forge-card p-5 flex items-start gap-4 hover:border-gray-700 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-white truncate">{p.name}</h3>
                    <span className={STATUS_CLASS[p.status]}>
                      {STATUS_LABELS[p.status]}
                    </span>
                    {p.compilation_success === true && (
                      <span className="status-success">Compiled</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-400 mb-3 truncate">{p.description}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-600">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDate(p.updated_at)}
                    </span>
                    <span>{SIM_LABELS[p.simulation_status]}</span>
                    <span className="font-mono text-gray-700">{p.id.slice(0, 8)}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    to={`/project/${p.id}`}
                    className="btn-secondary text-sm"
                  >
                    <ExternalLink className="w-4 h-4" /> Open
                  </Link>
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    className="p-2 text-gray-600 hover:text-red-400 transition-colors"
                    title="Delete project"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
