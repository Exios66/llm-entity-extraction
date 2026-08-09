"""Mailroom agents — LangChain-powered sorter, specialists, and judges."""

from agents.base_agent import BaseAgent, build_structured_schema
from agents.sorter_agent import DOC_CLASSES, DOC_CLASS_KEYS, SORTER_SCHEMA, SorterAgent
from agents.specialist_agents import (
    CONTRACTS_SCHEMA,
    CORPORATE_RECORDS_SCHEMA,
    COMPLIANCE_FILING_SCHEMA,
    CORRESPONDENCE_SCHEMA,
    COURT_OPINIONS_SCHEMA,
    DUE_DILIGENCE_SCHEMA,
    SPECIALIST_REGISTRY,
    SPECIALIST_SCHEMAS,
    ComplianceFilingSpecialist,
    ContractsSpecialist,
    CorporateRecordsSpecialist,
    CorrespondenceSpecialist,
    CourtOpinionsSpecialist,
    DueDiligenceSpecialist,
    get_extraction_schema,
    get_specialist,
)
from agents.judge_agent import (
    CLASSIFICATION_LABELS,
    CORRECTNESS_LABELS,
    LABELS,
    JudgeAgent,
)

__all__ = [
    "BaseAgent",
    "build_structured_schema",
    "DOC_CLASSES",
    "DOC_CLASS_KEYS",
    "SORTER_SCHEMA",
    "SorterAgent",
    "CONTRACTS_SCHEMA",
    "CORPORATE_RECORDS_SCHEMA",
    "COMPLIANCE_FILING_SCHEMA",
    "CORRESPONDENCE_SCHEMA",
    "COURT_OPINIONS_SCHEMA",
    "DUE_DILIGENCE_SCHEMA",
    "SPECIALIST_REGISTRY",
    "SPECIALIST_SCHEMAS",
    "ComplianceFilingSpecialist",
    "ContractsSpecialist",
    "CorporateRecordsSpecialist",
    "CorrespondenceSpecialist",
    "CourtOpinionsSpecialist",
    "DueDiligenceSpecialist",
    "get_extraction_schema",
    "get_specialist",
    "CLASSIFICATION_LABELS",
    "CORRECTNESS_LABELS",
    "LABELS",
    "JudgeAgent",
]
