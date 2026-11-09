import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import {
  ArrowLeft,
  FileText,
  Upload,
  CheckCircle,
  AlertTriangle,
  LoaderCircle,
  Download,
  Package,
  Clock,
  RefreshCw,
} from "lucide-react";

import API from "../services/api";

const documentTypes = [
  "Commercial Invoice",
  "Packing List",
  "Bill of Lading",
];

function ShipmentDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [shipment, setShipment] = useState(null);
  const [loading, setLoading] = useState(true);

  const [uploading, setUploading] = useState("");
  const [processing, setProcessing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [excelExporting, setExcelExporting] = useState(false);

  const [uploadedDocs, setUploadedDocs] = useState({});
  const [results, setResults] = useState(null);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Fetch shipment report
  const fetchReport = async () => {
    setReportLoading(true);

    try {
      const response = await API.get(`/shipments/${id}/report`);
      setReport(response.data);
    } catch (err) {
      setReport(null);
      console.error("Unable to load shipment report:", err);
    } finally {
      setReportLoading(false);
    }
  };

  // Convert backend document response into frontend state
  const updateUploadedDocuments = (documents) => {
    const savedDocuments = {};

    documents.forEach((document) => {
      savedDocuments[document.document_type] = {
        filename: document.original_filename,
        status: document.processing_status,
        id: document.id,
      };
    });

    setUploadedDocs(savedDocuments);
  };

  // Load shipment and previous processing results
  useEffect(() => {
    const fetchShipmentData = async () => {
      setLoading(true);
      setError("");

      try {
        const shipmentResponse = await API.get(`/shipments/${id}`);

        setShipment(shipmentResponse.data);

        const documentsResponse = await API.get(
          `/shipments/${id}/documents`
        );

        updateUploadedDocuments(documentsResponse.data);

        try {
          const reviewResponse = await API.get(
            `/shipments/${id}/review`
          );

          const review = reviewResponse.data;
          const documents = review.documents || [];

          const totalFields = documents.reduce(
            (total, document) =>
              total + (document.fields?.length || 0),
            0
          );

          if (totalFields > 0) {
            setResults({
              documents_processed: documents.filter(
                (document) => document.fields?.length > 0
              ).length,
              fields_extracted: totalFields,
              validation_results:
                review.validation_results || [],
            });

            await fetchReport();
          } else {
            setResults(null);
            setReport(null);
          }
        } catch {
          setResults(null);
          setReport(null);
        }
      } catch (err) {
        setError(
          err.response?.data?.detail ||
          "Unable to load shipment details."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchShipmentData();
  }, [id]);

  // Upload or replace a document
  const handleUpload = async (documentType, file) => {
    if (!file) return;

    setError("");
    setSuccess("");
    setUploading(documentType);

    const formData = new FormData();

    formData.append("document_type", documentType);
    formData.append("file", file);

    try {
      const response = await API.post(
        `/shipments/${id}/documents`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const uploadedDocument = response.data;

      setUploadedDocs((previous) => ({
        ...previous,
        [documentType]: {
          filename: uploadedDocument.original_filename,
          status: uploadedDocument.processing_status,
          id: uploadedDocument.id,
        },
      }));

      // Previous results are no longer current
      setResults(null);
      setReport(null);

      setSuccess(`${documentType} uploaded successfully!`);

      const shipmentResponse = await API.get(`/shipments/${id}`);

      setShipment(shipmentResponse.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        `Failed to upload ${documentType}.`
      );
    } finally {
      setUploading("");
    }
  };

  // Process all documents
  const handleProcess = async () => {
    setError("");
    setSuccess("");
    setProcessing(true);

    try {
      const response = await API.post(
        `/shipments/${id}/process`
      );

      setResults(response.data);

      // Refresh uploaded document statuses
      const documentsResponse = await API.get(
        `/shipments/${id}/documents`
      );

      updateUploadedDocuments(documentsResponse.data);

      // Refresh shipment status and report
      const shipmentResponse = await API.get(`/shipments/${id}`);

      setShipment(shipmentResponse.data);

      await fetchReport();

      setSuccess("Documents processed successfully!");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Document processing failed."
      );
    } finally {
      setProcessing(false);
    }
  };

  // Export CSV
  const handleExport = async () => {
    setError("");
    setSuccess("");
    setExporting(true);

    try {
      const response = await API.get(
        `/shipments/${id}/export`,
        {
          responseType: "blob",
        }
      );

      const blob = new Blob(
        [response.data],
        { type: "text/csv;charset=utf-8;" }
      );

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = `CargoCheck_${shipment.shipment_id}.csv`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setSuccess("Shipment CSV exported successfully!");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to export CSV. Please ensure all three documents are processed."
      );
    } finally {
      setExporting(false);
    }
  };

  // Export Excel
  const handleExcelExport = async () => {
    setError("");
    setSuccess("");
    setExcelExporting(true);

    try {
      const response = await API.get(
        `/shipments/${id}/export/excel`,
        {
          responseType: "blob",
        }
      );

      const blob = new Blob(
        [response.data],
        {
          type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
      );

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = `CargoCheck_${shipment.shipment_id}.xlsx`;

      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setSuccess("Shipment Excel file exported successfully!");
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to export Excel. Please ensure all three documents are processed."
      );
    } finally {
      setExcelExporting(false);
    }
  };

  // Shipment status styling
  const getShipmentStatusClass = (status) => {
    const normalized = status?.toLowerCase();

    if (normalized === "completed") {
      return "shipment-status completed";
    }

    if (normalized === "attention required") {
      return "shipment-status attention";
    }

    return "shipment-status pending";
  };

  // Format field names
  const formatFieldName = (fieldName) => {
    if (!fieldName) return "Unknown Field";

    return fieldName
      .replace(/_/g, " ")
      .replace(/\b\w/g, (char) => char.toUpperCase());
  };

  // Validation status styling
  const getValidationStatusClass = (status) => {
    if (status === "MATCH") {
      return "validation-status match";
    }

    if (status === "MISMATCH") {
      return "validation-status mismatch";
    }

    return "validation-status not-checked";
  };

  // Validation icon
  const getValidationIcon = (status) => {
    if (status === "MISMATCH") {
      return <AlertTriangle size={15} />;
    }

    if (status === "MATCH") {
      return <CheckCircle size={15} />;
    }

    return <Clock size={15} />;
  };

  // Severity styling
  const getSeverityClass = (severity) => {
    switch (severity?.toUpperCase()) {
      case "HIGH":
        return "severity-badge high";

      case "MEDIUM":
        return "severity-badge medium";

      default:
        return "severity-badge info";
    }
  };

  // Format compared values
  const formatComparedValue = (value) => {
    if (value === null || value === undefined || value === "") {
      return "Not available";
    }

    return String(value);
  };

  const allUploaded = documentTypes.every(
    (type) => uploadedDocs[type]
  );

  if (loading) {
    return (
      <div className="dashboard-content details-loading">
        <LoaderCircle size={25} className="details-spin" />
        <p>Loading shipment details...</p>
      </div>
    );
  }

  if (!shipment) {
    return (
      <div className="dashboard-content">
        <p className="error-message">
          {error || "Shipment not found."}
        </p>

        <button
          className="secondary-button"
          onClick={() => navigate("/shipments")}
        >
          Back to Shipments
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard-content shipment-details-page">

      {/* Back button */}
      <button
        className="back-button"
        onClick={() => navigate("/shipments")}
      >
        <ArrowLeft size={17} />
        Back to Shipments
      </button>

      {/* Shipment heading */}
      <div className="shipment-details-heading">
        <div>
          <h1>{shipment.shipment_id}</h1>
          <p>Shipment information and document verification</p>
        </div>

        <span className={getShipmentStatusClass(shipment.status)}>
          <span className="status-dot"></span>
          {shipment.status || "Pending"}
        </span>
      </div>

      {/* Alerts */}
      {error && (
        <div className="details-alert details-error">
          <AlertTriangle size={17} />
          {error}
        </div>
      )}

      {success && (
        <div className="details-alert details-success">
          <CheckCircle size={17} />
          {success}
        </div>
      )}

      {/* Shipment Information */}
      <div className="table-container details-card">
        <div className="details-section-heading">
          <div className="details-heading-icon">
            <Package size={20} />
          </div>

          <div>
            <h2>Shipment Information</h2>
            <p>Basic shipment details</p>
          </div>
        </div>

        <div className="details-grid">
          <div>
            <span>Shipment ID</span>
            <strong>{shipment.shipment_id}</strong>
          </div>

          <div>
            <span>Importer</span>
            <strong>{shipment.importer_name || "—"}</strong>
          </div>

          <div>
            <span>Supplier</span>
            <strong>{shipment.supplier_name || "—"}</strong>
          </div>

          <div>
            <span>Shipment Date</span>
            <strong>{shipment.shipment_date || "—"}</strong>
          </div>
        </div>
      </div>

      {/* Shipment Documents */}
      <div className="table-container document-section">
        <div className="section-heading details-section-heading">
          <div>
            <h2>Shipment Documents</h2>
            <p>
              Upload all three required documents to begin verification.
            </p>
          </div>
        </div>

        <div className="document-grid">
          {documentTypes.map((type) => (
            <div className="document-card" key={type}>
              <div className="document-card-icon">
                <FileText size={25} />
              </div>

              <h3>{type}</h3>

              {uploadedDocs[type] ? (
                <div className="uploaded-file">
                  <CheckCircle size={16} />
                  <span title={uploadedDocs[type].filename}>
                    {uploadedDocs[type].filename}
                  </span>
                </div>
              ) : (
                <p>PDF, JPG or PNG (Max 10 MB)</p>
              )}

              <label
                className={`upload-button ${
                  uploading === type ? "uploading" : ""
                }`}
              >
                {uploading === type ? (
                  <>
                    <LoaderCircle size={16} />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload size={16} />
                    {uploadedDocs[type]
                      ? "Replace File"
                      : "Choose File"}
                  </>
                )}

                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  hidden
                  disabled={uploading !== ""}
                  onChange={(e) => {
                    const file = e.target.files?.[0];

                    if (file) {
                      handleUpload(type, file);
                    }

                    e.target.value = "";
                  }}
                />
              </label>

              {uploadedDocs[type] && (
                <span className="document-saved-label">
                  <CheckCircle size={13} />
                  Uploaded
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Process Documents */}
        <div className="process-area">
          <button
            className="primary-button process-button"
            disabled={!allUploaded || processing || uploading !== ""}
            onClick={handleProcess}
          >
            {processing ? (
              <>
                <LoaderCircle size={18} className="details-spin" />
                Processing Documents...
              </>
            ) : (
              <>
                <RefreshCw size={17} />
                Process Documents
              </>
            )}
          </button>

          {!allUploaded && (
            <p className="message">
              Upload all three documents to enable processing.
            </p>
          )}
        </div>
      </div>

      {/* Processing Results */}
      {results && (
        <>
          {/* Processing Summary */}
          <div className="table-container results-section">
            <div className="details-section-heading">
              <div>
                <h2>Processing Summary</h2>
                <p>Document extraction and validation overview</p>
              </div>
            </div>

            <div className="result-stats">
              <div>
                <strong>{results.documents_processed ?? 0}</strong>
                <span>Documents Processed</span>
              </div>

              <div>
                <strong>{results.fields_extracted ?? 0}</strong>
                <span>Fields Extracted</span>
              </div>
            </div>

            {/* Validation Results */}
            <h3 className="validation-heading">
              Validation Results
            </h3>

            {results.validation_results?.length > 0 ? (
              <div className="validation-list">

                {results.validation_results.map((item, index) => (
                  <div className="validation-item" key={index}>

                    {/* Field information */}
                    <div className="validation-description">
                      <div className="validation-title-row">
                        <strong>
                          {formatFieldName(item.field_name)}
                        </strong>

                        <span
                          className={getSeverityClass(item.severity)}
                        >
                          {item.severity || "INFO"}
                        </span>
                      </div>

                      <p>{item.message}</p>

                      {/* Compared document values */}
                      {item.compared_values &&
                        Object.keys(item.compared_values).length > 0 && (
                          <div className="compared-values">
                            <strong className="compared-values-heading">
                              Compared Values
                            </strong>

                            <div className="compared-values-grid">
                              {Object.entries(
                                item.compared_values
                              ).map(([document, value]) => (
                                <div
                                  className="compared-value-card"
                                  key={document}
                                >
                                  <span>{document}</span>

                                  <strong>
                                    {formatComparedValue(value)}
                                  </strong>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                    </div>

                    {/* Validation status */}
                    <span
                      className={getValidationStatusClass(item.status)}
                    >
                      {getValidationIcon(item.status)}
                      {item.status || "NOT_CHECKED"}
                    </span>

                  </div>
                ))}

              </div>
            ) : (
              <p className="message">
                No validation results available.
              </p>
            )}
          </div>

          {/* Shipment Accuracy Report */}
          <div className="table-container results-section">
            <div className="details-section-heading">
              <div>
                <h2>Shipment Verification Report</h2>
                <p>Summary of extracted and validated fields</p>
              </div>
            </div>

            {reportLoading ? (
              <div className="details-loading">
                <LoaderCircle size={20} className="details-spin" />
                <p>Loading report...</p>
              </div>
            ) : report ? (
              <>
                <p className="report-shipment-id">
                  Shipment ID: <strong>{report.shipment_id}</strong>
                </p>

                <div className="result-stats report-stats">
                  <div>
                    <strong>{report.total_documents_processed}</strong>
                    <span>Documents Processed</span>
                  </div>

                  <div>
                    <strong>{report.total_fields_extracted}</strong>
                    <span>Fields Extracted</span>
                  </div>

                  <div>
                    <strong>{report.total_manual_corrections}</strong>
                    <span>Manual Corrections</span>
                  </div>

                  <div>
                    <strong className="report-match-value">
                      {report.matched_fields}
                    </strong>
                    <span>Matched Checks</span>
                  </div>

                  <div>
                    <strong className="report-mismatch-value">
                      {report.mismatched_fields}
                    </strong>
                    <span>Mismatched Checks</span>
                  </div>

                  <div>
                    <strong>{report.not_checked_fields}</strong>
                    <span>Not Checked</span>
                  </div>
                </div>

                <p className="report-note">
                  These figures represent validation check results,
                  not measured OCR accuracy.
                </p>
              </>
            ) : (
              <p className="message">
                Report is currently unavailable.
              </p>
            )}
          </div>

          {/* Review and Export */}
          <div className="action-buttons details-action-buttons">
            <button
              className="primary-button"
              onClick={() =>
                navigate(`/shipments/${id}/review`)
              }
            >
              <FileText size={17} />
              Review Documents
            </button>

            <button
              className="secondary-button"
              disabled={exporting || excelExporting}
              onClick={handleExport}
            >
              {exporting ? (
                <>
                  <LoaderCircle size={16} />
                  Exporting...
                </>
              ) : (
                <>
                  <Download size={16} />
                  Export CSV
                </>
              )}
            </button>

            <button
              className="secondary-button"
              disabled={excelExporting || exporting}
              onClick={handleExcelExport}
            >
              {excelExporting ? (
                <>
                  <LoaderCircle size={16} />
                  Exporting...
                </>
              ) : (
                <>
                  <Download size={16} />
                  Export Excel
                </>
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default ShipmentDetails;