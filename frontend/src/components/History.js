import React, { useEffect, useState } from "react";
import "../table.css";
import "../navbar.css";
import searchicon from "../img/icons8-search-100.png";
import { api, currentUser } from "../api.js";

const POLL_INTERVAL_MS = 5000;

function History() {
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredData, setFilteredData] = useState([]);
  const [sortOrder, setSortOrder] = useState("asc");
  const area = currentUser();

  const loadData = async () => {
    try {
      const response = await api.get(`/fetchv/${area}`);
      setData(response.data.data);
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ РёСЃС‚РѕСЂРёСЋ", error);
    }
  };

  useEffect(() => {
    loadData();
    const intervalId = setInterval(loadData, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [area]);

  const handleSearch = (event) => {
    setSearchTerm(event.target.value);
  };

  useEffect(() => {
    const query = searchTerm.toLowerCase();
    setFilteredData(
      data.filter(
        (row) =>
          (row.location || "").toLowerCase().includes(query) ||
          (row.time || "").toLowerCase().includes(query) ||
          (row.mac_address || "").toLowerCase().includes(query)
      )
    );
  }, [searchTerm, data]);

  const sortData = () => {
    const sortedData = [...data];
    sortedData.sort((a, b) =>
      sortOrder === "asc" ? (a.date > b.date ? 1 : -1) : a.date < b.date ? 1 : -1
    );
    setData(sortedData);
    setSortOrder(sortOrder === "asc" ? "desc" : "asc");
  };

  return (
    <>
      <div className="tbbar">
        <img src={searchicon} className="search_icon" alt="search" />
        <input
          className="search"
          type="text"
          placeholder="Search..."
          onChange={handleSearch}
        />
      </div>

      <div id="table-users">
        <table>
          <thead>
            <tr>
              <th className="History">No</th>
              <th className="History">
                Date{" "}
                <button className="short" onClick={sortData}>
                  {sortOrder === "asc" ? "в–І" : "в–ј"}
                </button>
              </th>
              <th className="History">Time</th>
              <th className="History">MAC Address</th>
              <th className="History">Location</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, index) => (
              <tr key={`${row.image_path}-${index}`}>
                <td>{index + 1}</td>
                <td>{row.date}</td>
                <td>{row.time}</td>
                <td>{row.mac_address}</td>
                <td>{row.location}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default History;
