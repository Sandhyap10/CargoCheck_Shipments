
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Search, Package, X } from "lucide-react";

function Header() {
  const navigate = useNavigate();

  const [shipments, setShipments] = useState([]);
  const [search, setSearch] = useState("");
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const searchRef = useRef(null);

  // Fetch shipments from backend
  useEffect(() => {
    const fetchShipments = async () => {
      try {
        setLoading(true);

        const response = await axios.get(
          "http://127.0.0.1:8000/shipments/"
        );

        const data = response.data;
        setShipments(Array.isArray(data) ? data : data.shipments || []);
      } catch (err) {
        console.error("Failed to fetch shipments:", err);
        setError("Unable to load shipments");
      } finally {
        setLoading(false);
      }
    };

    fetchShipments();
  }, []);

  // Filter shipments
  const filteredShipments = shipments.filter((shipment) => {
    const query = search.toLowerCase().trim();

    return (
      String(shipment.shipment_id || "").toLowerCase().includes(query) ||
      String(shipment.importer_name || "").toLowerCase().includes(query) ||
      String(shipment.supplier_name || "").toLowerCase().includes(query)
    );
  });

  // Open shipment details
  const handleShipmentClick = (shipment) => {
    navigate(`/shipments/${shipment.id}`);
    setSearch("");
    setShowResults(false);
  };

  // Close search results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        searchRef.current &&
        !searchRef.current.contains(event.target)
      ) {
        setShowResults(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  return (
    <header className="header">
      <div>
        <h2>Dashboard</h2>
        <p>Monitor and manage your shipments</p>
      </div>

      <div className="header-actions">

        {/* Shipment Search */}
        <div className="header-search-wrapper" ref={searchRef}>
          <div className="search-box">
            <Search size={18} />

            <input
              type="text"
              placeholder="Search shipments..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setShowResults(true);
              }}
              onFocus={() => setShowResults(true)}
            />

            {search && (
              <button
                className="search-clear"
                onClick={() => {
                  setSearch("");
                  setShowResults(false);
                }}
                aria-label="Clear search"
              >
                <X size={16} />
              </button>
            )}
          </div>

          {showResults && search.trim() && (
            <div className="search-results">
              {loading ? (
                <p className="search-message">
                  Loading shipments...
                </p>
              ) : error ? (
                <p className="search-message">{error}</p>
              ) : filteredShipments.length > 0 ? (
                filteredShipments.slice(0, 8).map((shipment) => (
                  <button
                    key={shipment.id}
                    className="search-result-item"
                    onClick={() => handleShipmentClick(shipment)}
                  >
                    <div className="search-result-icon">
                      <Package size={18} />
                    </div>

                    <div className="search-result-info">
                      <strong>{shipment.shipment_id}</strong>

                      <span>
                        {shipment.importer_name || "Unknown importer"}
                      </span>

                      <small>
                        Supplier: {shipment.supplier_name || "Not available"}
                      </small>
                    </div>
                  </button>
                ))
              ) : (
                <p className="search-message">
                  No matching shipments found.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Simple Admin Identity */}
        <div className="user-profile">
          <div className="avatar">A</div>
          <span>Admin</span>
        </div>

      </div>
    </header>
  );
}

export default Header;
