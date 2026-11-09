
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import {
  ArrowLeft,
  FileText,
  Pencil,
  Save,
  X,
  CheckCircle,
  History,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Download,
  AlertTriangle,
  Clock,
} from "lucide-react";

import API from "../services/api";

function DocumentReview() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [correctionHistory, setCorrectionHistory] = useState([]);

  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState("");

  const [activeDocument, setActiveDocument] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editedValue, setEditedValue] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  // Document preview states
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [zoom, setZoom] = useState(100);

  const currentDocument = data?.documents?.[activeDocument];

  // Fetch shipment review
  const fetchReview = async () => {
    try {
      const response = await API.get(`/shipments/${id}/review`);
      setData(response.data);
    } catch (err) {
      setError("Unable to load extracted fields.");
    } finally {
      setLoading(false);
    }
  };

  // Fetch correction history
  const fetchCorrectionHistory = async () => {
    try {
      setHistoryLoading(true);
      setHistoryError("");

      const response = await API.get(
        `/shipments/${id}/correction-history`
      );

      setCorrectionHistory(
        response.data.correction_history || []
      );
    } catch (err) {
      setHistoryError("Unable to load correction history.");
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    fetchReview();
    fetchCorrectionHistory();
  }, [id]);

  // Load original document preview
  useEffect(() => {
    let objectUrl = null;
    let cancelled = false;

    const loadPreview = async () => {
      if (!currentDocument?.document_id) {
        setPreviewUrl("");
        return;
      }

      try {
        setPreviewLoading(true);
        setPreviewError("");
        setPreviewUrl("");
        setZoom(100);

        const response = await API.get(
          `/shipments/${id}/documents/${currentDocument.document_id}/preview`,
          {
            responseType: "blob",
          }
        );

        if (cancelled) return;

        const blobUrl = URL.createObjectURL(response.data);
        objectUrl = blobUrl;
        setPreviewUrl(blobUrl);

      } catch (err) {
        if (!cancelled) {
          setPreviewError(
            "Unable to load the original document preview."
          );
        }
      } finally {
        if (!cancelled) {
          setPreviewLoading(false);
        }
      }
    };

    loadPreview();

    return () => {
      cancelled = true;

      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [id, currentDocument?.document_id]);

  // Start editing a field
  const startEditing = (field) => {
    setEditingId(field.id);
    setEditedValue(field.extracted_value || "");
    setReason("");
    setError("");
    setSuccess("");
  };

  // Cancel editing
  const cancelEditing = () => {
    setEditingId(null);
    setEditedValue("");
    setReason("");
  };

  // Save manual correction
  const saveCorrection = async (fieldId) => {
    if (!reason.trim()) {
      setError("Please provide a reason for the correction.");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      await API.post(
        `/extracted-fields/${fieldId}/corrections`,
        {
          corrected_value: editedValue,
          correction_reason: reason,
        }
      );

      setSuccess("Correction saved successfully!");
      setEditingId(null);
      setEditedValue("");
      setReason("");

      await Promise.all([
        fetchReview(),
        fetchCorrectionHistory(),
      ]);

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Unable to save correction."
      );
    } finally {
      setSaving(false);
    }
  };

  // Format dates in Indian Standard Time
  const formatDate = (dateValue) => {
    if (!dateValue) return "Date unavailable";

    const utcValue =
      !dateValue.endsWith("Z") &&
      !/[+-]\d{2}:\d{2}$/.test(dateValue)
        ? `${dateValue}Z`
        : dateValue;

    const date = new Date(utcValue);

    if (Number.isNaN(date.getTime())) {
      return "Date unavailable";
    }

    return date.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  };

  // Format field names
  const fieldLabel = (name) =>
    name
      .replaceAll("_", " ")
      .replace(/\b\w/g, (letter) => letter.toUpperCase());

  // Validation data
  const validationResults = data?.validation_results || [];

  const matchCount = validationResults.filter(
    (item) => item.status === "MATCH"
  ).length;

  const mismatchCount = validationResults.filter(
    (item) => item.status === "MISMATCH"
  ).length;

  const notCheckedCount = validationResults.filter(
    (item) => item.status === "NOT_CHECKED"
  ).length;

  // Get validation status CSS class
  const getStatusClass = (status) => {
    switch (status) {
      case "MATCH":
        return "status-match";

      case "MISMATCH":
        return "status-mismatch";

      case "NOT_CHECKED":
        return "status-not-checked";

      default:
        return "status-not-checked";
    }
  };

  // Get severity CSS class
  const getSeverityClass = (severity) => {
    switch ((severity || "").toUpperCase()) {
      case "HIGH":
        return "severity-high";

      case "MEDIUM":
        return "severity-medium";

      case "LOW":
        return "severity-low";

      default:
        return "severity-low";
    }
  };

  // Format compared values
  const formatComparedValues = (values) => {
    if (
      values === null ||
      values === undefined ||
      values === ""
    ) {
      return "No comparison values available";
    }

    if (typeof values === "string") {
      try {
        values = JSON.parse(values);
      } catch {
        return values;
      }
    }

    if (Array.isArray(values)) {
      return values.map((value) =>
        typeof value === "object" && value !== null
          ? JSON.stringify(value)
          : String(value)
      ).join(" | ");
    }

    if (typeof values === "object") {
      return Object.entries(values)
        .map(([key, value]) => {
          const displayValue =
            typeof value === "object" && value !== null
              ? JSON.stringify(value)
              : String(value ?? "—");

          return `${fieldLabel(key)}: ${displayValue}`;
        })
        .join(" | ");
    }

    return String(values);
  };

  const isPdf = currentDocument?.filename
    ?.toLowerCase()
    .endsWith(".pdf");

  const isImage = /\.(jpg|jpeg|png)$/i.test(
    currentDocument?.filename || ""
  );

  // Loading state
  if (loading) {
    return (
      <div className="dashboard-content">
        Loading extracted fields...
      </div>
    );
  }

  // Error state
  if (error && !data) {
    return (
      <div className="dashboard-content">
        <p className="error-message">{error}</p>
      </div>
    );
  }

  return (
    <div className="dashboard-content">

      {/* Back Button */}
      <button
        className="back-button"
        onClick={() => navigate(`/shipments/${id}`)}
      >
        <ArrowLeft size={17} />
        Back to Shipment
      </button>

      {/* Page Heading */}
      <div className="welcome-section">
        <h1>Document Review</h1>

        <p>
          Shipment {data?.shipment_id} — Review and correct
          extracted information.
        </p>
      </div>

      {error && (
        <p className="error-message">{error}</p>
      )}

      {success && (
        <p className="success-message">{success}</p>
      )}

      {/* Review Summary */}
      <div className="review-summary">

        <div>
          <strong>{data?.documents?.length || 0}</strong>
          <span>Documents</span>
        </div>

        <div>
          <strong>
            {data?.documents?.reduce(
              (total, doc) => total + doc.fields.length,
              0
            ) || 0}
          </strong>
          <span>Extracted Fields</span>
        </div>

        <div className="summary-match">
          <strong>{matchCount}</strong>
          <span>Matched</span>
        </div>

        <div className="summary-mismatch">
          <strong>{mismatchCount}</strong>
          <span>Mismatches</span>
        </div>

        <div className="summary-not-checked">
          <strong>{notCheckedCount}</strong>
          <span>Not Checked</span>
        </div>

      </div>

      {/* Document Review Workspace */}
      <div className="table-container review-container">

        <h2>Document Review Workspace</h2>

        {/* Document Tabs */}
        <div className="document-tabs">

          {data?.documents?.map((doc, index) => (
            <button
              key={doc.document_id}
              className={
                activeDocument === index
                  ? "document-tab active"
                  : "document-tab"
              }
              onClick={() => {
                setActiveDocument(index);
                cancelEditing();
                setError("");
                setSuccess("");
              }}
            >
              <FileText size={16} />
              {doc.document_type}
            </button>
          ))}

        </div>

        {currentDocument && (
          <>

            {/* Document Information */}
            <div className="review-document-info">

              <div>
                <strong>{currentDocument.document_type}</strong>
                <p>{currentDocument.filename}</p>
              </div>

              <span className="processed-label">
                <CheckCircle size={15} />
                Processed
              </span>

            </div>

            {/* Split Screen Workspace */}
            <div className="document-workspace">

              {/* LEFT: Original Document */}
              <div className="document-preview-panel">

                <div className="preview-heading">

                  <h3>Original Document</h3>

                  <div className="preview-controls">

                    <button
                      onClick={() =>
                        setZoom((value) =>
                          Math.max(50, value - 10)
                        )
                      }
                      disabled={!isImage || zoom <= 50}
                      title="Zoom out"
                    >
                      <ZoomOut size={17} />
                    </button>

                    <span>{zoom}%</span>

                    <button
                      onClick={() =>
                        setZoom((value) =>
                          Math.min(200, value + 10)
                        )
                      }
                      disabled={!isImage || zoom >= 200}
                      title="Zoom in"
                    >
                      <ZoomIn size={17} />
                    </button>

                    <button
                      onClick={() => setZoom(100)}
                      disabled={!isImage}
                      title="Reset zoom"
                    >
                      <RotateCcw size={16} />
                    </button>

                  </div>

                </div>

                <div className="document-preview-area">

                  {previewLoading ? (

                    <p className="message">
                      Loading original document...
                    </p>

                  ) : previewError ? (

                    <p className="error-message">
                      {previewError}
                    </p>

                  ) : previewUrl && isPdf ? (

                    <iframe
                      key={previewUrl}
                      src={previewUrl}
                      title="Original PDF Document"
                      className="pdf-preview"
                    />

                  ) : previewUrl && isImage ? (

                    <div className="image-preview">

                      <img
                        src={previewUrl}
                        alt={currentDocument.filename}
                        style={{
                          transform: `scale(${zoom / 100})`,
                        }}
                      />

                    </div>

                  ) : (

                    <div className="preview-empty">
                      <FileText size={42} />
                      <p>Document preview unavailable.</p>
                    </div>

                  )}

                </div>

                {previewUrl && (
                  <a
                    href={previewUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="preview-download"
                  >
                    <Download size={16} />
                    Open Original Document
                  </a>
                )}

              </div>

              {/* RIGHT: Extracted Fields */}
              <div className="extracted-fields-panel">

                <h3>Extracted Information</h3>

                <div className="review-table-scroll">

                  <table className="review-table">

                    <thead>
                      <tr>
                        <th>Field Name</th>
                        <th>Extracted Value</th>
                        <th>Confidence</th>
                        <th>Action</th>
                      </tr>
                    </thead>

                    <tbody>

                      {currentDocument.fields.map((field) => (

                        <tr key={field.id}>

                          <td>
                            <strong>
                              {fieldLabel(field.field_name)}
                            </strong>
                          </td>

                          <td>

                            {editingId === field.id ? (

                              <div className="edit-field">

                                <input
                                  value={editedValue}
                                  onChange={(e) =>
                                    setEditedValue(e.target.value)
                                  }
                                  placeholder="Corrected value"
                                />

                                <input
                                  value={reason}
                                  onChange={(e) =>
                                    setReason(e.target.value)
                                  }
                                  placeholder="Reason for correction"
                                />

                              </div>

                            ) : (

                              field.extracted_value || "—"

                            )}

                          </td>

                          <td>
                            <span className="confidence-label">
                              {Math.round(
                                (field.confidence_score || 0) * 100
                              )}%
                            </span>
                          </td>

                          <td>

                            {editingId === field.id ? (

                              <div className="action-buttons">

                                <button
                                  className="save-button"
                                  disabled={saving}
                                  onClick={() =>
                                    saveCorrection(field.id)
                                  }
                                >
                                  <Save size={15} />
                                  {saving ? "Saving..." : "Save"}
                                </button>

                                <button
                                  className="cancel-button"
                                  disabled={saving}
                                  onClick={cancelEditing}
                                >
                                  <X size={15} />
                                </button>

                              </div>

                            ) : (

                              <button
                                className="edit-button"
                                onClick={() => startEditing(field)}
                              >
                                <Pencil size={15} />
                                Edit
                              </button>

                            )}

                          </td>

                        </tr>

                      ))}

                    </tbody>

                  </table>

                </div>

              </div>

            </div>

          </>
        )}

      </div>

      {/* Improved Validation Overview */}
      <div className="table-container review-container">

        <div className="validation-heading">

          <div>
            <h2>Validation Overview</h2>

            <p>
              Cross-document verification results for this shipment.
            </p>
          </div>

          <span className="validation-total">
            {validationResults.length} Checks
          </span>

        </div>

        {/* Validation Counts */}
        <div className="validation-counts">

          <div className="validation-count-card count-match">
            <CheckCircle size={19} />
            <div>
              <strong>{matchCount}</strong>
              <span>Matched</span>
            </div>
          </div>

          <div className="validation-count-card count-mismatch">
            <AlertTriangle size={19} />
            <div>
              <strong>{mismatchCount}</strong>
              <span>Mismatches</span>
            </div>
          </div>

          <div className="validation-count-card count-not-checked">
            <Clock size={19} />
            <div>
              <strong>{notCheckedCount}</strong>
              <span>Not Checked</span>
            </div>
          </div>

        </div>

        {validationResults.length > 0 ? (

          <div className="validation-list">

            {validationResults.map((item) => (

              <div
                className={`validation-card ${getStatusClass(item.status)}`}
                key={item.id}
              >

                <div className="validation-card-header">

                  <div className="validation-title">
                    <strong>
                      {fieldLabel(item.field_name)}
                    </strong>

                    <span
                      className={`validation-status ${getStatusClass(item.status)}`}
                    >

                      {item.status === "MATCH" && (
                        <CheckCircle size={14} />
                      )}

                      {item.status === "MISMATCH" && (
                        <AlertTriangle size={14} />
                      )}

                      {item.status === "NOT_CHECKED" && (
                        <Clock size={14} />
                      )}

                      {item.status}

                    </span>
                  </div>

                  <span
                    className={`severity-badge ${getSeverityClass(item.severity)}`}
                  >
                    {item.severity || "Low"} Severity
                  </span>

                </div>

                <p className="validation-message">
                  {item.message}
                </p>

                <div className="compared-values">

                  <strong>Compared Values</strong>

                  <p>
                    {formatComparedValues(item.compared_values)}
                  </p>

                </div>

              </div>

            ))}

          </div>

        ) : (

          <div className="validation-empty">
            <FileText size={32} />

            <p>No validation results available.</p>

            <span>
              Process all three shipment documents to generate validation results.
            </span>
          </div>

        )}

      </div>

      {/* Correction History */}
      <div className="table-container review-container">

        <h2>
          <History size={20} />
          {" "}Correction History
        </h2>

        {historyLoading ? (

          <p>Loading correction history...</p>

        ) : historyError ? (

          <p className="error-message">{historyError}</p>

        ) : correctionHistory.length === 0 ? (

          <p>No corrections have been made yet.</p>

        ) : (

          <div className="review-table-scroll">

            <table className="review-table">

              <thead>
                <tr>
                  <th>Document</th>
                  <th>Field</th>
                  <th>Original Value</th>
                  <th>Corrected Value</th>
                  <th>Reason</th>
                  <th>Corrected At</th>
                </tr>
              </thead>

              <tbody>

                {correctionHistory.map((item) => (

                  <tr key={item.correction_id}>

                    <td>
                      <strong>{item.document_type}</strong>
                      <p>{item.document_name}</p>
                    </td>

                    <td>{fieldLabel(item.field_name)}</td>

                    <td>{item.old_value || "—"}</td>

                    <td>
                      <strong>
                        {item.corrected_value || "—"}
                      </strong>
                    </td>

                    <td>{item.correction_reason || "—"}</td>

                    <td>{formatDate(item.corrected_at)}</td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </div>

    </div>
  );
}

export default DocumentReview;
