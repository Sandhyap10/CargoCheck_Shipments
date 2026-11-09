
function StatCard({ title, value, description, icon: Icon }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <span className="stat-title">{title}</span>

        <div className="stat-icon">
          <Icon size={21} strokeWidth={2} />
        </div>
      </div>

      <h2 className="stat-value">{value}</h2>

      <p className="stat-description">{description}</p>
    </div>
  );
}

export default StatCard;
