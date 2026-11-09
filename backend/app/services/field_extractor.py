
import re


def result(value=None, confidence=0.0):
    return {
        "value": value.strip() if isinstance(value, str) else value,
        "confidence": confidence
    }


def normalize_label(label: str) -> str:
    return re.sub(r"[^a-z0-9]", "", label.lower())


def extract_labeled_value(text: str, labels: list[str]):
    """
    Supports:
    Label: Value
    Label | Value
    Label - Value
    Label = Value
    Label # Value
    Label    Value
    Label
    Value on next line
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for label in sorted(labels, key=len, reverse=True):
        escaped = re.escape(label.rstrip("."))

        pattern = (
            rf"^\s*{escaped}\.?"
            rf"(?:[ \t]*[:#|=][ \t]*|[ \t]+-[ \t]*|[ \t]{{2,}})"
            rf"(.+?)\s*$"
        )

        standalone_pattern = rf"^\s*{escaped}\.?\s*$"

        for index, line in enumerate(lines):
            match = re.search(pattern, line, re.IGNORECASE)

            if match:
                value = match.group(1).strip()
                if value:
                    return result(value, 0.95)

            if re.match(standalone_pattern, line, re.IGNORECASE):
                if index + 1 < len(lines):
                    next_line = lines[index + 1]

                    if not re.match(r"^[A-Z][A-Z /&]{2,}$", next_line):
                        return result(next_line, 0.85)

    return result()


def extract_combined_value(text: str, first_label: str, next_labels: list[str]):
    """
    Extracts a value from lines containing multiple labelled fields.
    Example: Gross Wt: 585 kg Net Wt: 530 kg
    """

    pattern = (
        rf"{re.escape(first_label)}\s*[:#|=]?\s*"
        rf"(.+?)"
    )

    for next_label in next_labels:
        pattern += rf"(?=\s+{re.escape(next_label)}\b|$)"

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
    Extracts product information from invoice table rows.
    Example:
    1 Brake Pad Sets 87083010 500 | SETS 12.50 6,250.00
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
            products.append({
                "description": match.group(1).strip(),
                "hsn_code": match.group(2),
                "quantity": match.group(3).replace(",", ""),
                "unit_price": match.group(4).replace(",", ""),
                "amount": match.group(5).replace(",", "")
            })

            unit_prices.append(match.group(4).replace(",", ""))

    total_match = re.search(
        r"(?im)^\s*TOTAL CIF [A-Z ]+\s+([\d,]+)\s+([\d,.]+)",
        text
    )

    if total_match:
        total_quantity = total_match.group(1).replace(",", "")

    return products, total_quantity, unit_prices


def extract_total_quantity(text: str):
    """
    Extracts total quantity from a table total row.
    Example: TOTAL 35 3,800 530.00 585.00
    """

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
    Extracts gross or net weight using different label formats.

    Examples:
    Gross Weight: 585 kg
    Gross Wt: 585 kg
    G.W.: 585 kg
    GW: 585 kg
    Net Weight: 530 kg
    N.W.: 530 kg
    NW: 530 kg
    """

    if weight_type.lower() == "gross":
        labels = [
            "Shipment Gross Weight",
            "Shipment Gross Wt",
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
            rf"(?<![A-Za-z]){re.escape(label)}"
            rf"(?![A-Za-z])\s*[:#|=.-]?\s*"
            rf"([\d,.]+\s*(?:kg|kgs|kilograms)?)"
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
        r"(?i)(\d+)\s*(?:CTNS|CARTONS|PACKAGES)",
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

        "unit_price": (
            result(", ".join(unit_prices), 0.90)
            if unit_prices
            else result()
        ),

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

    # Example total row:
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
    """Extracts vessel name and voyage number separately."""

    vessel = result()
    voyage = result()

    # Example: Vessel Name: MV Ocean Star V.026E

    match = re.search(
        r"\b(MV\s+[A-Z][A-Z ]*?)\s+V\.?\s*(\d+[A-Z]?)\b",
        text,
        re.IGNORECASE
    )

    if match:
        vessel = result(match.group(1).strip(), 0.95)
        voyage = result(match.group(2).strip(), 0.95)
        return vessel, voyage

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
                "Quantity"
            ]
        )

    packages = table["number_of_packages"]

    if not packages["value"]:
        packages = extract_package_count(text)

    package_type = result()

    if re.search(r"\bcartons?\b", text, re.IGNORECASE):
        package_type = result("Cartons", 0.90)

    elif re.search(r"\bpackages?\b", text, re.IGNORECASE):
        package_type = result("Packages", 0.85)

    vessel, voyage = extract_vessel_and_voyage(text)

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

        "net_weight": table["net_weight"],

        "gross_weight": table["gross_weight"],

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
    Extracts a value from the line immediately below a heading.
    Useful for B/L layouts where SHIPPER and CONSIGNEE
    appear on separate lines from their values.
    """

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for label in labels:
        pattern = rf"^\s*{re.escape(label)}\s*:?\s*$"

        for index, line in enumerate(lines):
            if re.match(pattern, line, re.IGNORECASE):

                if index + 1 < len(lines):
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
    match = re.search(
        r"(?i)Gross\s*(?:Wt|Weight)\s*[:#]?\s*"
        r"([\d,.]+)\s*(kg|kgs|kilograms)?",
        text
    )

    if match:
        value = match.group(1)

        if match.group(2):
            value += " " + match.group(2)

        return result(value, 0.95)

    return result()


def extract_bl_measurement(text: str):
    match = re.search(
        r"(?i)Measurement\s*[:#]?\s*"
        r"([\d,.]+)\s*(CBM|M3|M³)?",
        text
    )

    if match:
        value = match.group(1)

        if match.group(2):
            value += " " + match.group(2)

        return result(value, 0.95)

    return result()


def extract_bl_fields(text: str):
    # Normalize whitespace while preserving the original text.
    normalized = re.sub(r"[ \t]+", " ", text)

    # 1. B/L number
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
    shipper_match = re.search(
        r"SHIPPER\s+BOOKING\s*/\s*REFERENCE\s+"
        r"(.+?)\s+Booking\s+No\s*:",
        normalized,
        re.IGNORECASE | re.DOTALL
    )

    shipper = (
        result(shipper_match.group(1).strip(), 0.90)
        if shipper_match
        else result()
    )

    # 3. Consignee and Notify Party
    consignee = result()
    notify_party = result()

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

        if len(company_matches) >= 2:
            consignee = result(company_matches[0].strip(), 0.90)
            notify_party = result(company_matches[1].strip(), 0.90)

        elif len(company_matches) == 1:
            consignee = result(company_matches[0].strip(), 0.90)
            notify_party = result(company_matches[0].strip(), 0.85)

    # 4. Vessel and voyage
    vessel_match = re.search(
        r"\b(MV\s+[A-Z][A-Z ]+?)\s+V\.?\s*(\d+[A-Z]?)",
        normalized,
        re.IGNORECASE
    )

    vessel = result()
    voyage = result()

    if vessel_match:
        vessel = result(vessel_match.group(1).strip(), 0.95)
        voyage = result(vessel_match.group(2).strip(), 0.95)

    # 5. Container and seal numbers
    container_match = re.search(
        r"\b([A-Z]{4}\d{7})\s*/\s*([A-Z0-9-]+)\b",
        normalized
    )

    container = result()
    seal = result()

    if container_match:
        container = result(container_match.group(1), 0.95)
        seal = result(container_match.group(2), 0.95)

    # 6. Gross weight and measurement from the cargo table
    weight_match = re.search(
        r"(\d{2,3}(?:,\d{3})*(?:\.\d+)?)\s+"
        r"(\d+\.\d+)\s*(?:\n|$)",
        text
    )

    gross_weight = result()
    measurement = result()

    if weight_match:
        gross_weight = result(
            weight_match.group(1) + " kg",
            0.90
        )

        measurement = result(
            weight_match.group(2) + " CBM",
            0.90
        )

    # 7. Cargo description, including wrapped table lines
    cargo = result()

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

        cargo_text = re.sub(
            r"\s+",
            " ",
            cargo_text
        ).strip(" |")

        cargo = result(cargo_text, 0.90)

    # 8. Number of packages
    package_match = re.search(
        r"\b(\d+)\s+CTNS\b",
        normalized,
        re.IGNORECASE
    )

    packages = (
        result(package_match.group(1), 0.95)
        if package_match
        else extract_package_count(text)
    )

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
