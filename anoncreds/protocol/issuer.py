from typing import Sequence

from anoncreds.protocol.attribute_repo import AttrRepo
from anoncreds.protocol.credential_definition import CredentialDefinition, getDeserializedSK, getPPrime, getQPrime
from anoncreds.protocol.globals import LARGE_VPRIME_PRIME, LARGE_E_START, LARGE_E_END_RANGE
from anoncreds.protocol.types import CredDefPublicKey
from anoncreds.protocol.utils import get_prime_in_range, strToCharmInteger
from charm.core.math.integer import integer, randomBits


class Issuer:
    def __init__(self, id, attributeRepo: AttrRepo=None):
        self.id = id
        self.credDefs = {}              # Dict[Tuple, CredentialDefinition]
        self.credDefsForAttribs = {}    # Dict[Tuple, List]
        self.attributeRepo = attributeRepo

    def _addCredDef(self, credDef: CredentialDefinition):
        self.credDefs[(credDef.name, credDef.version)] = credDef
        key = tuple(sorted(credDef.attrNames))
        if key not in self.credDefsForAttribs:
            self.credDefsForAttribs[key] = []
        self.credDefsForAttribs[key].append(credDef)

    def addNewCredDef(self, attrNames, name, version,
                   p_prime=None, q_prime=None, ip=None, port=None):
        credDef = CredentialDefinition(attrNames, name, version,
                                       p_prime, q_prime, ip, port)
        self._addCredDef(credDef)
        return credDef

    def getCredDef(self, name=None, version=None, attributes: Sequence[str]=None):
        if name and version:
            return self.credDefs[(name, version)]
        else:
            defs = self.credDefsForAttribs.get(tuple(sorted(attributes)))
            return defs[-1] if defs else None

    def createCred(self, proverId, name, version, U):
        # This method works for one credDef only.
        credDef = self.getCredDef(name, version)
        attributes = self.attributeRepo.getAttributes(proverId)
        encAttrs = attributes.encoded()
        return Issuer.generateCredential(
            U, next(iter(encAttrs.values())), credDef.PK, None, credDef.p_prime,
            credDef.q_prime)

    @classmethod
    def generateCredential(cls, uValue, attributes, pk, sk=None, p_prime=None, q_prime=None):
        """
        Issue the credential for the defined attributes

        :param u: The `u` value provided by the prover
        :param attrs: The attributes for which the credential needs to be generated
        :return: The presentation token as a combination of (A, e, vprimeprime)
        """
        u = strToCharmInteger(uValue) if isinstance(uValue, str) else uValue

        if sk:
            sk = getDeserializedSK(sk)
            p_prime, q_prime = getPPrime(sk), getQPrime(sk)

        if not u:
            raise ValueError("u must be provided to issue a credential")
        # Generate a random prime and
        # Set the Most-significant-bit to 1
        vprimeprime = integer(randomBits(LARGE_VPRIME_PRIME) |
                              (2 ** (LARGE_VPRIME_PRIME - 1)))
        # Generate prime number in the range (2^596, 2^596 + 2^119)
        estart = 2 ** LARGE_E_START
        eend = (estart + 2 ** LARGE_E_END_RANGE)
        e = get_prime_in_range(estart, eend)
        A = Issuer._sign(pk, attributes, vprimeprime, u, e, p_prime, q_prime)
        return A, e, vprimeprime

    # @classmethod
    # def generateCredential(cls, uValue, attributes, pk, sk):
    #     sk = getDeserializedSK(sk)
    #     p_prime, q_prime = getPPrime(sk), getQPrime(sk)
    #     return Issuer.generateCredential(uValue, attributes, pk, p_prime, q_prime)



    def _sign(pk: CredDefPublicKey, attrs, v, u, e, p_prime, q_prime):
        Rx = 1 % pk.N
        # Get the product sequence for the (R[i] and attrs[i]) combination
        for k, val in attrs.items():
            Rx = Rx * (pk.R[str(k)] ** val)
        if u != 0:
            u = u % pk.N
            Rx *= u
        nprime = p_prime * q_prime
        einverse = e % nprime
        Q = pk.Z / (Rx * (pk.S ** v)) % pk.N
        A = Q ** (einverse ** -1) % pk.N
        return A

