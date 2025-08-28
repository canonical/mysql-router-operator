# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

"""Relation to TLS certificate provider"""

import base64
import dataclasses
import json
import logging
import re
import socket
import typing

import charms.tls_certificates_interface.v2.tls_certificates as tls_certificates
import ops

import relations.secrets

if typing.TYPE_CHECKING:
    import abstract_charm

logger = logging.getLogger(__name__)

_PEER_RELATION_ENDPOINT_NAME = "tls"

_TLS_REQUESTED_CSR = "tls-requested-csr"
_TLS_ACTIVE_CSR = "tls-active-csr"
_TLS_CERTIFICATE = "tls-certificate"
_TLS_CA = "tls-ca"
_TLS_CHAIN = "tls-chain"
_TLS_PRIVATE_KEY = "tls-private-key"
_TLS_FIELDS = [
    _TLS_REQUESTED_CSR,
    _TLS_ACTIVE_CSR,
    _TLS_CERTIFICATE,
    _TLS_CA,
    _TLS_CHAIN,
    _TLS_PRIVATE_KEY,
]


def _generate_private_key() -> str:
    """Generate TLS private key."""
    return tls_certificates.generate_private_key().decode("utf-8")


# TODO python3.10 min version: Add `(kw_only=True)`
@dataclasses.dataclass
class _Relation:
    """Relation to TLS certificate provider"""

    _charm: "abstract_charm.MySQLRouterCharm"
    _interface: tls_certificates.TLSCertificatesRequiresV2
    _secrets: relations.secrets.RelationSecrets

    @property
    def certificate_saved(self) -> bool:
        """Whether a TLS certificate is available to use"""
        for value in (
            self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_CERTIFICATE),
            self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_CA),
        ):
            if not value:
                return False
        return True

    @property
    def key(self) -> str:
        """The TLS private key"""
        private_key = self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_PRIVATE_KEY)
        if not private_key:
            private_key = _generate_private_key()
            self._secrets.set_value(relations.secrets.UNIT_SCOPE, _TLS_PRIVATE_KEY, private_key)
        return private_key

    @property
    def certificate(self) -> str:
        """The TLS certificate"""
        return self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_CERTIFICATE)

    @property
    def certificate_authority(self) -> str:
        """The TLS certificate authority"""
        return self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_CA)

    def save_certificate(self, event: tls_certificates.CertificateAvailableEvent) -> None:
        """Save TLS certificate in peer relation unit databag."""
        if (
            event.certificate_signing_request.strip()
            != self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_REQUESTED_CSR).strip()
        ):
            logger.warning("Unknown certificate received. Ignoring.")
            return
        if (
            self.certificate_saved
            and event.certificate_signing_request.strip()
            == self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_ACTIVE_CSR)
        ):
            # Workaround for https://github.com/canonical/tls-certificates-operator/issues/34
            logger.debug("TLS certificate already saved.")
            return
        logger.debug(f"Saving TLS certificate {event=}")
        self._secrets.set_value(relations.secrets.UNIT_SCOPE, _TLS_CERTIFICATE, event.certificate)
        self._secrets.set_value(relations.secrets.UNIT_SCOPE, _TLS_CA, event.ca)
        self._secrets.set_value(relations.secrets.UNIT_SCOPE, _TLS_CHAIN, json.dumps(event.chain))
        self._secrets.set_value(
            relations.secrets.UNIT_SCOPE,
            _TLS_ACTIVE_CSR,
            self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_REQUESTED_CSR),
        )
        logger.debug(f"Saved TLS certificate {event=}")
        self._charm.reconcile(event=None)

    def _generate_csr(self, *, event, key: bytes) -> bytes:
        """Generate certificate signing request (CSR)."""
        sans_ip = ["127.0.0.1"]  # needed for the HTTP server when related with COS
        if self._charm.is_externally_accessible(event=event):
            sans_ip.append(self._charm.host_address)

        return tls_certificates.generate_csr(
            private_key=key,
            subject=socket.getfqdn(),
            organization=self._charm.app.name,
            sans_ip=sans_ip,
        )

    def request_certificate_creation(self, *, event):
        """Request new TLS certificate from related provider charm."""
        logger.debug("Requesting TLS certificate creation")
        csr = self._generate_csr(event=event, key=self.key.encode("utf-8"))
        self._interface.request_certificate_creation(certificate_signing_request=csr)
        self._secrets.set_value(
            relations.secrets.UNIT_SCOPE, _TLS_REQUESTED_CSR, csr.decode("utf-8")
        )
        logger.debug("Requested TLS certificate creation")

    def request_certificate_renewal(self, *, event):
        """Request TLS certificate renewal from related provider charm."""
        logger.debug("Requesting TLS certificate renewal")
        old_csr = self._secrets.get_value(relations.secrets.UNIT_SCOPE, _TLS_ACTIVE_CSR).encode(
            "utf-8"
        )
        new_csr = self._generate_csr(event=event, key=self.key.encode("utf-8"))
        self._interface.request_certificate_renewal(
            old_certificate_signing_request=old_csr, new_certificate_signing_request=new_csr
        )
        self._secrets.set_value(
            relations.secrets.UNIT_SCOPE, _TLS_REQUESTED_CSR, new_csr.decode("utf-8")
        )
        logger.debug("Requested TLS certificate renewal")


class RelationEndpoint(ops.Object):
    """Relation endpoint and handlers for TLS certificate provider"""

    NAME = "certificates"

    def __init__(self, charm_: "abstract_charm.MySQLRouterCharm") -> None:
        super().__init__(charm_, self.NAME)
        self._charm = charm_
        self._interface = tls_certificates.TLSCertificatesRequiresV2(self._charm, self.NAME)

        self._secrets = relations.secrets.RelationSecrets(
            charm_,
            _PEER_RELATION_ENDPOINT_NAME,
            unit_secret_fields=[_TLS_PRIVATE_KEY],
        )

        self.framework.observe(
            self._charm.on["set-tls-private-key"].action,
            self._on_set_tls_private_key,
        )
        self.framework.observe(
            self._charm.on[self.NAME].relation_created, self._on_tls_relation_created
        )
        self.framework.observe(
            self._charm.on[self.NAME].relation_broken, self._on_tls_relation_broken
        )

        self.framework.observe(
            self._interface.on.certificate_available, self._on_certificate_available
        )
        self.framework.observe(
            self._interface.on.certificate_expiring, self._on_certificate_expiring
        )

    @property
    def _relation(self) -> typing.Optional[_Relation]:
        if not self._charm.model.get_relation(self.NAME):
            return
        return _Relation(
            _charm=self._charm,
            _interface=self._interface,
            _secrets=self._secrets,
        )

    @property
    def certificate_saved(self) -> bool:
        """Whether a TLS certificate is available to use"""
        if self._relation is None:
            return False
        return self._relation.certificate_saved

    @property
    def key(self) -> typing.Optional[str]:
        """The TLS private key"""
        if self._relation is None:
            return None
        return self._relation.key

    @property
    def certificate(self) -> typing.Optional[str]:
        """The TLS certificate"""
        if self._relation is None:
            return None
        return self._relation.certificate

    @property
    def certificate_authority(self) -> typing.Optional[str]:
        """The TLS certificate authority"""
        if self._relation is None:
            return None
        return self._relation.certificate_authority

    @staticmethod
    def _parse_tls_key(raw_content: str) -> str:
        """Parse TLS key from plain text or base64 format."""
        if re.match(r"(-+(BEGIN|END) [A-Z ]+-+)", raw_content):
            return re.sub(
                r"(-+(BEGIN|END) [A-Z ]+-+)",
                "\n\\1\n",
                raw_content,
            )
        return base64.b64decode(raw_content).decode("utf-8")

    def _on_set_tls_private_key(self, event: ops.ActionEvent) -> None:
        """Handle action to set unit TLS private key."""
        logger.debug("Handling set TLS private key action")
        if key := event.params.get("internal-key"):
            key = self._parse_tls_key(key)
        else:
            key = _generate_private_key()
            event.log("No key provided. Generated new key.")
            logger.debug("No TLS key provided via action. Generated new key.")
        self._secrets.set_value(relations.secrets.UNIT_SCOPE, _TLS_PRIVATE_KEY, key)
        event.log("Saved TLS private key")
        logger.debug("Saved TLS private key")
        if self._relation is None:
            event.log(
                "No TLS certificate relation active. Relate a certificate provider charm to enable TLS."
            )
            logger.debug("No TLS certificate relation active. Skipped certificate request")
        else:
            try:
                self._relation.request_certificate_creation(event=event)
            except Exception as e:
                event.fail(f"Failed to request certificate: {e}")
                logger.exception(
                    "Failed to request certificate after TLS private key set via action"
                )
                raise
        logger.debug("Handled set TLS private key action")

    def _on_tls_relation_created(self, event) -> None:
        """Request certificate when TLS relation created."""
        self._relation.request_certificate_creation(event=event)

    def _on_tls_relation_broken(self, _) -> None:
        """Delete TLS certificate."""
        logger.debug("Deleting TLS certificate")
        for field in _TLS_FIELDS:
            self._secrets.set_value(relations.secrets.UNIT_SCOPE, field, None)
        self._charm.reconcile(event=None)
        logger.debug("Deleted TLS certificate")

    def _on_certificate_available(self, event: tls_certificates.CertificateAvailableEvent) -> None:
        """Save TLS certificate."""
        self._relation.save_certificate(event)

    def _on_certificate_expiring(self, event: tls_certificates.CertificateExpiringEvent) -> None:
        """Request the new certificate when old certificate is expiring."""
        if event.certificate != self.certificate:
            logger.warning("Unknown certificate expiring")
            return

        self._relation.request_certificate_renewal(event=event)
