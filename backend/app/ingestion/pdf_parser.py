from io import BytesIO

import pdfplumber

from app.ingestion.csv_parser import ParseResult, parse_statement_lines


def parse_bank_pdf(content: bytes) -> ParseResult:
    lines: list[str] = []
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    for row in table:
                        values = [cell or "" for cell in row]
                        lines.append(" ".join(values))
                text = page.extract_text() or ""
                lines.extend(text.splitlines())
    except Exception as exc:  # pdfplumber raises several parser-specific errors
        raise ValueError("PDF statement could not be opened or parsed") from exc

    result = parse_statement_lines(lines)
    if not result.transactions:
        raise ValueError("PDF statement did not contain parseable transaction rows")
    return result
