import { type ProjectStatus, type SimulationStatus } from '../types'

// ── Status labels & styles ────────────────────────────────────────────────────

export const STATUS_LABELS: Record<ProjectStatus, string> = {
  created: 'Created',
  planning: 'Planning...',
  planned: 'Planned',
  generating: 'Generating...',
  generated: 'Generated',
  validating: 'Validating...',
  validated: 'Validated',
  compiling: 'Compiling...',
  compiled: 'Compiled ✓',
  compile_failed: 'Compile Failed',
  repairing: 'Repairing...',
  complete: 'Complete',
  error: 'Error',
}

export const STATUS_CLASS: Record<ProjectStatus, string> = {
  created: 'status-muted',
  planning: 'status-info',
  planned: 'status-info',
  generating: 'status-info',
  generated: 'status-info',
  validating: 'status-info',
  validated: 'status-success',
  compiling: 'status-info',
  compiled: 'status-success',
  compile_failed: 'status-error',
  repairing: 'status-warning',
  complete: 'status-success',
  error: 'status-error',
}

export const SIM_LABELS: Record<SimulationStatus, string> = {
  not_simulated: 'Not Simulated',
  ready_to_simulate: 'Ready to Simulate',
  simulation_running: 'Simulating...',
  simulation_passed: 'Simulation Passed ✓',
  simulation_failed: 'Simulation Failed',
  simulation_unavailable: 'Simulation Unavailable',
  manual_verification_required: 'Manual Verification Required',
}

export const SIM_CLASS: Record<SimulationStatus, string> = {
  not_simulated: 'status-muted',
  ready_to_simulate: 'status-info',
  simulation_running: 'status-info',
  simulation_passed: 'status-success',
  simulation_failed: 'status-error',
  simulation_unavailable: 'status-warning',
  manual_verification_required: 'status-warning',
}

export function isRunning(status: ProjectStatus): boolean {
  return ['planning', 'generating', 'validating', 'compiling', 'repairing'].includes(status)
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString()
  } catch { return iso }
}

export function formatINR(amount: number): string {
  return `₹${amount.toFixed(2)}`
}
