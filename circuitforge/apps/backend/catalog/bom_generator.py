"""
CircuitForge AI - BOM Generator
Generates Bill of Materials from project spec using catalog pricing.
Uses Python Decimal for correct monetary arithmetic.
"""
from __future__ import annotations
import sys
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from schemas import ProjectSpec, BOM, BOMLine
from catalog.components import CATALOG, ESP32_DEVKIT


def generate_bom(project_id: str, spec: ProjectSpec) -> BOM:
    """
    Generate BOM from project specification.
    Prices are indicative catalog estimates — not live market prices.
    """
    lines: list[BOMLine] = []
    total = Decimal("0.00")

    # Always include the board
    board_cat = ESP32_DEVKIT
    board_qty = 1
    board_unit = Decimal(str(board_cat.unit_price_inr))
    board_subtotal = board_unit * board_qty
    lines.append(BOMLine(
        component_id=board_cat.id,
        name=board_cat.name,
        quantity=board_qty,
        unit_price_inr=float(board_unit),
        subtotal_inr=float(board_subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        price_source=board_cat.price_source,
        price_verified_date=board_cat.price_verified_date,
        confidence="indicative",
    ))
    total += board_subtotal

    # Components
    for inst in spec.components:
        cat = CATALOG.get(inst.catalog_id)
        if cat is None:
            continue
        qty = Decimal(str(inst.quantity))
        unit = Decimal(str(cat.unit_price_inr))
        subtotal = (qty * unit).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        lines.append(BOMLine(
            component_id=cat.id,
            name=cat.name,
            quantity=inst.quantity,
            unit_price_inr=float(unit),
            subtotal_inr=float(subtotal),
            price_source=cat.price_source,
            price_verified_date=cat.price_verified_date,
            confidence="indicative",
        ))
        total += subtotal

    total_rounded = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return BOM(
        project_id=project_id,
        lines=lines,
        total_inr=float(total_rounded),
        currency="INR",
        generated_at=datetime.utcnow().isoformat(),
        note=(
            "Prices are indicative catalog estimates as of the verification date. "
            "Verify current prices before purchasing. Prices may vary by supplier."
        ),
    )
