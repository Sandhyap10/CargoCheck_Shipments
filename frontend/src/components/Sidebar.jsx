
import {
  LayoutDashboard,
  Package,
  Settings,
  Ship,
} from "lucide-react";
import { NavLink } from "react-router-dom";

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <Ship size={27} />
        <h2>CargoCheck AI</h2>
      </div>

      <p className="menu-label">WORKSPACE</p>

      <nav>
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <LayoutDashboard size={19} />
          Dashboard
        </NavLink>

        <NavLink
          to="/shipments"
          className={({ isActive }) =>
            isActive ? "nav-link active" : "nav-link"
          }
        >
          <Package size={19} />
          Shipments
        </NavLink>
      </nav>
</aside>
  );
}

export default Sidebar;
