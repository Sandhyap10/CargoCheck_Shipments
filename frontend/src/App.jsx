
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import Dashboard from "./pages/dashboard";
import Shipments from "./pages/shipments";
import ShipmentDetails from "./pages/shipmentdetails";
import DocumentReview from "./pages/Documentreview";

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />

        <main className="main-content">
          <Header />

          <Routes>
            <Route path="/" element={<Dashboard />} />

            <Route path="/shipments" element={<Shipments />} />

            <Route
              path="/shipments/:id"
              element={<ShipmentDetails />}
            />

            <Route
              path="/shipments/:id/review"
              element={<DocumentReview />}
            />

            <Route
              path="/review"
              element={<Navigate to="/shipments" replace />}
            />

            <Route
              path="*"
              element={<Navigate to="/" replace />}
            />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
