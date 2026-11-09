import re
from typing import Optional


def result(value=None, confidence=0.0):
    """Return a consistent extraction result."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            value = None

    return {
        "value": value,
        "confidence": confidence if value is not None else 0.0
    }


def normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", label.lower())


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _label_regex(label: str) -> str:
    """
    Build a label expression that tolerates repeated spaces and punctuation
    while still matching the label literally.
    """
    parts = re.split(r"\s+", label.strip().rstrip("."))
    return r"\s+".join(re.escape(part) for part in parts)


def extract_labeled_value(text: str, labels: list[str]):
    """
    Extract a value from common label formats:
      Label: Value
      Label | Value
      Label - Value
      Label = Value
      Label # Value
      Label    Value
      Label
      Value on the next line

    The label must start the line, reducing accidental matches inside
    unrelated sentences.
    """
    lines = _non_empty_lines(text)

    for label in sorted(labels, key=len, reverse=True):
        label_pattern = _label_regex(label)

        same_line_pattern = re.compile(
            rf"^\s*{label_pattern}\.?"
            rf"(?:[ \t]*[:#|=][ \t]*|[ \t]+-[ \t]*|[ \t]{{2,}})"
            rf"(.+?)\s*$",
            re.IGNORECASE
        )
        standalone_pattern = re.compile(
            rf"^\s*{label_pattern}\.?\s*$",
            re.IGNORECASE
        )

        for index, line in enumerate(lines):
            match = same_line_pattern.match(line)
            if match:
                value = match.group(1).strip()
                if value:
                    return result(value, 0.95)

            if standalone_pattern.match(line) and index + 1 < len(lines):
                next_line = lines[index + 1].strip()

                # Avoid treating the next section heading as a field value.
                if not re.match(
                    r"^[A-Z][A-Z /&()_-]{2,}$",
                    next_line
                ):
                    return result(next_line, 0.85)

    return result()


def extract_combined_value(text: str, first_label: str, next_labels: list[str]):
    """
    Extract one value from a line containing multiple labelled fields.
    Example: Gross Wt: 585 kg Net Wt: 530 kg
    """
    lookahead = "|".join(re.escape(label) for label in next_labels)

    pattern = (
        rf"{re.escape(first_label)}\s*[:#|=.-]?\s*"
        rf"(.+?)"
        rf"(?=\s+(?:{lookahead})\b|$)"
    )

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return result(match.group(1).strip(), 0.95)

    return result()


def clean_unit_price(value):
    if not value:
        return value

    match = re.search(r"\d[\d,]*(?:\.\d+)?", value)
    if match:
        return match.group(0).replace(",", "")

    return value.strip()


def extract_invoice_table_fields(text: str):
    """
    Extract product information from invoice table rows.
    Retains support for the table format handled by the original parser.
    """
    products = []
    total_quantity = None
    unit_prices = []

    for line in text.splitlines():
        line = line.strip()

        match = re.match(
            r"^\d+\s+(.+?)\s+(\d{6,10})\s+"
            r"([\d,]+)\s*\|?\s*[A-Z]+\s+"
            r"([\d,.]+)\s+([\d,.]+)$",
            line,
            re.IGNORECASE
        )

        if match:
            unit_price = match.group(4).replace(",", "")
            products.append({
                "description": match.group(1).strip(),
                "hsn_code": match.group(2),
                "quantity": match.group(3).replace(",", ""),
                "unit_price": unit_price,
                "amount": match.group(5).replace(",", "")
            })
            unit_prices.append(unit_price)

    total_match = re.search(
        r"(?im)^\s*TOTAL CIF [A-Z ]+\s+([\d,]+)\s+([\d,.]+)",
        text
    )

    if total_match:
        total_quantity = total_match.group(1).replace(",", "")

    return products, total_quantity, unit_prices


def extract_total_quantity(text: str):
    patterns = [
        r"(?im)^\s*TOTAL(?:\s+CIF\s+[A-Z ]+)?\s+[\d,]+\s+([\d,]+)\s+",
        r"(?im)^\s*TOTAL\s+QUANTITY\s*[:#|=]?\s*([\d,]+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return result(match.group(1).replace(",", ""), 0.90)

    return result()


def extract_total_weight(text: str, weight_type: str):
    """
    Extract gross or net weight from common labels, including:
    Gross Weight, Gross Wt, G.W., GW, Net Weight, Net Wt, N.W., NW.
    """
    if weight_type.lower() == "gross":
        labels = [
            "Shipment Gross Weight",
            "Shipment Gross Wt",
            "Total Gross Weight",
            "Gross Weight",
            "Gross Wt.",
            "Gross Wt",
            "Gross Mass",
            "G.W.",
            "G.W",
            "GW"
        ]
    else:
        labels = [
            "Shipment Net Weight",
            "Shipment Net Wt",
            "Total Net Weight",
            "Net Weight",
            "Net Wt.",
            "Net Wt",
            "Net Mass",
            "N.W.",
            "N.W",
            "NW"
        ]

    for label in sorted(labels, key=len, reverse=True):
        pattern = (
            rf"(?<![A-Za-z]){_label_regex(label)}"
            rf"(?![A-Za-z])\s*[:#|=.-]?\s*"
            rf"([\d,]+(?:\.\d+)?\s*(?:kg|kgs|kilograms)?)"
        )

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return result(match.group(1).strip(), 0.95)

    return result()


def extract_package_count(text: str):
    value = extract_labeled_value(
        text,
        [
            "Number of Packages",
            "No. of Packages",
            "No of Packages",
            "Total Packages",
            "Packages",
            "Pkgs Count",
            "No. of Pkgs",
            "No of Pkgs",
            "Pkg Count",
            "Package Count"
        ]
    )

    if value["value"]:
        match = re.search(r"\d[\d,]*", value["value"])
        if match:
            return result(
                match.group(0).replace(",", ""),
                value["confidence"]
            )

    match = re.search(
        r"(?im)^\s*TOTAL\s+(\d+)\s+[\d,]+\s+",
        text
    )
    if match:
        return result(match.group(1), 0.90)

    match = re.search(
        r"(?i)(\d+)\s*(?:CTNS|CARTONS|PACKAGES)\b",
        text
    )
    if match:
        return result(match.group(1), 0.85)

    return result()


def extract_invoice_fields(text: str):
    products, table_quantity, unit_prices = extract_invoice_table_fields(text)

    quantity = extract_labeled_value(
        text,
        [
            "Total Quantity",
            "Total Qty",
            "Total Qnty",
            "Quantity",
            "Qty",
            "Qnty"
        ]
    )

    if not quantity["value"]:
        quantity = extract_total_quantity(text)

    total_amount = extract_labeled_value(
        text,
        [
            "Total Amount",
            "Grand Total",
            "Invoice Total",
            "InvoiceTotal"
        ]
    )

    if not total_amount["value"]:
        match = re.search(
            r"(?im)^\s*TOTAL\s+CIF\s+[A-Z ]+\s+[\d,]+\s+([\d,]+\.\d{2})",
            text
        )
        if match:
            total_amount = result(match.group(1), 0.90)

    unit_price = (
        result(", ".join(unit_prices), 0.90)
        if unit_prices
        else extract_labeled_value(
            text,
            [
                "Unit Price",
                "Price per Unit",
                "Unit Rate",
                "Rate per Unit"
            ]
        )
    )

    return {
        "invoice_number": extract_labeled_value(
            text,
            [
                "Invoice Number",
                "Invoice No",
                "Invoice #",
                "Inv No",
                "Inv. No.",
                "Inv #",
                "Inv. #"
            ]
        ),

        "invoice_date": extract_labeled_value(
            text,
            [
                "Invoice Date",
                "Date of Invoice",
                "Inv Date",
                "Dated",
                "Date"
            ]
        ),

        "buyer": extract_labeled_value(
            text,
            [
                "Consignee / Buyer",
                "Consignee / Bill To",
                "Buyer",
                "Bill To",
                "Importer"
            ]
        ),

        "seller": extract_labeled_value(
            text,
            [
                "Seller",
                "Exporter",
                "Supplier"
            ]
        ),

        "currency": extract_labeled_value(
            text,
            [
                "Currency Code",
                "Currency"
            ]
        ),

        "incoterm": extract_labeled_value(
            text,
            [
                "Incoterms 2020",
                "Incoterm",
                "Terms of Delivery",
                "Trade Term"
            ]
        ),

        "product_description": (
            result("; ".join(p["description"] for p in products), 0.90)
            if products
            else extract_labeled_value(
                text,
                [
                    "Product Description",
                    "Description of Goods",
                    "Goods Description",
                    "Product"
                ]
            )
        ),

        "hsn_code": (
            result(", ".join(p["hsn_code"] for p in products), 0.90)
            if products
            else extract_labeled_value(
                text,
                [
                    "HSN Code",
                    "HS Code",
                    "HSN"
                ]
            )
        ),

        "quantity": (
            result(table_quantity, 0.90)
            if table_quantity
            else quantity
        ),

        "unit_price": unit_price,

        "gross_weight": extract_total_weight(text, "gross"),

        "net_weight": extract_total_weight(text, "net"),

        "total_amount": total_amount
    }


def extract_packing_table_fields(text: str):
    products = []

    for line in text.splitlines():
        line = line.strip()

        match = re.match(
            r"^\d+\s*-\s*\d+\s+(.+?)\s+"
            r"\d+\s+[\d,]+\s*(?:pcs|pieces|units)\s+"
            r"[\d,]+\s+[\d,.]+\s+[\d,.]+",
            line,
            re.IGNORECASE
        )

        if match:
            products.append(match.group(1).strip())

    # Original packing-table total format:
    # TOTAL 35 3,800 530.00 585.00 | 2.14 CBM
    total_match = re.search(
        r"(?im)^\s*TOTAL\s+(\d+)\s+([\d,]+)\s+"
        r"([\d,.]+)\s+([\d,.]+)",
        text
    )

    net_weight = result()
    gross_weight = result()
    quantity = result()
    packages = result()

    if total_match:
        packages = result(total_match.group(1), 0.95)
        quantity = result(
            total_match.group(2).replace(",", ""),
            0.95
        )
        net_weight = result(total_match.group(3), 0.95)
        gross_weight = result(total_match.group(4), 0.95)

    container_match = re.search(
        r"\b([A-Z]{4}\d{7})\b",
        text
    )

    container_number = (
        result(container_match.group(1), 0.95)
        if container_match
        else result()
    )

    return {
        "products": products,
        "quantity": quantity,
        "number_of_packages": packages,
        "net_weight": net_weight,
        "gross_weight": gross_weight,
        "container_number": container_number
    }


def extract_vessel_and_voyage(text: str):
    """Extract vessel name and voyage number from combined or separate labels."""
    vessel = result()
    voyage = result()

    # Combined example: MV Ocean Star V.026E
    combined_patterns = [
        r"\b(MV\s+[A-Z][A-Z0-9 .'-]*?)\s+V\.?\s*(\d+[A-Z]?)\b",
        r"\b(M\/V\s+[A-Z][A-Z0-9 .'-]*?)\s+V\.?\s*(\d+[A-Z]?)\b"
    ]

    for pattern in combined_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return (
                result(match.group(1).strip(), 0.95),
                result(match.group(2).strip(), 0.95)
            )

    # Separate labels, as in:
    # Vessel Name: MSC Horizon
    # Voyage Number: V123
    vessel = extract_labeled_value(
        text,
        [
            "Vessel Name",
            "Ocean Vessel",
            "Vessel"
        ]
    )

    voyage = extract_labeled_value(
        text,
        [
            "Voyage Number",
            "Voyage No.",
            "Voyage No",
            "Voyage"
        ]
    )

    return vessel, voyage


def extract_packing_list_fields(text: str):
    table = extract_packing_table_fields(text)

    quantity = table["quantity"]
    if not quantity["value"]:
        quantity = extract_labeled_value(
            text,
            [
                "Total Quantity",
                "Total Units",
                "Total Qty",
                "Quantity",
                "Qty"
            ]
        )

    packages = table["number_of_packages"]
    if not packages["value"]:
        packages = extract_package_count(text)

    # Prefer an explicitly labelled package type.
    package_type = extract_labeled_value(
        text,
        [
            "Package Type",
            "Packing Type",
            "Type of Packages"
        ]
    )

    if not package_type["value"]:
        if re.search(r"\bcartons?\b", text, re.IGNORECASE):
            package_type = result("Cartons", 0.90)
        elif re.search(r"\bpackages?\b", text, re.IGNORECASE):
            package_type = result("Packages", 0.85)

    vessel, voyage = extract_vessel_and_voyage(text)

    table_net_weight = table["net_weight"]
    if not table_net_weight["value"]:
        table_net_weight = extract_total_weight(text, "net")

    table_gross_weight = table["gross_weight"]
    if not table_gross_weight["value"]:
        table_gross_weight = extract_total_weight(text, "gross")

    return {
        "product_description": (
            result("; ".join(table["products"]), 0.90)
            if table["products"]
            else extract_labeled_value(
                text,
                [
                    "Product Description",
                    "Description of Goods",
                    "Goods Description",
                    "Product"
                ]
            )
        ),

        "quantity": quantity,

        "number_of_packages": packages,

        "package_type": package_type,

        "net_weight": table_net_weight,

        "gross_weight": table_gross_weight,

        "container_number": table["container_number"],

        "seal_number": extract_labeled_value(
            text,
            [
                "Seal Number",
                "Seal No",
                "Seal No.",
                "Seal #",
                "Seal"
            ]
        ),

        "vessel_name": vessel,

        "voyage_number": voyage
    }


def extract_heading_value(text: str, labels: list[str]):
    """
    Extract a value from the line immediately below a standalone heading.
    Useful for document layouts where a heading and its value are on
    separate lines.
    """
    lines = _non_empty_lines(text)

    for label in labels:
        pattern = re.compile(
            rf"^\s*{_label_regex(label)}\s*:?\s*$",
            re.IGNORECASE
        )

        for index, line in enumerate(lines):
            if pattern.match(line) and index + 1 < len(lines):
                next_line = lines[index + 1].strip()

                if next_line and not re.match(
                    r"^(SHIPPER|CONSIGNEE|NOTIFY PARTY|"
                    r"VESSEL|VOYAGE|DESCRIPTION OF GOODS)\s*:?\s*$",
                    next_line,
                    re.IGNORECASE
                ):
                    return result(next_line, 0.90)

    return result()


def extract_bl_container_and_seal(text: str):
    """
    Handles combined fields such as:
    Container / Seal Nos: MSKU1234567 / SL884512
    """
    match = re.search(
        r"(?i)Container\s*/\s*Seal\s+Nos?\.?\s*[:#]?\s*"
        r"([A-Z]{4}\d{7})\s*/\s*([A-Z0-9-]+)",
        text
    )

    if match:
        return (
            result(match.group(1), 0.95),
            result(match.group(2), 0.95)
        )

    return result(), result()


def extract_bl_weight(text: str):
    # Reuse the general gross-weight extractor.
    return extract_total_weight(text, "gross")


def extract_bl_measurement(text: str):
    match = re.search(
        r"(?i)Measurement\s*[:#|=.-]?\s*"
        r"([\d,]+(?:\.\d+)?)\s*(CBM|M3|M³)?",
        text
    )

    if match:
        value = match.group(1)
        if match.group(2):
            value += " " + match.group(2)
        return result(value, 0.95)

    return result()


def extract_bl_fields(text: str):
    """
    Extract fields from both simple labelled B/L documents and the
    older tabular B/L layout supported by the original implementation.
    """
    normalized = re.sub(r"[ \t]+", " ", text)

    # 1. Bill of Lading Number
    bl_number = extract_labeled_value(
        normalized,
        [
            "Bill of Lading Number",
            "Bill of Lading No",
            "B/L Number",
            "B/L No",
            "BOL Number",
            "BOL No",
            "BL Number",
            "BL No"
        ]
    )

    # 2. Shipper
    shipper = extract_labeled_value(
        normalized,
        [
            "Shipper",
            "Exporter"
        ]
    )

    if not shipper["value"]:
        # Fallback for the older SHIPPER / BOOKING / REFERENCE layout.
        shipper_match = re.search(
            r"SHIPPER\s+BOOKING\s*/\s*REFERENCE\s+"
            r"(.+?)\s+Booking\s+No\s*:",
            normalized,
            re.IGNORECASE | re.DOTALL
        )
        if shipper_match:
            shipper = result(shipper_match.group(1).strip(), 0.90)

    # 3. Consignee and Notify Party
    consignee = extract_labeled_value(
        normalized,
        [
            "Consignee",
            "Receiver"
        ]
    )

    notify_party = extract_labeled_value(
        normalized,
        [
            "Notify Party",
            "Notify"
        ]
    )

    # Fallback for the older B/L layout.
    if not consignee["value"] or not notify_party["value"]:
        party_match = re.search(
            r"CONSIGNEE\s+NOTIFY PARTY\s+"
            r"(.+?)\s+Industriestrasse",
            normalized,
            re.IGNORECASE | re.DOTALL
        )

        if party_match:
            party_text = party_match.group(1).strip()
            company_matches = re.findall(
                r"([A-Z][A-Za-z0-9&.,' -]*?"
                r"(?:GmbH|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?|Inc\.?))",
                party_text
            )

            if not consignee["value"] and company_matches:
                consignee = result(company_matches[0].strip(), 0.90)

            if not notify_party["value"] and len(company_matches) >= 2:
                notify_party = result(company_matches[1].strip(), 0.90)

    # 4. Vessel and voyage
    vessel, voyage = extract_vessel_and_voyage(normalized)

    # Fallback for the older combined MV ... V123 format.
    if not vessel["value"] or not voyage["value"]:
        vessel_match = re.search(
            r"\b(MV\s+[A-Z][A-Z ]+?)\s+V\.?\s*(\d+[A-Z]?)",
            normalized,
            re.IGNORECASE
        )

        if vessel_match:
            if not vessel["value"]:
                vessel = result(vessel_match.group(1).strip(), 0.95)
            if not voyage["value"]:
                voyage = result(vessel_match.group(2).strip(), 0.95)

    # 5. Container and seal numbers
    container = extract_labeled_value(
        normalized,
        [
            "Container Number",
            "Container No.",
            "Container No",
            "Container #",
            "Container ID"
        ]
    )

    seal = extract_labeled_value(
        normalized,
        [
            "Seal Number",
            "Seal No.",
            "Seal No",
            "Seal #"
        ]
    )

    # Support the combined Container / Seal Nos format.
    if not container["value"] or not seal["value"]:
        combined_container, combined_seal = extract_bl_container_and_seal(
            normalized
        )

        if not container["value"]:
            container = combined_container
        if not seal["value"]:
            seal = combined_seal

    # Final fallback for a standard ISO container number.
    if not container["value"]:
        container_match = re.search(
            r"\b([A-Z]{4}\d{7})\b",
            normalized
        )
        if container_match:
            container = result(container_match.group(1), 0.90)

    # 6. Gross weight and measurement
    gross_weight = extract_bl_weight(normalized)
    measurement = extract_bl_measurement(normalized)

    # Retain fallback for the older tabular cargo layout.
    if not gross_weight["value"] or not measurement["value"]:
        weight_match = re.search(
            r"(\d{2,3}(?:,\d{3})*(?:\.\d+)?)\s+"
            r"(\d+\.\d+)\s*(?:\n|$)",
            text
        )

        if weight_match:
            if not gross_weight["value"]:
                gross_weight = result(
                    weight_match.group(1) + " kg",
                    0.90
                )
            if not measurement["value"]:
                measurement = result(
                    weight_match.group(2) + " CBM",
                    0.90
                )

    # 7. Cargo description
    cargo = extract_labeled_value(
        normalized,
        [
            "Cargo Description",
            "Product Description",
            "Description of Goods",
            "Goods Description"
        ]
    )

    # Fallback for the older automotive cargo-table layout.
    if not cargo["value"]:
        cargo_match = re.search(
            r"(Automotive\s+(?:accessories|spare\s+parts)\s*:\s*.+?)"
            r"(?=\s+SHIPPED ON BOARD|\Z)",
            text,
            re.IGNORECASE | re.DOTALL
        )

        if cargo_match:
            cargo_text = cargo_match.group(1)
            cargo_text = re.sub(
                r"\b\d{2,3}(?:,\d{3})*(?:\.\d+)?\s+"
                r"\d+\.\d+\b",
                "",
                cargo_text
            )
            cargo_text = re.sub(
                r"RMP\s*/\s*HAMBURG",
                "",
                cargo_text,
                flags=re.IGNORECASE
            )
            cargo_text = re.sub(
                r"C/No\.?\s*\d+\s*-\s*\d+",
                "",
                cargo_text,
                flags=re.IGNORECASE
            )
            cargo_text = re.sub(r"\s+", " ", cargo_text).strip(" |")
            cargo = result(cargo_text, 0.90)

    # 8. Number of packages
    packages = extract_package_count(normalized)

    if not packages["value"]:
        package_match = re.search(
            r"\b(\d+)\s+CTNS\b",
            normalized,
            re.IGNORECASE
        )
        if package_match:
            packages = result(package_match.group(1), 0.95)

    return {
        "shipper": shipper,
        "consignee": consignee,
        "notify_party": notify_party,
        "vessel_name": vessel,
        "voyage_number": voyage,
        "bill_of_lading_number": bl_number,
        "container_number": container,
        "seal_number": seal,
        "product_description": cargo,
        "gross_weight": gross_weight,
        "number_of_packages": packages,
        "measurement": measurement
    }


def extract_document_fields(document_type: str, text: str):
    extractors = {
        "Commercial Invoice": extract_invoice_fields,
        "Packing List": extract_packing_list_fields,
        "Bill of Lading": extract_bl_fields
    }

    extractor = extractors.get(document_type)

    if not extractor:
        raise ValueError(
            f"Unsupported document type: {document_type}"
        )

    return extractor(text)
