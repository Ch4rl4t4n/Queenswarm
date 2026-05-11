export default function HiveHome() {
  const api =
    process.env.NEXT_PUBLIC_API_BASE ?? "http://backend:8000/api/v1";
  return (
    <main className="hive-main">
      <h1 className="hive-title">Queenswarm</h1>
      <p className="hive-sub">
        Bee-hive dashboard shell. API base:{" "}
        <code className="hive-code">{api}</code>
      </p>
    </main>
  );
}
