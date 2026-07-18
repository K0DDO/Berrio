"""Receipt recognition pipeline: OCR text → structure → validate → category."""

from __future__ import annotations

from app.modules.receipts.recognition.extractor import extract_structured_from_ocr
from app.modules.receipts.recognition.models import StructuredReceipt, ValidationResult
from app.modules.receipts.recognition.prompts import CONFIDENCE_AUTO_SAVE_THRESHOLD
from app.modules.receipts.recognition.validator import validate_structured


class ReceiptRecognitionPipeline:
    """
    Split pipeline:
      raw OCR text → deterministic extraction → validation

    LLM may be plugged later for structure, but must use anti-hallucination prompts
    and still pass the same validator. Photos are never persisted.
    """

    def analyze_text(self, raw_text: str) -> tuple[StructuredReceipt, ValidationResult]:
        structured = extract_structured_from_ocr(raw_text)
        validation = validate_structured(structured)
        structured.requires_confirmation = validation.requires_confirmation
        if validation.requires_confirmation and not structured.reason:
            structured.reason = (
                validation.reasons[0]
                if validation.reasons
                else "Не удалось уверенно распознать чек"
            )
        structured.success = structured.success and (
            structured.overall_confidence >= 0.3 or bool(structured.amount.value)
        )
        if validation.ok and structured.overall_confidence >= CONFIDENCE_AUTO_SAVE_THRESHOLD:
            structured.requires_confirmation = False
            structured.reason = None
        return structured, validation
