
import { useEffect, useState } from "react";
import {
  Plus,
  Search,
  Package,
  X,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import API from "../services/api";

function Shipments() {
  const [shipments, setShipments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [shipmentIdError, setShipmentIdError] = useState("");

  const navigate = useNavigate();

  const [form, setForm] = useState({
    shipment_id: "",
    importer_name: "",
    supplier_name: "",
    shipment_date: "",
    status: "Pending",
  });

  const shipmentIdPattern = /^SHP-\d{3}$/;

  const fetchShipments = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await API.get("/shipments/");
      const data = response.data;

      setShipments(
        Array.isArray(data) ? data : data.shipments || []
      );
    } catch (err) {
      console.error("Shipment loading error:", err);
      setError("Could not load shipments. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShipments();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));

    if (name === "shipment_id") {
      const trimmedValue = value.trim();

      if (!trimmedValue) {
        setShipmentIdError("Shipment ID is required.");
      } else if (!shipmentIdPattern.test(trimmedValue)) {
        setShipmentIdError(
          "Enter a valid Shipment ID, e.g. SHP-172."
        );
      } else {
        setShipmentIdError("");
      }
    }

    setError("");
  };

  const getApiErrorMessage = (err) => {
    const detail = err.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "string"
            ? item
            : item.msg || "Invalid input"
        )
        .join(". ");
    }

    if (detail && typeof detail === "object") {
      return detail.msg || "Please check the entered information.";
    }

    return "Unable to create shipment. Please try again.";
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setSuccess("");

    const shipmentId = form.shipment_id.trim();

    if (!shipmentIdPattern.test(shipmentId)) {
      setShipmentIdError(
        "Enter a valid Shipment ID, e.g. SHP-172."
      );
      return;
    }

    const duplicate = shipments.some(
      (shipment) =>
        shipment.shipment_id?.toLowerCase() ===
        shipmentId.toLowerCase()
    );

    if (duplicate) {
      setError("This Shipment ID already exists. Please enter another ID.");
      return;
    }

    setShipmentIdError("");

    try {
      await API.post("/shipments/", {
        ...form,
        shipment_id: shipmentId,
      });

      setSuccess("Shipment created successfully!");

      setForm({
        shipment_id: "",
        importer_name: "",
        supplier_name: "",
        shipment_date: "",
        status: "Pending",
      });

      setShipmentIdError("");
      setShowForm(false);

      await fetchShipments();
    } catch (err) {
      console.error("Shipment creation error:", err);

      setError(getApiErrorMessage(err));
      setShowForm(true);
    }
  };

  // Search and status filtering
  const filteredShipments = shipments.filter((shipment) => {
    const searchText = search.trim().toLowerCase();

    const matchesSearch = [
      shipment.shipment_id,
      shipment.importer_name,
      shipment.supplier_name,
    ].some((value) =>
      String(value || "").toLowerCase().includes(searchText)
    );

    const shipmentStatus = (
      shipment.status || "Pending"
    ).toLowerCase();

    const matchesStatus =
      statusFilter === "All" ||
      shipmentStatus === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  const clearFilters = () => {
    setSearch("");
    setStatusFilter("All");
  };

  const getStatusClass = (status) => {
    const normalizedStatus = status?.toLowerCase();

    if (normalizedStatus === "completed") {
      return "shipment-status completed";
    }

    if (normalizedStatus === "attention required") {
      return "shipment-status attention";
    }

    return "shipment-status pending";
  };

  return (
    <div className="dashboard-content shipments-page">

      {/* Page Heading */}
      <div className="page-heading shipments-heading">
        <div>
          <h1>Shipments</h1>
          <p>
            Manage and monitor all your import shipments.
          </p>
        </div>

        <button
          className="primary-button shipments-create-button"
          onClick={() => {
            setShowForm(!showForm);
            setError("");
            setSuccess("");
            setShipmentIdError("");
          }}
        >
          <Plus size={18} />
          New Shipment
        </button>
      </div>

      {error && (
        <div
          className="shipment-alert error-message"
          role="alert"
        >
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div
          className="shipment-alert success-message"
          role="status"
        >
          <CheckCircle size={18} />
          <span>{success}</span>
        </div>
      )}

      {/* Create Shipment Form */}
      {showForm && (
        <div className="form-container shipment-form">
          <h2>Create New Shipment</h2>

          <form onSubmit={handleSubmit} noValidate>
            <div className="form-grid">

              <label>
                Shipment ID *

                <input
                  name="shipment_id"
                  value={form.shipment_id}
                  onChange={handleChange}
                  placeholder="e.g. SHP-172"
                  required
                  maxLength={7}
                  aria-invalid={Boolean(shipmentIdError)}
                  aria-describedby="shipment-id-error"
                  autoComplete="off"
                />

                {shipmentIdError && (
                  <span
                    id="shipment-id-error"
                    className="shipment-field-error"
                    role="alert"
                  >
                    <AlertCircle size={14} />
                    {shipmentIdError}
                  </span>
                )}

                <small className="shipment-field-hint">
                  Format: SHP- followed by exactly 3 digits.
                </small>
              </label>

              <label>
                Importer Name *

                <input
                  name="importer_name"
                  value={form.importer_name}
                  onChange={handleChange}
                  placeholder="Enter importer"
                  required
                />
              </label>

              <label>
                Supplier Name *

                <input
                  name="supplier_name"
                  value={form.supplier_name}
                  onChange={handleChange}
                  placeholder="Enter supplier"
                  required
                />
              </label>

              <label>
                Shipment Date

                <input
                  type="date"
                  name="shipment_date"
                  value={form.shipment_date}
                  onChange={handleChange}
                />
              </label>

            </div>

            <div className="form-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setShowForm(false);
                  setError("");
                  setShipmentIdError("");
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
                disabled={
                  !shipmentIdPattern.test(form.shipment_id.trim()) ||
                  Boolean(shipmentIdError)
                }
              >
                Create Shipment
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Shipments Table */}
      <div className="table-container shipments-table-container">

        <div className="shipment-toolbar">
          <div>
            <h2>All Shipments</h2>
            <p>
              Showing {filteredShipments.length} of{" "}
              {shipments.length} shipments
            </p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="shipment-filters">

          <div className="search-box shipment-search">
            <Search size={18} />

            <input
              placeholder="Search ID, importer or supplier..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            {search && (
              <button
                type="button"
                className="clear-search"
                onClick={() => setSearch("")}
                title="Clear search"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <select
            className="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="All">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="Completed">Completed</option>
            <option value="Attention Required">
              Attention Required
            </option>
          </select>

          {(search || statusFilter !== "All") && (
            <button
              className="secondary-button clear-filters-button"
              onClick={clearFilters}
            >
              Clear Filters
            </button>
          )}

        </div>

        {loading ? (
          <p className="message shipments-message">
            Loading shipments...
          </p>
        ) : error && shipments.length === 0 ? (
          <div className="empty-state">
            <Package size={35} />
            <p>Unable to load shipments.</p>
            <button
              className="secondary-button"
              onClick={fetchShipments}
            >
              Try Again
            </button>
          </div>
        ) : filteredShipments.length === 0 ? (
          <div className="empty-state shipments-empty-state">
            <Package size={35} />
            <h3>No shipments found</h3>
            <p>
              Try changing your search or status filter.
            </p>
            <button
              className="secondary-button"
              onClick={clearFilters}
            >
              Clear Filters
            </button>
          </div>
        ) : (

          <div className="table-scroll">
            <table className="shipments-table">

              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Importer</th>
                  <th>Supplier</th>
                  <th>Date</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {filteredShipments.map((shipment) => (
                  <tr key={shipment.id}>

                    <td>
                      <button
                        className="shipment-link"
                        onClick={() =>
                          navigate(`/shipments/${shipment.id}`)
                        }
                      >
                        {shipment.shipment_id}
                      </button>
                    </td>

                    <td>
                      {shipment.importer_name || "—"}
                    </td>

                    <td>
                      {shipment.supplier_name || "—"}
                    </td>

                    <td>
                      {shipment.shipment_date || "—"}
                    </td>

                    <td>
                      <span
                        className={getStatusClass(shipment.status)}
                      >
                        <span className="status-dot"></span>
                        {shipment.status || "Pending"}
                      </span>
                    </td>

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

export default Shipments;
