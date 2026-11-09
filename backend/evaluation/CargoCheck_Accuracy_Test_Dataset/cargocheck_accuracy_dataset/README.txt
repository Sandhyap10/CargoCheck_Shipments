CARGOCHECK AI - SYNTHETIC ACCURACY EVALUATION DATASET

Contents
- Commercial_Invoices/: 5 sample Commercial Invoice PDFs
- Packing_Lists/: 5 sample Packing List PDFs
- Bills_of_Lading/: 5 sample Bill of Lading PDFs
- CargoCheck_Ground_Truth.xlsx: manually defined expected field values

Dataset design
- 5 synthetic shipment records (SHP-201 through SHP-205)
- 15 PDFs total: 9 digitally generated and 6 scanned-style image PDFs
- Ground Truth sheet contains one row per expected extracted field.
- Dataset Summary sheet describes the dataset.

Important
These are synthetic examples, not real trade documents. They are for software testing only.
The measured accuracy on this small synthetic dataset must not be presented as proven
real-world accuracy or a guarantee of 95% performance.

Suggested evaluation
1. Run each PDF through the existing CargoCheck OCR and field extraction pipeline.
2. Match extracted results to the Ground Truth sheet by filename and field_name.
3. Normalize harmless differences (whitespace, case, commas in numeric values, and units)
   before comparing.
4. Report exact field accuracy overall, by document type, and by field.
5. Keep missing or incorrectly extracted values as incorrect; do not silently exclude them.
