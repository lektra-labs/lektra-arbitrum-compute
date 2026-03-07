// SPDX-License-Identifier: MIT
  pragma solidity ^0.8.24;

  import "forge-std/Script.sol";
  import "../src/SettlementEscrow.sol";

  contract Deploy is Script {
      function run() external returns (SettlementEscrow deployed) {
          uint256 pk = vm.envUint("DEPLOYER_PRIVATE_KEY");

          vm.startBroadcast(pk);
          deployed = new SettlementEscrow();
          vm.stopBroadcast();
      }
  }
