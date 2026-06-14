"use client";

import { useEffect, useState } from "react";

export default function TokenInput() {
  const [token, setToken] = useState("");

  useEffect(() => {
    const t = localStorage.getItem("INVIGI_TOKEN") || "";
    setToken(t);
  }, []);

  const save = () => {
    localStorage.setItem("INVIGI_TOKEN", token.trim());
  };

  return (
    <div className="card mb-6">
      <div className="card-header">Bearer Token</div>
      <div className="card-body flex flex-col gap-3 md:flex-row">
        <input
          className="input"
          placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button className="btn btn-primary" onClick={save}>Save</button>
      </div>
    </div>
  );
}
