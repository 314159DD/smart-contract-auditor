# Sprint 1: Core Scanner — Contract Auditor

**Goal:** Build the Solidity smart contract analysis engine that parses contracts, detects common vulnerabilities using static analysis, and layers AI analysis on top for deeper reasoning. By end of sprint, you can feed in a Solidity file and get a structured vulnerability report.

**Duration:** 2 weeks
**Status:** Not Started

---

## Task 1.1: Solidity Parsing Engine

**Input:** Raw Solidity source files (.sol)
**Output:** Parsed AST with function signatures, state variables, modifiers, and inheritance tree

### Subtasks

- [ ] **1.1.1** Set up Python project structure:
  ```
  smart-contract-auditor/
  ├── src/
  │   ├── parser/
  │   │   ├── solidity.py       # Solidity source parser
  │   │   ├── ast_analyzer.py   # AST traversal and analysis
  │   │   └── models.py         # Contract, Function, Variable dataclasses
  │   ├── detectors/
  │   ├── ai/
  │   ├── reports/
  │   └── config.py
  ├── tests/
  │   └── contracts/            # Sample Solidity files for testing
  ├── requirements.txt
  └── .env.example
  ```
- [ ] **1.1.2** Install and configure solidity parser:
  ```bash
  pip install py-solc-x solcx antlr4-python3-runtime
  # OR use slither-analyzer which includes parsing
  pip install slither-analyzer
  ```
- [ ] **1.1.3** Implement Solidity parser:
  ```python
  class SolidityParser:
      def parse(self, source: str) -> Contract:
          """Parse Solidity source into structured Contract object"""
      def parse_file(self, path: str) -> Contract:
          """Parse a .sol file"""
      def resolve_imports(self, source: str, base_path: str) -> str:
          """Resolve import statements (OpenZeppelin, etc.)"""
  ```
- [ ] **1.1.4** Define Contract model:
  ```python
  @dataclass
  class Contract:
      name: str
      source: str
      compiler_version: str
      functions: list[Function]
      state_variables: list[StateVariable]
      modifiers: list[Modifier]
      events: list[Event]
      inheritance: list[str]        # Parent contract names
      imports: list[str]
      pragma: str

  @dataclass
  class Function:
      name: str
      visibility: str               # public/external/internal/private
      mutability: str               # view/pure/payable/nonpayable
      modifiers: list[str]
      parameters: list[Parameter]
      returns: list[Parameter]
      body_source: str
      line_start: int
      line_end: int
  ```
- [ ] **1.1.5** Handle multi-contract files and inheritance resolution
- [ ] **1.1.6** Create test suite with 5+ sample contracts:
  - Simple ERC-20 token
  - Multi-contract file with inheritance
  - Contract with known vulnerabilities (reentrancy, overflow)
  - OpenZeppelin-based contract with imports
  - Complex DeFi contract (LP, staking)

**Acceptance Criteria:**
- Parser extracts all functions, variables, modifiers from a standard ERC-20
- Inheritance tree is correctly resolved for multi-level inheritance
- Import resolution handles OpenZeppelin paths
- All 5 test contracts parse without errors

---

## Task 1.2: Static Vulnerability Detectors

**Input:** Parsed Contract object
**Output:** List of detected vulnerabilities with severity, location, and description

### Subtasks

- [ ] **1.2.1** Define vulnerability model:
  ```python
  @dataclass
  class Vulnerability:
      detector: str                # Which detector found it
      severity: str                # CRITICAL / HIGH / MEDIUM / LOW / INFO
      title: str                   # Short description
      description: str             # Detailed explanation
      location: str                # Contract.function or line number
      recommendation: str          # How to fix it
      confidence: str              # high / medium / low
      cwe_id: str                  # CWE identifier if applicable
      references: list[str]        # Links to known exploits or docs
  ```
- [ ] **1.2.2** Implement core detectors:
  ```python
  # detectors/
  ├── reentrancy.py          # Reentrancy vulnerabilities
  ├── access_control.py      # Missing access controls, unprotected functions
  ├── overflow.py            # Integer overflow/underflow (pre-0.8.0)
  ├── unchecked_call.py      # Unchecked external call return values
  ├── tx_origin.py           # tx.origin authentication
  ├── selfdestruct.py        # Unprotected selfdestruct
  ├── delegatecall.py        # Dangerous delegatecall patterns
  ├── timestamp.py           # Block timestamp dependence
  ├── gas_limit.py           # Unbounded loops, DoS vectors
  ├── front_running.py       # Front-running vulnerability patterns
  └── base.py                # BaseDetector interface
  ```
- [ ] **1.2.3** Implement reentrancy detector:
  - Check for external calls followed by state changes
  - Check for missing ReentrancyGuard on payable functions
  - Check for cross-function reentrancy (state shared between functions)
  - Severity: CRITICAL
- [ ] **1.2.4** Implement access control detector:
  - Functions that modify state without `onlyOwner` or equivalent
  - Missing zero-address checks on admin functions
  - Unprotected `initialize()` functions (proxy pattern)
  - Severity: HIGH
- [ ] **1.2.5** Implement overflow detector:
  - Flag arithmetic operations in contracts with pragma < 0.8.0
  - Check for unchecked blocks in 0.8.0+ contracts
  - Severity: HIGH (pre-0.8.0), LOW (post-0.8.0 with unchecked)
- [ ] **1.2.6** Implement remaining detectors (unchecked_call, tx_origin, selfdestruct, delegatecall, timestamp, gas_limit, front_running)
- [ ] **1.2.7** Build detector runner:
  ```python
  class DetectorRunner:
      def __init__(self, detectors: list[BaseDetector]):
          self.detectors = detectors

      def run_all(self, contract: Contract) -> list[Vulnerability]:
          """Run all detectors against a parsed contract"""

      def run_detector(self, name: str, contract: Contract) -> list[Vulnerability]:
          """Run a specific detector"""
  ```

**Acceptance Criteria:**
- Reentrancy detector catches classic reentrancy pattern (external call before state update)
- Access control detector flags public state-changing functions without modifiers
- Overflow detector correctly distinguishes pre-0.8.0 and post-0.8.0 contracts
- Each detector produces a Vulnerability with all fields populated
- Test contracts with known vulnerabilities trigger the correct detectors

---

## Task 1.3: AI Analysis Layer

**Input:** Parsed contract + static analysis results
**Output:** AI-enhanced vulnerability analysis with deeper reasoning, business logic review, and fix suggestions

### Subtasks

- [ ] **1.3.1** Implement AI analyzer:
  ```python
  # ai/
  ├── analyzer.py            # Main AI analysis orchestrator
  ├── prompts.py             # Prompt templates for each analysis type
  └── models.py              # AIAnalysis dataclass
  ```
- [ ] **1.3.2** Build analysis prompt template:
  ```
  System: You are an expert smart contract security auditor.

  Analyze the following Solidity contract for:
  1. Business logic vulnerabilities (not just code patterns)
  2. Economic attack vectors (flash loan attacks, oracle manipulation, sandwich attacks)
  3. Centralization risks (admin keys, upgrade patterns, kill switches)
  4. Gas optimization issues
  5. Conformance to best practices (OpenZeppelin patterns, EIP standards)

  Static analysis already found: [list of detected vulnerabilities]

  For each finding:
  - Severity (CRITICAL/HIGH/MEDIUM/LOW/INFO)
  - Detailed explanation of the attack scenario
  - Specific code fix (show before/after)
  - References to similar real-world exploits
  ```
- [ ] **1.3.3** Implement tiered analysis:
  - **Quick scan** (free tier): Static detectors only. No AI. < 5 seconds.
  - **Standard scan** (paid tier): Static + single-pass AI analysis. ~30 seconds.
  - **Deep audit** (premium): Static + multi-pass AI with cross-reference. ~2 minutes.
- [ ] **1.3.4** Implement AI fix generation:
  - For each vulnerability, generate a specific code fix
  - Show before/after code diff
  - Explain why the fix works
- [ ] **1.3.5** Implement confidence scoring:
  - Cross-reference AI findings with static analysis
  - Higher confidence when both AI and static agree
  - Flag AI-only findings as "requires manual review"

**Acceptance Criteria:**
- AI analyzer identifies at least 1 finding NOT caught by static analysis on test contracts
- Each AI finding includes a specific code fix with before/after
- Quick scan completes in < 5 seconds (no API calls)
- Standard scan completes in < 60 seconds
- Deep audit completes in < 3 minutes
- Confidence scoring correctly elevates findings confirmed by both static + AI

---

## Task 1.4: Report Generation

**Input:** Static analysis results + AI analysis results
**Output:** Structured audit report in JSON and Markdown formats

### Subtasks

- [ ] **1.4.1** Define report schema:
  ```python
  @dataclass
  class AuditReport:
      contract_name: str
      contract_address: str | None
      source_hash: str              # SHA256 of source code
      scan_type: str                # quick/standard/deep
      timestamp: datetime
      summary: ReportSummary
      findings: list[Finding]
      contract_info: ContractInfo

  @dataclass
  class ReportSummary:
      total_findings: int
      critical: int
      high: int
      medium: int
      low: int
      info: int
      risk_score: float             # 0-100 (0=safe, 100=extremely risky)
      verdict: str                  # "PASS" / "CAUTION" / "FAIL"
  ```
- [ ] **1.4.2** Implement Markdown report generator:
  - Executive summary with risk score and verdict
  - Findings table sorted by severity
  - Detailed finding sections with code snippets and fixes
  - Contract overview (functions, state variables, inheritance)
  - Methodology section (which detectors ran, AI model used)
- [ ] **1.4.3** Implement JSON report output (for API consumption)
- [ ] **1.4.4** Build audit CLI:
  ```bash
  python -m src.audit scan <file.sol> --type quick
  python -m src.audit scan <file.sol> --type standard --output report.md
  python -m src.audit scan <file.sol> --type deep --output report.json --format json
  python -m src.audit scan --address 0x... --chain ethereum  # Fetch from Etherscan
  ```
- [ ] **1.4.5** Implement Etherscan source code fetcher:
  - Fetch verified contract source from Etherscan API
  - Support Ethereum, Polygon, Arbitrum, Base, Optimism
  - Handle multi-file contracts (flattened or separate)

**Acceptance Criteria:**
- Markdown report is human-readable with clear severity indicators
- JSON report is valid and parseable, includes all fields
- CLI accepts both file path and contract address inputs
- Etherscan fetcher retrieves verified source code for known contracts
- Risk score is calculated consistently (weighted sum of findings by severity)

---

## Sprint 1 Definition of Done

- [ ] Solidity parser handles ERC-20, inheritance, imports
- [ ] 10 static vulnerability detectors are implemented and tested
- [ ] AI analyzer produces findings with code fix suggestions
- [ ] Reports generate in both Markdown and JSON formats
- [ ] CLI scans both local files and Etherscan-verified contracts
- [ ] Test suite covers all detectors with known-vulnerable contracts
- [ ] All code committed with type hints, docstrings, and tests
