// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Complex DeFi Vault — yield-bearing vault with fee tiers and governance
/// @dev Used for parser stress-testing (complex contract structure)

// ── Minimal interfaces ────────────────────────────────────────────────────────

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

interface IStrategy {
    function deposit(uint256 amount) external;
    function withdraw(uint256 amount) external;
    function totalAssets() external view returns (uint256);
    function harvest() external returns (uint256 profit);
}

// ── Governance ────────────────────────────────────────────────────────────────

contract TimelockGovernance {
    uint256 public constant MIN_DELAY = 2 days;

    struct Proposal {
        address target;
        bytes data;
        uint256 eta;
        bool executed;
        bool cancelled;
    }

    mapping(bytes32 => Proposal) public proposals;
    address public admin;
    address public pendingAdmin;

    event ProposalQueued(bytes32 indexed id, address target, uint256 eta);
    event ProposalExecuted(bytes32 indexed id);
    event ProposalCancelled(bytes32 indexed id);

    constructor() {
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    function queue(address target, bytes calldata data, uint256 eta)
        external
        onlyAdmin
        returns (bytes32 id)
    {
        require(eta >= block.timestamp + MIN_DELAY, "Delay too short");
        id = keccak256(abi.encode(target, data, eta));
        proposals[id] = Proposal(target, data, eta, false, false);
        emit ProposalQueued(id, target, eta);
    }

    function execute(bytes32 id) external onlyAdmin {
        Proposal storage p = proposals[id];
        require(!p.executed && !p.cancelled, "Invalid state");
        require(block.timestamp >= p.eta, "Not ready");
        p.executed = true;
        (bool ok, ) = p.target.call(p.data);
        require(ok, "Execution failed");
        emit ProposalExecuted(id);
    }

    function cancel(bytes32 id) external onlyAdmin {
        proposals[id].cancelled = true;
        emit ProposalCancelled(id);
    }

    function setPendingAdmin(address newAdmin) external onlyAdmin {
        pendingAdmin = newAdmin;
    }

    function acceptAdmin() external {
        require(msg.sender == pendingAdmin, "Not pending admin");
        admin = pendingAdmin;
        pendingAdmin = address(0);
    }
}

// ── Vault share token ─────────────────────────────────────────────────────────

contract VaultShares is IERC20 {
    string public constant name = "Vault Share";
    string public constant symbol = "vSHARE";
    uint8 public constant decimals = 18;

    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    address public immutable vault;

    modifier onlyVault() {
        require(msg.sender == vault, "Not vault");
        _;
    }

    constructor(address _vault) {
        vault = _vault;
    }

    function totalSupply() external view override returns (uint256) { return _totalSupply; }
    function balanceOf(address a) external view override returns (uint256) { return _balances[a]; }
    function allowance(address o, address s) external view override returns (uint256) { return _allowances[o][s]; }

    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    function approve(address spender, uint256 amount) external override returns (bool) {
        _allowances[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        require(_allowances[from][msg.sender] >= amount, "Allowance");
        _allowances[from][msg.sender] -= amount;
        _transfer(from, to, amount);
        return true;
    }

    function mint(address to, uint256 amount) external onlyVault {
        _balances[to] += amount;
        _totalSupply += amount;
    }

    function burn(address from, uint256 amount) external onlyVault {
        require(_balances[from] >= amount, "Insufficient");
        _balances[from] -= amount;
        _totalSupply -= amount;
    }

    function _transfer(address from, address to, uint256 amount) internal {
        require(_balances[from] >= amount, "Insufficient");
        _balances[from] -= amount;
        _balances[to] += amount;
    }
}

// ── Main vault ────────────────────────────────────────────────────────────────

contract DeFiVault is TimelockGovernance {
    // ── Constants ───────────────────────────────────────────────────────────
    uint256 public constant MAX_BPS = 10_000;
    uint256 public constant PERFORMANCE_FEE_CAP = 2_000; // 20%
    uint256 public constant WITHDRAWAL_FEE_CAP = 100;    // 1%
    uint256 public constant PRECISION = 1e18;

    // ── State ────────────────────────────────────────────────────────────────
    IERC20 public immutable asset;
    VaultShares public immutable shares;
    IStrategy public strategy;

    uint256 public performanceFeeBps = 1_000; // 10%
    uint256 public withdrawalFeeBps = 50;     // 0.5%
    address public treasury;
    bool public paused;

    uint256 public totalDeposited;
    uint256 public totalFeesClaimed;
    uint256 public lastHarvestBlock;

    mapping(address => uint256) public userDeposited;
    mapping(address => uint256) public userRewardDebt;

    // ── Events ───────────────────────────────────────────────────────────────
    event Deposited(address indexed user, uint256 assets, uint256 sharesIssued);
    event Withdrawn(address indexed user, uint256 assets, uint256 sharesBurned, uint256 fee);
    event Harvested(uint256 profit, uint256 fee);
    event StrategyUpdated(address oldStrategy, address newStrategy);
    event FeeUpdated(string feeType, uint256 oldBps, uint256 newBps);

    constructor(address _asset, address _treasury) {
        asset = IERC20(_asset);
        treasury = _treasury;
        shares = new VaultShares(address(this));
    }

    // ── Modifiers ─────────────────────────────────────────────────────────────
    modifier notPaused() {
        require(!paused, "Paused");
        _;
    }

    modifier validStrategy() {
        require(address(strategy) != address(0), "No strategy");
        _;
    }

    // ── Deposit / Withdraw ────────────────────────────────────────────────────

    function deposit(uint256 assets) external notPaused returns (uint256 sharesOut) {
        require(assets > 0, "Zero assets");
        uint256 totalBefore = _totalAssets();
        asset.transferFrom(msg.sender, address(this), assets);

        // ERC-4626 share math: shares = assets * totalShares / totalAssets
        uint256 supply = shares.totalSupply();
        sharesOut = supply == 0
            ? assets
            : (assets * supply) / totalBefore;

        shares.mint(msg.sender, sharesOut);
        userDeposited[msg.sender] += assets;
        totalDeposited += assets;

        if (address(strategy) != address(0)) {
            asset.approve(address(strategy), assets);
            strategy.deposit(assets);
        }

        emit Deposited(msg.sender, assets, sharesOut);
    }

    function withdraw(uint256 sharesIn) external notPaused returns (uint256 assetsOut) {
        require(sharesIn > 0, "Zero shares");
        uint256 supply = shares.totalSupply();
        require(supply > 0, "No shares");

        assetsOut = (sharesIn * _totalAssets()) / supply;
        shares.burn(msg.sender, sharesIn);

        // Withdrawal fee
        uint256 fee = (assetsOut * withdrawalFeeBps) / MAX_BPS;
        assetsOut -= fee;

        if (address(strategy) != address(0) && _localBalance() < assetsOut + fee) {
            strategy.withdraw(assetsOut + fee - _localBalance());
        }

        if (fee > 0) {
            asset.transfer(treasury, fee);
            totalFeesClaimed += fee;
        }
        asset.transfer(msg.sender, assetsOut);

        emit Withdrawn(msg.sender, assetsOut, sharesIn, fee);
    }

    // ── Yield management ──────────────────────────────────────────────────────

    function harvest() external validStrategy notPaused {
        require(block.number > lastHarvestBlock, "Already harvested this block");
        lastHarvestBlock = block.number;

        uint256 profit = strategy.harvest();
        if (profit > 0) {
            uint256 fee = (profit * performanceFeeBps) / MAX_BPS;
            if (fee > 0) {
                asset.transferFrom(address(strategy), treasury, fee);
                totalFeesClaimed += fee;
            }
            emit Harvested(profit, fee);
        }
    }

    // ── View helpers ──────────────────────────────────────────────────────────

    function pricePerShare() external view returns (uint256) {
        uint256 supply = shares.totalSupply();
        if (supply == 0) return PRECISION;
        return (_totalAssets() * PRECISION) / supply;
    }

    function previewDeposit(uint256 assets) external view returns (uint256) {
        uint256 supply = shares.totalSupply();
        if (supply == 0) return assets;
        return (assets * supply) / _totalAssets();
    }

    function previewWithdraw(uint256 sharesIn) external view returns (uint256 net, uint256 fee) {
        uint256 gross = (sharesIn * _totalAssets()) / shares.totalSupply();
        fee = (gross * withdrawalFeeBps) / MAX_BPS;
        net = gross - fee;
    }

    function _totalAssets() internal view returns (uint256) {
        uint256 local = _localBalance();
        uint256 inStrategy = address(strategy) != address(0) ? strategy.totalAssets() : 0;
        return local + inStrategy;
    }

    function _localBalance() internal view returns (uint256) {
        return asset.balanceOf(address(this));
    }

    // ── Admin ─────────────────────────────────────────────────────────────────

    function setStrategy(address newStrategy) external onlyAdmin {
        require(newStrategy != address(0), "Zero address");
        if (address(strategy) != address(0)) {
            // Withdraw all from old strategy
            uint256 inOld = strategy.totalAssets();
            if (inOld > 0) strategy.withdraw(inOld);
        }
        emit StrategyUpdated(address(strategy), newStrategy);
        strategy = IStrategy(newStrategy);
    }

    function setPerformanceFee(uint256 newBps) external onlyAdmin {
        require(newBps <= PERFORMANCE_FEE_CAP, "Exceeds cap");
        emit FeeUpdated("performance", performanceFeeBps, newBps);
        performanceFeeBps = newBps;
    }

    function setWithdrawalFee(uint256 newBps) external onlyAdmin {
        require(newBps <= WITHDRAWAL_FEE_CAP, "Exceeds cap");
        emit FeeUpdated("withdrawal", withdrawalFeeBps, newBps);
        withdrawalFeeBps = newBps;
    }

    function setTreasury(address newTreasury) external onlyAdmin {
        require(newTreasury != address(0), "Zero address");
        treasury = newTreasury;
    }

    function setPaused(bool _paused) external onlyAdmin {
        paused = _paused;
    }

    function emergencyWithdrawAll() external onlyAdmin {
        if (address(strategy) != address(0)) {
            uint256 inStrategy = strategy.totalAssets();
            if (inStrategy > 0) strategy.withdraw(inStrategy);
        }
        paused = true;
    }
}
