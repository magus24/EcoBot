import React, { useEffect, useState } from "react";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";
import "../table.css";
import "../navbar.css";
import searchicon from "../img/icons8-search-100.png";
import { api, currentUser, mediaUrl } from "../api.js";

const POLL_INTERVAL_MS = 5000;

function Table() {
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredData, setFilteredData] = useState([]);
  const [sortOrder, setSortOrder] = useState("asc");
  const [fullimg, setFullimg] = useState(null);
  const [show, setShow] = useState(false);
  const area = currentUser();

  const loadData = async () => {
    try {
      const response = await api.get(`/fetch/${area}`);
      setData(response.data.data);
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ detections", error);
    }
  };

  useEffect(() => {
    loadData();
    const intervalId = setInterval(loadData, POLL_INTERVAL_MS);
    return () => clearInterval(intervalId);
  }, [area]);

  // РџРѕРёСЃРє
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

  // РЎРѕСЂС‚РёСЂРѕРІРєР° РїРѕ РґР°С‚Рµ
  const sortData = () => {
    const sortedData = [...data];
    sortedData.sort((a, b) =>
      sortOrder === "asc" ? (a.date > b.date ? 1 : -1) : a.date < b.date ? 1 : -1
    );
    setData(sortedData);
    setSortOrder(sortOrder === "asc" ? "desc" : "asc");
  };

  // Verify: 0 <-> 1
  const handleVerify = async (row) => {
    try {
      await api.post(`/verify/${encodeURIComponent(row.image_path)}/${encodeURIComponent(row.location)}`);
      loadData();
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ РїРѕРґС‚РІРµСЂРґРёС‚СЊ detection", error);
    }
  };

  // Delete: РїРѕРјРµС‡Р°РµРј РєР°Рє СѓРґР°Р»С‘РЅРЅС‹Р№ (soft delete)
  const handleDelete = async (row) => {
    try {
      await api.post(`/temp_delete/${encodeURIComponent(row.image_path)}`);
      loadData();
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ СѓРґР°Р»РёС‚СЊ detection", error);
    }
  };

  const openFullImage = (row) => {
    setFullimg(mediaUrl(row.image_path));
    setShow(true);
  };

  return (
    <div className="content-wrap">
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
              <th>No</th>
              <th>Image</th>
              <th>
                Date
                <button className="short" onClick={sortData}>
                  {sortOrder === "asc" ? "в–І" : "в–ј"}
                </button>
              </th>
              <th>Time</th>
              <th>MAC Address</th>
              <th>Location</th>
              <th>Verify</th>
              <th>Delete</th>
            </tr>
          </thead>
          <tbody>
            {filteredData.map((row, index) => (
              <React.Fragment key={row.image_path}>
                <tr>
                  <td>{index + 1}</td>
                  <td>
                    <img
                      alt={`detection ${row.image_path}`}
                      width="200"
                      src={mediaUrl(row.image_path)}
                      onClick={() => openFullImage(row)}
                    />
                  </td>
                  <td>{row.date}</td>
                  <td>{row.time}</td>
                  <td>{row.mac_address}</td>
                  <td>{row.location}</td>
                  <td>
                    <Button variant="success" type="button" className="Verify" id="ve" onClick={() => handleVerify(row)}>
                      Verify
                    </Button>
                  </td>
                  <td>
                    <Button variant="danger" type="button" onClick={() => handleDelete(row)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      <Modal
        show={show}
        backdrop="static"
        keyboard={true}
        size="xl"
        onHide={() => setShow(false)}
        dialogClassName="modal-190w"
        aria-labelledby="detection-image-title"
      >
        <Modal.Header closeButton>
          <Modal.Title id="detection-image-title">Image Information</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <img alt="detection" width="600px" height="400px" src={fullimg || ""} />
        </Modal.Body>
      </Modal>
    </div>
  );
}

export default Table;
