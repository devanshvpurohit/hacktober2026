"""
CircuitForge AI - Pydantic Schemas
Central source of truth for all project data structures.
"""
from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import uuid
from datetime import datetime


# ── Enums ─────────────────────────────────────────────────────────────────────

class ProjectStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    PLANNED = "planned"
    GENERATING = "generating"
    GENERATED = "generated"
    VALIDATING = "validating"
    VALIDATED = "validated"
    COMPILING = "compiling"
    COMPILED = "compiled"
    COMPILE_FAILED = "compile_failed"
    REPAIRING = "repairing"
    COMPLETE = "complete"
    ERROR = "error"


class SimulationStatus(str, Enum):
    NOT_SIMULATED = "not_simulated"
    READY = "ready_to_simulate"
    RUNNING = "simulation_running"
    PASSED = "simulation_passed"
    FAILED = "simulation_failed"
    UNAVAILABLE = "simulation_unavailable"
    MANUAL = "manual_verification_required"


class BoardType(str, Enum):
    ESP32 = "esp32"
    ESP32_S3 = "esp32s3"
    ARDUINO_UNO = "arduino_uno"
    ARDUINO_NANO = "arduino_nano"


# ── Component Schemas ─────────────────────────────────────────────────────────

class ComponentPin(BaseModel):
    name: str
    description: str
    pin_type: str  # power, signal, ground, analog, digital, i2c, spi, uart
    required: bool = True


class WiringRule(BaseModel):
    from_pin: str
    to_component: str
    to_pin: str
    description: str
    required: bool = True


class CatalogComponent(BaseModel):
    id: str
    name: str
    category: str
    wokwi_id: str
    supported_boards: list[str]
    pins: list[ComponentPin]
    wiring_rules: list[WiringRule] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    unit_price_inr: float
    price_source: str = "catalog_estimate"
    price_verified_date: str = "2025-01-01"
    electrical_constraints: list[str] = Field(default_factory=list)
    description: str = ""
    datasheet_url: str = ""
    example_firmware: str = ""


# ── Project Specification Schemas ─────────────────────────────────────────────

class PinAssignment(BaseModel):
    component_id: str
    component_instance: str  # e.g. "dht22_1"
    component_pin: str
    gpio_pin: int
    description: str


class Connection(BaseModel):
    from_component: str
    from_pin: str
    to_component: str
    to_pin: str
    wire_color: str = "green"


class ComponentInstance(BaseModel):
    instance_id: str
    catalog_id: str
    name: str
    quantity: int = 1
    value: Optional[str] = None  # e.g. "220" for resistor value in ohms


class ProjectSpec(BaseModel):
    name: str
    description: str
    behavior: str
    board: BoardType = BoardType.ESP32
    components: list[ComponentInstance] = Field(default_factory=list)
    pin_assignments: list[PinAssignment] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    unsupported: list[str] = Field(default_factory=list)
    threshold_value: Optional[float] = None
    threshold_unit: Optional[str] = None


# ── Validation Result ─────────────────────────────────────────────────────────

class ValidationError(BaseModel):
    code: str
    severity: str  # error | warning | info
    message: str
    field: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationError] = Field(default_factory=list)


# ── BOM ───────────────────────────────────────────────────────────────────────

class BOMLine(BaseModel):
    component_id: str
    name: str
    quantity: int
    unit_price_inr: float
    subtotal_inr: float
    price_source: str
    price_verified_date: str
    confidence: str = "indicative"


class BOM(BaseModel):
    project_id: str
    lines: list[BOMLine]
    total_inr: float
    currency: str = "INR"
    generated_at: str
    note: str = "Prices are indicative catalog estimates. Verify current prices before purchasing."


# ── Repair ────────────────────────────────────────────────────────────────────

class RepairAttempt(BaseModel):
    attempt_number: int
    diagnosis: str
    patch_description: str
    files_affected: list[str]
    rationale: str
    expected_verification: str
    applied: bool
    compile_success: Optional[bool] = None
    error_after: Optional[str] = None
    timestamp: str


# ── Project ───────────────────────────────────────────────────────────────────

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    user_request: str
    status: ProjectStatus = ProjectStatus.CREATED
    simulation_status: SimulationStatus = SimulationStatus.NOT_SIMULATED
    spec: Optional[ProjectSpec] = None
    firmware_code: Optional[str] = None
    diagram_json: Optional[dict] = None
    validation_result: Optional[ValidationResult] = None
    compilation_success: Optional[bool] = None
    compilation_log: Optional[str] = None
    repair_attempts: list[RepairAttempt] = Field(default_factory=list)
    bom: Optional[BOM] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error_message: Optional[str] = None
    workspace_path: Optional[str] = None


# ── API Request/Response schemas ──────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    user_request: str = Field(..., min_length=10, max_length=2000)


class ProjectSummary(BaseModel):
    id: str
    name: str
    description: str
    status: ProjectStatus
    simulation_status: SimulationStatus
    created_at: str
    updated_at: str
    compilation_success: Optional[bool] = None
