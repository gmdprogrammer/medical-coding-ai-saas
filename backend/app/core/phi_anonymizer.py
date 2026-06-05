"""
PHI Anonymization Module
━━━━━━━━━━━━━━━━━━━━━━
Implements a layered approach to detect and remove Protected Health Information
(PHI) per HIPAA's 18 Safe Harbor identifiers:

Layer 1 — Regex patterns for deterministic identifiers (SSN, phone, MRN, dates, etc.)
Layer 2 — Microsoft Presidio NLP-based entity recognition (names, addresses, orgs)
Layer 3 — spaCy NER for additional context-aware detection

All PHI is replaced with typed placeholders ("[NAME]", "[PHONE]", etc.)
so clinical meaning is preserved while identifiers are stripped.
"""

import re
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger


@dataclass
class AnonymizationResult:
    original_hash: str          # SHA-256 of original — for audit without storing PHI
    anonymized_text: str
    phi_found: bool
    entities_removed: list[str] = field(default_factory=list)


class PHIAnonymizer:
    """
    Multi-layer PHI anonymizer aligned with HIPAA 45 CFR §164.514(b).
    Falls back gracefully if Presidio / spaCy are unavailable at runtime.
    """

    # ── Regex patterns for structured PHI ────────────────────────────────────
    _PATTERNS: list[tuple[str, str, str]] = [
        # (label, pattern, replacement)
        ("SSN",         r"\b\d{3}-\d{2}-\d{4}\b",                          "[SSN]"),
        ("SSN_NODASH",  r"\b\d{9}\b(?=\s|$)",                              "[SSN]"),
        ("PHONE",       r"\b(\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[PHONE]"),
        ("EMAIL",       r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",   "[EMAIL]"),
        ("ZIP",         r"\b\d{5}(?:-\d{4})?\b",                           "[ZIP]"),
        ("DATE",        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2},? \d{4})\b", "[DATE]"),
        ("MRN",         r"\bMRN[:#\s]*\d{5,12}\b",                         "[MRN]"),
        ("NPI",         r"\bNPI[:#\s]*\d{10}\b",                            "[NPI]"),
        ("DEA",         r"\b[A-Z]{2}\d{7}\b",                              "[DEA]"),
        ("IP_ADDR",     r"\b(?:\d{1,3}\.){3}\d{1,3}\b",                    "[IP]"),
        ("URL",         r"https?://[^\s]+",                                 "[URL]"),
        ("CREDIT_CARD", r"\b(?:\d{4}[-\s]?){3}\d{4}\b",                    "[CC]"),
        ("ACCT_NUM",    r"\b(?:account|acct|acc)[\s#:]*\d{6,20}\b",        "[ACCOUNT]"),
        ("FAX",         r"\b(?:fax|fax#|f:)[\s:]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b", "[FAX]"),
        ("AGE_OVER_89", r"\b(?:1[01]\d|120)\s*(?:year|yr)s?\s*old\b",     "[AGE_OVER_89]"),
    ]

    def __init__(self, use_presidio: bool = True, use_spacy: bool = True):
        self._compiled = [
            (label, re.compile(pattern, re.IGNORECASE), replacement)
            for label, pattern, replacement in self._PATTERNS
        ]
        self._presidio_analyzer = None
        self._presidio_anonymizer = None
        self._nlp = None

        if use_presidio:
            self._init_presidio()
        if use_spacy:
            self._init_spacy()

    # ── Initializers (fail-safe) ──────────────────────────────────────────────

    def _init_presidio(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_analyzer.nlp_engine import NlpEngineProvider
            from presidio_anonymizer import AnonymizerEngine

            # Configure Presidio to use the small spaCy model (always installed).
            # By default Presidio tries en_core_web_lg which may not be present.
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            self._presidio_analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self._presidio_anonymizer = AnonymizerEngine()
            logger.info("Presidio analyzer initialized (en_core_web_sm)")
        except Exception as exc:
            logger.warning(f"Presidio unavailable — regex+spaCy-only mode: {exc}")

    def _init_spacy(self) -> None:
        try:
            import spacy
            # Try small model first (always installed), then large if available
            for model_name in ("en_core_web_sm", "en_core_web_lg"):
                try:
                    self._nlp = spacy.load(model_name)
                    logger.info(f"spaCy model loaded: {self._nlp.meta['name']}")
                    break
                except OSError:
                    continue
            if self._nlp is None:
                logger.warning("No spaCy model found — spaCy NER layer disabled")
        except Exception as exc:
            logger.warning(f"spaCy unavailable: {exc}")

    # ── Public API ─────────────────────────────────────────────────────────────

    def anonymize(self, text: str) -> AnonymizationResult:
        """
        Run all three anonymization layers in sequence.
        Returns the anonymized text plus a report of what was found.
        """
        original_hash = hashlib.sha256(text.encode()).hexdigest()
        entities_removed: list[str] = []
        current = text

        # Layer 1 — regex
        current, regex_entities = self._apply_regex(current)
        entities_removed.extend(regex_entities)

        # Layer 2 — Presidio
        current, presidio_entities = self._apply_presidio(current)
        entities_removed.extend(presidio_entities)

        # Layer 3 — spaCy NER (catches remaining names / locations)
        current, spacy_entities = self._apply_spacy(current)
        entities_removed.extend(spacy_entities)

        unique_entities = list(dict.fromkeys(entities_removed))  # preserve order, dedupe
        return AnonymizationResult(
            original_hash=original_hash,
            anonymized_text=current,
            phi_found=bool(unique_entities),
            entities_removed=unique_entities,
        )

    # ── Layer implementations ─────────────────────────────────────────────────

    def _apply_regex(self, text: str) -> tuple[str, list[str]]:
        found: list[str] = []
        for label, pattern, replacement in self._compiled:
            new_text, count = pattern.subn(replacement, text)
            if count:
                found.extend([label] * count)
                text = new_text
        return text, found

    def _apply_presidio(self, text: str) -> tuple[str, list[str]]:
        if not self._presidio_analyzer:
            return text, []
        try:
            from presidio_anonymizer.entities import OperatorConfig
            results = self._presidio_analyzer.analyze(
                text=text,
                language="en",
                entities=[
                    "PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "LOCATION",
                    "DATE_TIME", "NRP", "MEDICAL_LICENSE",
                ],
            )
            if not results:
                return text, []
            anonymized = self._presidio_anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "PERSON":            OperatorConfig("replace", {"new_value": "[NAME]"}),
                    "PHONE_NUMBER":      OperatorConfig("replace", {"new_value": "[PHONE]"}),
                    "EMAIL_ADDRESS":     OperatorConfig("replace", {"new_value": "[EMAIL]"}),
                    "LOCATION":          OperatorConfig("replace", {"new_value": "[LOCATION]"}),
                    "DATE_TIME":         OperatorConfig("replace", {"new_value": "[DATE]"}),
                    "NRP":               OperatorConfig("replace", {"new_value": "[ID]"}),
                    "MEDICAL_LICENSE":   OperatorConfig("replace", {"new_value": "[LICENSE]"}),
                },
            )
            entity_types = [r.entity_type for r in results]
            return anonymized.text, entity_types
        except Exception as exc:
            logger.warning(f"Presidio anonymization error: {exc}")
            return text, []

    def _apply_spacy(self, text: str) -> tuple[str, list[str]]:
        """
        Catch any names / locations Presidio missed using spaCy NER.
        Only replaces PERSON and GPE entities to avoid over-anonymization.
        """
        if not self._nlp:
            return text, []
        try:
            doc = self._nlp(text)
            replacements: list[tuple[int, int, str]] = []
            found: list[str] = []
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    replacements.append((ent.start_char, ent.end_char, "[NAME]"))
                    found.append("PERSON")
                elif ent.label_ in ("GPE", "LOC", "FAC"):
                    replacements.append((ent.start_char, ent.end_char, "[LOCATION]"))
                    found.append(ent.label_)
            # Apply replacements in reverse so offsets stay valid
            for start, end, repl in sorted(replacements, key=lambda x: x[0], reverse=True):
                text = text[:start] + repl + text[end:]
            return text, found
        except Exception as exc:
            logger.warning(f"spaCy anonymization error: {exc}")
            return text, []


# Module-level singleton — initialized once on import
_anonymizer: Optional[PHIAnonymizer] = None


def get_anonymizer() -> PHIAnonymizer:
    global _anonymizer
    if _anonymizer is None:
        _anonymizer = PHIAnonymizer()
    return _anonymizer
