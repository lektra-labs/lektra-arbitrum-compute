// SPDX-License-Identifier: MIT
  pragma solidity ^0.8.24;

  contract SettlementEscrow {
      enum JobStatus {
          NONE,
          CREATED,
          RESULT_SUBMITTED,
          PAYMENT_RELEASED
      }

      struct Job {
          address requester;
          address provider;
          uint64 valueWei;
          uint64 challengeWindowSec;
          bytes32 inputSpecHash;
          bytes32 resultHash;
          uint64 energyMicroKwh;
          bytes32 attestationDigest;
          JobStatus status;
      }

      uint256 public nextJobId = 1;
      mapping(uint256 => Job) public jobs;

      event JobCreated(
          uint256 indexed jobId,
          address indexed requester,
          address indexed provider,
          uint64 valueWei,
          uint64 challengeWindowSec,
          bytes32 inputSpecHash
      );

      event ResultSubmitted(
          uint256 indexed jobId,
          bytes32 resultHash,
          uint64 energyMicroKwh,
          bytes32 attestationDigest
      );

      event PaymentReleased(uint256 indexed jobId);

      function createJob(
      address provider,
      uint64 escrowValueWei,
      uint64 challengeWindowSec,
      bytes32 inputSpecHash
  ) external payable returns (uint256 jobId) {
      require(provider != address(0), "provider=0");
      require(escrowValueWei > 0, "value=0");
      require(msg.value > 0, "no value sent");

      jobId = nextJobId++;
      jobs[jobId] = Job({
          requester: msg.sender,
          provider: provider,
          valueWei: uint64(msg.value),
          challengeWindowSec: challengeWindowSec,
          inputSpecHash: inputSpecHash,
          resultHash: bytes32(0),
          energyMicroKwh: 0,
          attestationDigest: bytes32(0),
          status: JobStatus.CREATED
      });

      emit JobCreated(
          jobId,
          msg.sender,
          provider,
          uint64(msg.value),
          challengeWindowSec,
          inputSpecHash
      );
  }

      function submitResult(
          uint256 jobId,
          bytes32 resultHash,
          uint64 energyMicroKwh,
          bytes32 attestationDigest,
          bytes calldata /* signature */
      ) external {
          Job storage j = jobs[jobId];
          require(j.status == JobStatus.CREATED, "not created");
          require(msg.sender == j.provider || msg.sender == j.requester, "not allowed");
          require(resultHash != bytes32(0), "result=0");

          j.resultHash = resultHash;
          j.energyMicroKwh = energyMicroKwh;
          j.attestationDigest = attestationDigest;
          j.status = JobStatus.RESULT_SUBMITTED;

          emit ResultSubmitted(jobId, resultHash, energyMicroKwh, attestationDigest);
      }

      function releasePayment(uint256 jobId) external {
          Job storage j = jobs[jobId];
          require(j.status == JobStatus.RESULT_SUBMITTED, "no result");
          require(msg.sender == j.requester, "only requester");

          j.status = JobStatus.PAYMENT_RELEASED;
          (bool ok, ) = payable(j.provider).call{value: j.valueWei}("");
          require(ok, "transfer failed");

          emit PaymentReleased(jobId);
      }
  }
