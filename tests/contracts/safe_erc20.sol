// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/// @title A simple safe ERC-20 token (no known vulnerabilities)
contract SafeToken is ERC20, Ownable, ReentrancyGuard {
    uint256 public constant MAX_SUPPLY = 100_000_000 ether;

    constructor(address initialOwner)
        ERC20("SafeToken", "SAFE")
        Ownable(initialOwner)
    {}

    /// @notice Mint new tokens — only owner
    function mint(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "Zero address");
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
    }

    /// @notice Burn tokens from caller's balance
    function burn(uint256 amount) external {
        _burn(msg.sender, amount);
    }

    /// @notice Withdraw accidentally sent ETH — only owner
    function rescueETH() external onlyOwner nonReentrant {
        uint256 bal = address(this).balance;
        require(bal > 0, "No ETH");
        (bool ok, ) = owner().call{value: bal}("");
        require(ok, "Transfer failed");
    }
}
