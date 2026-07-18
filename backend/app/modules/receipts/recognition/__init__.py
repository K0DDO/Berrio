"""Receipt recognition — OCR → structure → validation (no hallucinations)."""

from app.modules.receipts.recognition.pipeline import ReceiptRecognitionPipeline
from app.modules.receipts.recognition.prompts import (
    CONFIDENCE_AUTO_SAVE_THRESHOLD,
    RECEIPT_OCR_SYSTEM,
    RECEIPT_STRUCTURE_SYSTEM,
)

__all__ = [
    "CONFIDENCE_AUTO_SAVE_THRESHOLD",
    "RECEIPT_OCR_SYSTEM",
    "RECEIPT_STRUCTURE_SYSTEM",
    "ReceiptRecognitionPipeline",
]
