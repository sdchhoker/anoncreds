import pytest

from anoncreds.protocol.types import ProofInput
from anoncreds.protocol.utils import groupIdentityG1
from anoncreds.test.conftest import presentProofAndVerify


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testIssueRevocationCredential(claimsProver1Gvt, issuerGvt,
                                        claimDefGvtId):
    nonRevocClaimGvtProver1 = claimsProver1Gvt.nonRevocClaim
    acc = await issuerGvt.wallet.getAccumulator(claimDefGvtId)
    tails = await issuerGvt.wallet.getTails(claimDefGvtId)
    assert nonRevocClaimGvtProver1
    assert nonRevocClaimGvtProver1.witness
    assert nonRevocClaimGvtProver1.witness.V
    assert nonRevocClaimGvtProver1.i == 1
    assert nonRevocClaimGvtProver1.witness.gi == tails[1]

    assert acc.V
    assert acc.acc != 1

    assert nonRevocClaimGvtProver1.witness.V == acc.V


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testRevoce(claimsProver1Gvt, issuerGvt, claimDefGvtId):
    await issuerGvt.revoke(claimDefGvtId, 1)
    newAcc = await issuerGvt.wallet.getAccumulator(claimDefGvtId)
    assert not newAcc.V
    assert newAcc.acc == groupIdentityG1()


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testUpdateWitnessNotChangedIfInSync(claimsProver1Gvt, claimDefGvtId,
                                              prover1):
    nonRevocClaimGvtProver1 = claimsProver1Gvt.nonRevocClaim
    acc = await prover1.wallet.getAccumulator(claimDefGvtId)

    # not changed as in sync
    oldOmega = nonRevocClaimGvtProver1.witness.omega

    c2 = await prover1._nonRevocProofBuilder.updateNonRevocationClaim(
        claimDefGvtId.claimDefKey,
        nonRevocClaimGvtProver1)
    assert c2.witness.V == acc.V
    assert oldOmega == c2.witness.omega


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testUpdateWitnessChangedIfOutOfSync(claimsProver1Gvt, issuerGvt,
                                              claimDefGvtId, prover1):
    nonRevocClaimGvtProver1 = claimsProver1Gvt.nonRevocClaim
    acc = await issuerGvt.wallet.getAccumulator(claimDefGvtId)

    # not in sync
    acc.V.add(3)
    assert nonRevocClaimGvtProver1.witness.V != acc.V

    # witness is updated
    oldOmega = nonRevocClaimGvtProver1.witness.omega
    c2 = await prover1._nonRevocProofBuilder.updateNonRevocationClaim(
        claimDefGvtId.claimDefKey,
        nonRevocClaimGvtProver1)
    assert c2.witness.V == acc.V
    assert oldOmega != c2.witness.omega


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testUpdateRevocedWitness(claimsProver1Gvt, issuerGvt, claimDefGvtId,
                                   prover1):
    nonRevocClaimGvtProver1 = claimsProver1Gvt.nonRevocClaim
    await issuerGvt.revoke(claimDefGvtId, 1)
    with pytest.raises(ValueError):
        await prover1._nonRevocProofBuilder.updateNonRevocationClaim(
            claimDefGvtId.claimDefKey, nonRevocClaimGvtProver1)


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testInitNonRevocClaim(claimDefGvtId, prover1, issuerGvt,
                                attrsProver1Gvt, keysGvt, issueAccumulatorGvt):
    claimsReq = await prover1.createClaimRequest(claimDefGvtId)
    claims = await issuerGvt.issueClaim(claimDefGvtId, claimsReq)

    oldV = claims.nonRevocClaim.v
    await prover1.processClaim(claimDefGvtId, claims)
    newC2 = (await prover1.wallet.getClaims(claimDefGvtId)).nonRevocClaim
    vrPrime = (
        await prover1.wallet.getNonRevocClaimInitData(claimDefGvtId)).vPrime

    assert oldV + vrPrime == newC2.v


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testCAndTauList(claimsProver1Gvt, claimDefGvtId, prover1):
    nonRevocClaimGvtProver1 = claimsProver1Gvt.nonRevocClaim
    proofRevBuilder = prover1._nonRevocProofBuilder
    assert await proofRevBuilder.testProof(claimDefGvtId.claimDefKey,
                                           nonRevocClaimGvtProver1)


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testRevocedWithUpdateWitness(claimDefGvtId, issuerGvt, prover1,
                                       verifier, claimsProver1Gvt):
    await issuerGvt.revoke(claimDefGvtId, 1)

    proofInput = ProofInput(['name'], [])
    with pytest.raises(ValueError):
        await presentProofAndVerify(verifier, proofInput, prover1)


@pytest.mark.skipif('sys.platform == "win32"', reason='SOV-86')
@pytest.mark.asyncio
async def testRevocedWithoutUpdateWitness(claimDefGvtId, issuerGvt, prover1,
                                          verifier, claimsProver1Gvt):
    proofInput = ProofInput(['name'], [])
    nonce = verifier.generateNonce()
    proof, revealedAttrs = await prover1.presentProof(proofInput, nonce)

    await issuerGvt.revoke(claimDefGvtId, 1)

    return await verifier.verify(proofInput, proof, revealedAttrs, nonce)
