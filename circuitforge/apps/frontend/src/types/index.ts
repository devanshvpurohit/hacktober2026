// API types — mirror backend Pydantic schemas

export type ProjectStatus =
  | 'created' | 'planning' | 'planned' | 'generating' | 'generated'
  | 'validating' | 'validated' | 'compiling' | 'compiled' | 'compile_failed'
  | 'repairing' | 'complete' | 'error'

export type SimulationStatus =
  | 'not_simulated' | 'ready_to_simulate' | 'simulation_running'
  | 'simulation_passed' | 'simulation_failed' | 'simulation_unavailable'
  | 'manual_verification_required'

export interface ComponentInstance {
  instance_id: string
  catalog_id: string
  name: string
  quantity: number
  value?: string
}

export interface PinAssignment {
  component_id: string
  component_instance: string
  component_pin: string
  gpio_pin: number
  description: string
}

export interface Connection {
  from_component: string
  from_pin: string
  to_component: string
  to_pin: string
  wire_color: string
}

export interface ProjectSpec {
  name: string
  description: string
  behavior: string
  board: string
  components: ComponentInstance[]
  pin_assignments: PinAssignment[]
  connections: Connection[]
  libraries: string[]
  acceptance_criteria: string[]
  assumptions: string[]
  warnings: string[]
  missing_info: string[]
  unsupported: string[]
  threshold_value?: number
  threshold_unit?: string
}

export interface ValidationError {
  code: string
  severity: string
  message: string
  field?: string
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
  warnings: ValidationError[]
}

export interface BOMLine {
  component_id: string
  name: string
  quantity: number
  unit_price_inr: number
  subtotal_inr: number
  price_source: string
  price_verified_date: string
  confidence: string
}

export interface BOM {
  project_id: string
  lines: BOMLine[]
  total_inr: number
  currency: string
  generated_at: string
  note: string
}

export interface RepairAttempt {
  attempt_number: number
  diagnosis: string
  patch_description: string
  files_affected: string[]
  rationale: string
  expected_verification: string
  applied: boolean
  compile_success?: boolean
  error_after?: string
  timestamp: string
}

export interface Project {
  id: string
  name: string
  description: string
  user_request: string
  status: ProjectStatus
  simulation_status: SimulationStatus
  spec?: ProjectSpec
  firmware_code?: string
  diagram_json?: any
  validation_result?: ValidationResult
  compilation_success?: boolean
  compilation_log?: string
  repair_attempts: RepairAttempt[]
  bom?: BOM
  created_at: string
  updated_at: string
  error_message?: string
  workspace_path?: string
}

export interface ProjectSummary {
  id: string
  name: string
  description: string
  status: ProjectStatus
  simulation_status: SimulationStatus
  created_at: string
  updated_at: string
  compilation_success?: boolean
}

export interface SystemStatus {
  os: string
  arch: string
  python: string
  ollama: { available: boolean; version?: string; error?: string }
  models: {
    planner: { name: string; installed: boolean; inference_ok: boolean; error?: string }
    firmware_generator: { name: string; installed: boolean; inference_ok: boolean; error?: string }
  }
  arduino_cli: { available: boolean; version?: string; path?: string; error?: string }
  arduino_boards: { installed?: boolean; esp32_installed?: boolean; error?: string }
  wokwi_cli: { available: boolean; version?: string; error?: string }
}

export interface CatalogComponent {
  id: string
  name: string
  category: string
  wokwi_id: string
  supported_boards: string[]
  unit_price_inr: number
  description: string
  libraries: string[]
  electrical_constraints: string[]
}
