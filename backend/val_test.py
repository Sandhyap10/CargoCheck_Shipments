
from app.services.validation_service import validate_shipment


documents = {
    "Commercial Invoice": {
        "gross_weight": {
            "value": "3120 kg",
            "confidence": 0.95
        },
        "quantity": {
            "value": "2400",
            "confidence": 0.95
        },
        "product_description": {
            "value": "LED Panel Light 40W",
            "confidence": 0.95
        }
    },

    "Packing List": {
        "gross_weight": {
            "value": "3165 kg",
            "confidence": 0.95
        },
        "quantity": {
            "value": "2400",
            "confidence": 0.95
        },
        "product_description": {
            "value": "LED Panel Light 40W",
            "confidence": 0.95
        }
    },

    "Bill of Lading": {
        "gross_weight": {
            "value": "3165 kg",
            "confidence": 0.95
        },
        "product_description": {
            "value": "LED Panel Light 40W",
            "confidence": 0.95
        }
    }
}


results = validate_shipment(documents)

for result in results:
    print("\nField:", result["field_name"])
    print("Status:", result["status"])
    print("Severity:", result["severity"])
    print("Message:", result["message"])
    print("Compared values:", result["compared_values"])
