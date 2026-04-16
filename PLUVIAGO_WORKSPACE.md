# Pluviago Biotech ERP - Complete Workspace Flow

## Project Overview

Pluviago is a pharmaceutical biotech ERP system for managing the complete lifecycle of algae/cell culture production from raw material procurement through cultivation, harvesting, and extraction. The system tracks quality control, genealogy, and compliance throughout the entire process.

---

## System Architecture

### Module Structure
```
pluviago/
├── pluviago_biotech/          # Main module
│   ├── doctype/               # 21 DocTypes (business entities)
│   ├── report/                # Custom reports
│   ├── utils/                 # Shared utilities (stock_utils.py)
│   ├── workspace/             # UI workspaces
│   └── tasks.py               # Scheduled tasks (alerts, notifications)
├── setup/                     # Installation phases (phase1-7)
├── www/                       # Web pages (custom login)
└── hooks.py                   # Frappe hooks configuration
```

---

## Complete Production Flow

### Stage 0: Procurement & Raw Materials

**DocType:** `Raw Material Batch`

**Purpose:** Track incoming chemicals and raw materials from suppliers

**Key Fields:**
- `batch_number` - Unique identifier (RMB-YYYY-####)
- `material_name` - Chemical/material name
- `supplier` - Vendor information
- `received_qty` / `received_qty_uom` - Quantity received
- `consumed_qty` - Total consumed (auto-calculated)
- `remaining_qty` - Available stock (auto-calculated)
- `expiry_date` - Expiration tracking
- `qc_status` - Pending / Passed / Failed
- `status` - Active / Exhausted / Expired

**Workflow:**
1. Store Keeper creates RMB on material receipt
2. QC Analyst performs quality checks
3. QC Manager approves (qc_status = Passed)
4. Batch becomes available for use in preparations
5. System tracks consumption and updates remaining_qty
6. Status auto-changes to "Exhausted" when remaining_qty <= 0

**Alerts:**
- Orange alert: Expiring within 30 days
- Red alert: Already expired
- Low stock alert: remaining_qty below threshold

---

### Stage 0A: Stock Solution Preparation

**DocType:** `Stock Solution Batch`

**Purpose:** Prepare concentrated stock solutions (A1-A7) from raw materials

**Key Fields:**
- `batch_number` - SSB-YYYY-####
- `solution_type` - A1 / A2 / A3 / A4 / A5 / A6 / A7 / A5M
- `target_volume` - Intended volume (Litres)
- `available_volume` - Remaining volume after use
- `preparation_status` - Draft / QC Pending / Released / Wasted
- `qc_status` - Pending / Passed / Failed
- `released_date` / `released_by` - Release tracking

**Child Table:** `Stock Solution Ingredient`
- `raw_material_batch` - Link to RMB (required)
- `qty` - Quantity consumed
- `uom` - Unit of measure (must match RMB)

**Workflow:**
1. Lab Technician creates SSB, adds ingredients from approved RMBs
2. Fills sterilization details (method, temperature, duration)
3. Clicks **"Mark Preparation Complete"**
   - System validates: UOM match, no over-consumption
   - Deducts qty from each RMB
   - Creates Stock Consumption Log (action = Consumed)
   - Sets preparation_status = QC Pending
4. QC Analyst performs checks (pH, clarity, concentration)
5. **If QC Pass:**
   - Submit batch
   - preparation_status = Released
   - available_volume = target_volume
   - Batch available for medium preparation
6. **If QC Fail:**
   - Click "Mark as Wasted"
   - preparation_status = Wasted
   - Stock NOT reversed (chemicals physically gone)
   - Creates log entry (action = Written Off)

**QC Parameters:**
- pH range
- Clarity (Pass/Fail)
- Concentration (if applicable)
- Sterilization verification

---

### Stage 0B: Medium Preparation (Green & Red)

**DocTypes:** `Green Medium Batch`, `Red Medium Batch`

**Purpose:** Prepare growth media by combining stock solutions and direct chemicals

**Green Medium Batch:**
- Uses stock solutions: A1, A2, A3
- Direct chemicals via `Medium Direct Ingredient` child table
- QC Checkpoint 1: Clarity, pH, sterilization verification

**Red Medium Batch:**
- Uses stock solutions: A4, A5, A6, A7, A5M
- Direct chemicals via `Medium Direct Ingredient` child table
- QC Checkpoint 2: Clarity, pH, sterilization verification

**Key Fields:**
- `batch_number` - GMB-YYYY-#### / RMB-YYYY-####
- `target_volume` - Intended volume
- `preparation_status` - Draft / QC Pending / Released / Wasted
- Stock solution links (a1, a2, a3 for Green; a4-a7, a5m for Red)
- `qc_checkpoint_X_clarity` - Pass/Fail
- `qc_checkpoint_X_ph` - Measured pH
- `overall_qc_status` - Pass/Fail

**Child Table:** `Medium Direct Ingredient`
- `raw_material_batch` - Direct chemical source (required)
- `qty` - Quantity used
- `uom` - Unit of measure

**Workflow:**
1. Lab Technician creates batch
2. Links to approved Stock Solution Batches
3. Adds direct chemicals from RMBs
4. Fills sterilization details
5. Clicks **"Mark Preparation Complete"**
   - Deducts stock solution volumes
   - Deducts direct chemical quantities from RMBs
   - Creates consumption logs
   - preparation_status = QC Pending
6. QC performs Checkpoint 1 (Green) or Checkpoint 2 (Red)
7. **If Pass:** Submit → Released
8. **If Fail:** Mark as Wasted or log corrective action

**Corrective Action Support:**
- `corrective_action_taken` - Description
- `corrective_action_by` - User
- `corrective_action_date` - Date
- `re_qc_required` - Checkbox for re-testing

---

### Stage 0C: Final Medium Preparation

**DocType:** `Final Medium Batch`

**Purpose:** Combine Green and Red media in specific ratios for cultivation

**Key Fields:**
- `batch_number` - FMB-YYYY-####
- `green_medium_batch` - Link to approved GMB
- `red_medium_batch` - Link to approved RMB
- `green_volume` - Volume of green medium used
- `red_volume` - Volume of red medium used
- `total_volume` - Final volume
- `mixing_ratio` - Green:Red ratio
- `qc_checkpoint_3_clarity` - Pass/Fail
- `qc_checkpoint_3_ph` - Measured pH
- `overall_qc_status` - Pass/Fail

**Workflow:**
1. Lab Technician creates FMB
2. Links approved Green and Red medium batches
3. Specifies volumes and mixing ratio
4. Fills sterilization and mixing details
5. QC performs Checkpoint 3
6. **If Pass:** Submit → Available for cultivation
7. **If Fail:** Corrective action or waste

---

### Stage 1-6: Cultivation Pipeline

**DocType:** `Production Batch`

**Purpose:** Track cell culture through all cultivation stages

**Cultivation Stages:**
1. **Flask** - Initial small-scale culture (Stage 1)
2. **25L PBR** - First photobioreactor scale-up (Stage 2)
3. **275L PBR** - Medium-scale reactor (Stage 3)
4. **925L PBR** - Large-scale reactor (Stage 4)
5. **6600L PBR** - Production-scale reactor (Stage 5)
6. **Harvest** - Final harvest stage (Stage 6)

**Key Fields:**
- `batch_number` - PB-YYYY-####
- `strain` - Link to Pluviago Strain
- `current_stage` - Flask / 25L PBR / 275L PBR / 925L PBR / 6600L PBR / Harvest
- `parent_batch` - Link to source batch (genealogy)
- `generation_number` - Generation in lineage
- `status` - Active / Harvested / Disposed / Scaled Up / Contaminated
- `lineage_status` - Active / Returned / Archived
- `final_medium_batch` - Link to FMB used
- `inoculation_date` - Start date
- `inoculation_volume` - Initial culture volume
- `target_volume` - Expected final volume

**Child Table:** `Production Batch QC`
- `qc_date` - When measured
- `stage` - Which cultivation stage
- `par` - Photosynthetically Active Radiation
- `ph` - pH measurement
- `od` - Optical Density
- `cell_count` - Cells per mL
- `cell_size` - Average cell size (μm)
- `dry_weight` - Biomass dry weight (g/L)
- `microscopy_result` - Observations
- `contamination_detected` - Yes/No
- `qc_type` - Process QC / Biological QC

**Stage Decision Fields (per stage):**
- `stage_X_decision` - Proceed / Hold / Dispose / Pending
- `stage_X_decision_date` - When decided
- `stage_X_decision_by` - Who decided
- `stage_X_notes` - Decision rationale

**Workflow:**
1. Production Manager creates Flask batch
2. Links to approved Final Medium Batch
3. Links to Pluviago Strain
4. Records inoculation details
5. **During cultivation:**
   - Lab Technician records QC readings (PAR, pH, OD, cell count)
   - QC Analyst performs microscopy
   - System tracks contamination incidents
6. **Stage decision:**
   - If healthy: stage_X_decision = Proceed → Scale up to next stage
   - If contaminated: stage_X_decision = Dispose → End batch
   - If uncertain: stage_X_decision = Hold → Monitor further
7. **Scale-up:**
   - Creates new Production Batch at next stage
   - parent_batch = current batch
   - generation_number = parent + 1
   - current_stage = next stage
8. **Repeat** through all stages until Harvest

**Special Workflows:**

**Return-to-Cultivation (Back-Propagation):**
- Available from 275L or 6600L stages
- Button: "Return to Flask"
- Withdraws culture volume, dilutes with fresh medium
- Creates new Flask batch (child of source)
- Source batch continues running (both active simultaneously)
- Source lineage_status = Returned
- Tracked via `Cultivation Return Event` DocType

**Batch Splitting:**
- One parent can inoculate multiple child batches
- Creates parallel cultivation runs
- Genealogy shows branching tree structure

---

### Stage 7: Harvest

**DocType:** `Harvest Batch`

**Purpose:** Record harvest from production batch

**Key Fields:**
- `batch_number` - HB-YYYY-####
- `production_batch` - Link to source Production Batch
- `harvest_date` - When harvested
- `harvested_volume` - Volume collected (Litres)
- `harvested_by` - User who performed harvest
- `actual_dry_weight` - Biomass weight (kg)
- `yield_percentage` - Calculated yield
- `qc_status` - Pending / Passed / Failed
- `storage_location` - Where stored
- `storage_temperature` - Storage conditions

**QC Parameters:**
- Biomass quality
- Contamination check
- Moisture content
- Visual inspection

**Workflow:**
1. Production Manager initiates harvest from Production Batch
2. Records harvest details (volume, weight)
3. QC Analyst performs harvest QC
4. **If Pass:** Submit → Available for extraction
5. **If Fail:** Investigate and dispose

---

### Stage 8: Extraction

**DocType:** `Extraction Batch`

**Purpose:** Extract target compounds from harvested biomass

**Key Fields:**
- `batch_number` - EB-YYYY-####
- `harvest_batch` - Link to source Harvest Batch
- `extraction_date` - When performed
- `extraction_method` - Method used
- `solvent_used` - Extraction solvent
- `extracted_volume` - Volume obtained
- `extract_concentration` - Concentration (mg/mL)
- `yield_percentage` - Extraction yield
- `qc_status` - Pending / Passed / Failed

**Workflow:**
1. Lab Technician creates extraction batch
2. Links to approved Harvest Batch
3. Records extraction parameters
4. QC performs final product testing
5. **If Pass:** Submit → Final product ready
6. **If Fail:** Investigate or dispose

---

## Supporting DocTypes

### Pluviago Strain

**Purpose:** Master data for cell culture strains

**Key Fields:**
- `strain_name` - Unique identifier
- `strain_code` - Short code
- `species` - Biological species
- `description` - Strain characteristics
- `optimal_growth_conditions` - Temperature, pH, light
- `status` - Active / Inactive / Archived

---

### Contamination Incident

**Purpose:** Track contamination events during cultivation

**Key Fields:**
- `incident_number` - CI-YYYY-####
- `production_batch` - Affected batch
- `detection_date` - When detected
- `contamination_type` - Bacterial / Fungal / Other
- `severity` - Low / Medium / High / Critical
- `root_cause` - Investigation findings
- `corrective_action` - Actions taken
- `preventive_action` - Future prevention measures
- `status` - Open / Under Investigation / Closed

---

### Cultivation Return Event

**Purpose:** Log return-to-cultivation (back-propagation) events

**Key Fields:**
- `event_number` - CRE-YYYY-####
- `source_batch` - Original production batch (275L or 6600L)
- `returned_batch` - New Flask batch created
- `withdrawal_volume` - Culture volume withdrawn
- `dilution_medium_batch` - Medium used for dilution
- `dilution_volume` - Medium volume added
- `return_date` - When performed
- `returned_by` - User
- `reason` - Why returned to Flask

---

### OOS Investigation

**Purpose:** Out-of-Specification investigation for failed QC

**Key Fields:**
- `investigation_number` - OOS-YYYY-####
- `linked_doctype` - Which batch type
- `linked_batch` - Specific batch
- `parameter_failed` - Which QC parameter
- `failed_value` - Actual value
- `expected_range` - Specification range
- `investigation_by` - Investigator
- `root_cause` - Findings
- `conclusion` - Lab Error / Process Deviation / True OOS
- `disposition` - Retest / Reject / Release with Deviation
- `status` - Open / Under Investigation / Closed

---

### Stock Consumption Log

**Purpose:** Audit trail for all chemical consumption

**Key Fields:**
- `log_number` - SCL-YYYY-####
- `log_date` - Timestamp
- `action` - Consumed / Written Off (Loss) / Reversed
- `raw_material_batch` - Which RMB affected
- `material_name` - Chemical name
- `qty_change` - Negative = deduction, positive = reversal
- `uom` - Unit of measure
- `balance_after` - Remaining qty after this event
- `source_doctype` - Which batch triggered it
- `source_document` - Specific batch number
- `preparation_stage` - A1-A7 / Green / Red / Final
- `performed_by` - User
- `remarks` - Notes

**Read-only for all users** - System-generated only

---

### QC Parameter Spec

**Purpose:** Define QC specifications for different stages

**Key Fields:**
- `parameter_name` - pH / PAR / OD / Cell Count / etc.
- `applicable_stage` - Which stage/batch type
- `min_value` - Lower limit
- `max_value` - Upper limit
- `uom` - Unit of measure
- `test_method` - How to measure
- `frequency` - How often to test

---

## User Roles & Permissions

### Defined Roles

1. **Pluviago Admin** - Full system access
2. **QA Head** - Quality assurance oversight
3. **QC Manager** - QC approval authority
4. **QC Analyst** - Perform QC tests
5. **Production Manager** - Cultivation oversight
6. **Lab Technician** - Prepare media, record data
7. **Store Keeper** - Raw material management

### Permission Matrix

| DocType | Lab Tech | QC Analyst | QC Manager | Prod Manager | Store Keeper |
|---------|----------|------------|------------|--------------|--------------|
| Raw Material Batch | Read | Read/Write | Submit | Read | Create/Write |
| Stock Solution Batch | Create/Write | Write/Submit | Submit | Read | Read |
| Green/Red Medium | Create/Write | Write/Submit | Submit | Read | Read |
| Final Medium Batch | Create/Write | Write/Submit | Submit | Read | Read |
| Production Batch | Write | Write | Read | Create/Submit | Read |
| Harvest Batch | Write | Write/Submit | Create/Submit | Create/Submit | Read |
| Extraction Batch | Create/Write | Write/Submit | Submit | Read | Read |
| Contamination Incident | Create | Write | Submit | Create/Write | Read |
| OOS Investigation | Read | Create/Write | Submit | Read | Read |

---

## Reports

### Production Summary Report
- Lists all production batches with key metrics
- Filters: strain, date range, stage, status
- Columns: batch, strain, stage, generation, inoculation date, harvest date, yield

### QC Compliance Report
- All QC entries across all batch types
- Filters: date range, batch type, QC status, parameter
- Shows: batch, parameter, value, spec range, result, analyst

### Genealogy Report
- Traces lineage from Flask to Harvest
- Shows parent-child relationships
- Displays generation numbers
- Highlights return-to-cultivation events

### Reactor Yield Report
- Yield trends per strain, generation, stage
- Average yield calculations
- Performance metrics

### Chemical Inventory Status
- Current stock levels for all raw materials
- Columns: batch, material, received, consumed, remaining, expiry, status
- Color indicators: red (expired), orange (expiring soon), green (healthy)

### Batch Traceability Report
- Complete audit trail for a specific batch
- All linked batches (upstream and downstream)
- All QC entries
- All consumption logs
- Contamination incidents

---

## Scheduled Tasks

### Daily Tasks (tasks.py)

1. **check_pending_qc()**
   - Finds batches with QC pending > 2 days
   - Sends alert to QC Manager
   - Covers: Production Batch, RMB, Stock Solutions

2. **check_expiry_alerts()**
   - Finds RMBs expiring within 30 days
   - Sends alert to Store Keeper and QC Manager
   - Red alert for already expired

3. **check_low_stock()**
   - Calculates total remaining_qty per chemical
   - Alerts if below min_stock_qty
   - Sends to Store Keeper and Procurement

---

## Key Business Rules

### Stock Consumption
- Chemicals deducted when "Mark Preparation Complete" clicked
- Deduction happens BEFORE QC (reflects physical reality)
- If QC fails → batch marked "Wasted", stock NOT reversed
- Only Draft batches can be cancelled with stock reversal
- UOM must match between ingredient and RMB (no auto-conversion)
- Over-consumption blocked (hard error)

### QC Workflow
- All batches start with qc_status = Pending
- QC must pass before batch can be used downstream
- Failed QC can trigger:
  - Corrective action + re-test
  - OOS investigation
  - Waste/disposal
- QC readings tracked in child tables with timestamps

### Genealogy Tracking
- Every Production Batch has parent_batch (except first Flask)
- generation_number increments with each scale-up
- Return-to-cultivation creates sibling lineage
- Batch splitting creates parallel lineages
- Full traceability from Flask to Extraction

### Stage Progression
- Must complete QC at each stage before proceeding
- Stage decision required: Proceed / Hold / Dispose
- Scale-up creates new batch at next stage
- Harvest ends cultivation pipeline

---

## Implementation Status

### ✅ Completed (Phase 1-3)
- All 21 DocTypes created
- Stock consumption tracking with logs
- QC workflows for all stages
- Genealogy tracking
- Basic reports
- Scheduled tasks
- Custom login page

### 🚧 In Progress
- Return-to-cultivation workflow (Task 2.1)
- Batch splitting (Task 2.2)
- OOS investigation workflow (Task 3.3)
- Enhanced reporting

### 📋 Planned (Phase 4-7)
- Workspace UI enhancements
- BMR print formats
- SOP document linkage
- Field-level role permissions
- Email notification system
- Mobile access optimization

---

## File Locations

### Core Module
```
pluviago/pluviago_biotech/
├── doctype/
│   ├── raw_material_batch/
│   ├── stock_solution_batch/
│   ├── green_medium_batch/
│   ├── red_medium_batch/
│   ├── final_medium_batch/
│   ├── production_batch/
│   ├── harvest_batch/
│   ├── extraction_batch/
│   ├── pluviago_strain/
│   ├── contamination_incident/
│   ├── cultivation_return_event/
│   ├── oos_investigation/
│   ├── stock_consumption_log/
│   ├── qc_parameter_spec/
│   ├── stock_solution_ingredient/
│   ├── medium_direct_ingredient/
│   ├── production_batch_qc/
│   ├── green_medium_qc_entry/
│   ├── red_medium_qc_entry/
│   └── medium_batch_corrective_action/
├── report/
│   ├── production_summary/
│   ├── qc_compliance_report/
│   ├── genealogy_report/
│   └── batch_traceability/
├── utils/
│   └── stock_utils.py
├── workspace/
│   └── pluviago_biotech.json
└── tasks.py
```

### Setup Scripts
```
pluviago/setup/
├── phase1.py  # Core data integrity
├── phase2.py  # Biological workflows
├── phase3.py  # QC improvements
├── phase4.py  # Alerts & notifications
├── phase5.py  # UI/workspace
├── phase6.py  # Compliance & docs
├── phase7.py  # Reporting
└── run_all_phases.py
```

---

## Quick Start Guide

### For Lab Technicians

1. **Receive Raw Materials**
   - Create Raw Material Batch
   - Record supplier, qty, expiry
   - Wait for QC approval

2. **Prepare Stock Solutions**
   - Create Stock Solution Batch (A1-A7)
   - Add ingredients from approved RMBs
   - Mark Preparation Complete
   - Wait for QC

3. **Prepare Media**
   - Create Green/Red Medium Batch
   - Link stock solutions
   - Add direct chemicals
   - Mark Preparation Complete
   - Wait for QC

4. **Prepare Final Medium**
   - Create Final Medium Batch
   - Link approved Green and Red batches
   - Specify mixing ratio
   - Wait for QC

### For Production Managers

1. **Start Cultivation**
   - Create Production Batch (Flask stage)
   - Link to strain and final medium
   - Record inoculation details

2. **Monitor Growth**
   - Record QC readings (PAR, pH, OD, cell count)
   - Make stage decisions (Proceed/Hold/Dispose)

3. **Scale Up**
   - When ready, create next stage batch
   - Link as child of current batch
   - Repeat through all stages

4. **Harvest**
   - Create Harvest Batch
   - Record harvest details
   - Wait for final QC

### For QC Analysts

1. **Test Batches**
   - Perform required QC tests
   - Record results in QC fields
   - Set qc_status = Passed or Failed

2. **Handle Failures**
   - If fail: log corrective action or mark as wasted
   - If needed: create OOS Investigation
   - Re-test if corrective action taken

3. **Approve Releases**
   - Submit approved batches
   - Batches become available for next stage

### For Store Keepers

1. **Manage Inventory**
   - Create RMBs on receipt
   - Monitor expiry alerts
   - Check stock levels
   - Initiate reorders when low

---

## Integration Points

### Frappe/ERPNext Integration
- Uses Frappe framework DocType system
- Integrates with User and Role management
- Uses Frappe notification system
- Leverages Frappe scheduler for tasks
- Uses Frappe print format system

### Potential Future Integrations
- SCADA/bioreactor systems (auto-import readings)
- Laboratory instruments (auto-import QC data)
- Barcode/QR scanning for batch tracking
- Email server for automated notifications
- Mobile apps for floor data entry

---

## Compliance & Audit

### Audit Trail
- All document changes tracked by Frappe
- Stock Consumption Log provides chemical audit trail
- QC entries timestamped with analyst name
- Stage decisions recorded with user and date
- Contamination incidents formally documented

### Regulatory Readiness
- Batch Manufacturing Records (BMR) printable
- Complete traceability from raw material to final product
- QC compliance reporting
- OOS investigation workflow
- SOP linkage capability
- Electronic signatures via Frappe

---

## Support & Maintenance

### Key Documentation
- `TASKS.md` - Implementation task list (24 tasks across 8 phases)
- `STOCK_CONSUMPTION_DESIGN.md` - Stock tracking design
- `CUSTOM_LOGIN_SETUP.md` - Login page setup
- `PROJECT_OVERVIEW.md` - High-level overview
- This file - Complete workspace flow

### Development Workflow
1. Tasks organized in phases (phase1.py - phase7.py)
2. Each phase has setup script for fixtures/data
3. Pre-commit hooks for code quality (ruff, eslint, prettier)
4. Git-based version control

### Testing Approach
- Test scenarios documented in STOCK_CONSUMPTION_DESIGN.md
- Manual testing for each workflow
- QC validation at each stage
- User acceptance testing per role

---

## Glossary

- **RMB** - Raw Material Batch
- **SSB** - Stock Solution Batch
- **GMB** - Green Medium Batch
- **RMB** - Red Medium Batch (context-dependent)
- **FMB** - Final Medium Batch
- **PB** - Production Batch
- **HB** - Harvest Batch
- **EB** - Extraction Batch
- **PBR** - Photobioreactor
- **QC** - Quality Control
- **QA** - Quality Assurance
- **OOS** - Out of Specification
- **BMR** - Batch Manufacturing Record
- **SOP** - Standard Operating Procedure
- **PAR** - Photosynthetically Active Radiation
- **OD** - Optical Density
- **UOM** - Unit of Measure

---

**Document Version:** 1.0  
**Last Updated:** March 30, 2026  
**Status:** Complete workspace mapping  
**Maintained By:** Pluviago Development Team
