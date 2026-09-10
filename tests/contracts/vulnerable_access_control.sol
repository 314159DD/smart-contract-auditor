// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Missing access control vulnerabilities
/// @dev VULNERABLE — for testing only. DO NOT DEPLOY.
contract VulnerableToken {
    address public owner;
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    constructor() {
        owner = msg.sender;
    }

    /// @dev VULNERABLE: anyone can mint tokens — no onlyOwner
    function mint(address to, uint256 amount) public {
        balances[to] += amount;
        totalSupply += amount;
    }

    /// @dev VULNERABLE: no zero-address check on setOwner
    function setOwner(address newOwner) public {
        // Missing: require(newOwner != address(0));
        // Missing: require(msg.sender == owner);
        owner = newOwner;
    }

    /// @dev VULNERABLE: unprotected initialize — proxy pattern attack surface
    function initialize(address _owner) public {
        owner = _owner;
        totalSupply = 1_000_000 ether;
        balances[_owner] = totalSupply;
    }

    function burn(address from, uint256 amount) public {
        // No access control
        require(balances[from] >= amount, "Insufficient");
        balances[from] -= amount;
        totalSupply -= amount;
    }
}
