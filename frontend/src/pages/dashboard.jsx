
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Package,
  CheckCircle,
  Clock,
  AlertTriangle,
  RefreshCw,
  ArrowRight,
} from "lucide-react";

import API from "../services/api";
import StatCard from "../components/StatCard";

function Dashboard() {
  const navigate = useNavigate();

  const [shipments, setShipments] = useState([]);
  const [reportStats, setReportStats] = useState({
    completed: 0,
    pending: 0,
    attentionRequired: 0,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const response = await API.get("/shipments/");
      const shipmentList = Array.isArray(response.data)
        ? response.data
        : response.data.shipments || [];

      setShipments(shipmentList);

      let completed = 0;
      let pending = 0;
      let attentionRequired = 0;

      shipmentList.forEach((shipment) => {
        const status = shipment.status?.toLowerCase();

        if (status === "completed") {
          completed++;
        } else if (status === "attention required") {
          attentionRequired++;
        } else {
          pending++;
        }
      });

      setReportStats({
        completed,
        pending,
        attentionRequired,
      });
    } catch (err) {
      console.error("Dashboard error:", err);
      setError(
        "Unable to load shipments. Please check whether the backend is running."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const getStatusClass = (status) => {
    const normalizedStatus = status?.toLowerCase();

    if (normalizedStatus === "completed") {
      return "dashboard-status completed";
    }

    if (normalizedStatus === "attention required") {
      return "dashboard-status attention";
    }

    return "dashboard-status pending";
  };

  const recentShipments = [...shipments]
    .sort((a, b) => {
      return (
        new Date(b.created_at || 0).getTime() -
        new Date(a.created_at || 0).getTime()
      );
    })
    .slice(0, 5);

  return (
    <div className="dashboard-content">

      {/* Welcome Section */}
      <div className="welcome-section dashboard-welcome">
        <div>
          <h1>Welcome back!</h1>
          <p>
            Here's what's happening with your shipments today.
          </p>
        </div>

        <button
          className="dashboard-refresh-button"
          onClick={fetchDashboardData}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "refresh-spinning" : ""}
          />
          Refresh
        </button>
      </div>

      {/* Statistics */}
      <div className="stats-grid">

        <StatCard
          title="Total Shipments"
          value={loading ? "..." : shipments.length}
          description="All registered shipments"
          icon={Package}
        />

        <StatCard
          title="Completed"
          value={loading ? "..." : reportStats.completed}
          description="Successfully processed"
          icon={CheckCircle}
        />

        <StatCard
          title="Pending"
          value={loading ? "..." : reportStats.pending}
          description="Awaiting processing"
          icon={Clock}
        />

        <StatCard
          title="Attention Required"
          value={loading ? "..." : reportStats.attentionRequired}
          description="Validation discrepancies"
          icon={AlertTriangle}
        />

      </div>

      {/* Recent Shipments */}
      <div className="table-container dashboard-table-container">

        <div className="section-heading dashboard-section-heading">
          <div>
            <h2>Recent Shipments</h2>
            <p>Your latest shipment records</p>
          </div>

          <button
            className="dashboard-view-all"
            onClick={() => navigate("/shipments")}
          >
            View All
            <ArrowRight size={16} />
          </button>
        </div>

        {loading ? (
          <div className="dashboard-state">
            <RefreshCw size={20} className="refresh-spinning" />
            <p>Loading shipments...</p>
          </div>
        ) : error ? (
          <div className="dashboard-state dashboard-error">
            <AlertTriangle size={22} />
            <p>{error}</p>
            <button onClick={fetchDashboardData}>
              Try Again
            </button>
          </div>
        ) : shipments.length === 0 ? (
          <div className="dashboard-state">
            <Package size={28} />
            <h3>No shipments yet</h3>
            <p>Create your first shipment to get started.</p>
            <button
              onClick={() => navigate("/shipments")}
              className="dashboard-view-all"
            >
              Go to Shipments
              <ArrowRight size={16} />
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table className="dashboard-table">

              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Importer</th>
                  <th>Supplier</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {recentShipments.map((shipment) => (
                  <tr
                    key={shipment.id}
                    onClick={() =>
                      navigate(`/shipments/${shipment.id}`)
                    }
                    className="dashboard-clickable-row"
                  >
                    <td className="dashboard-shipment-id">
                      {shipment.shipment_id}
                    </td>

                    <td>
                      {shipment.importer_name || "—"}
                    </td>

                    <td>
                      {shipment.supplier_name || "—"}
                    </td>

                    <td>
                      <span className={getStatusClass(shipment.status)}>
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

export default Dashboard;
