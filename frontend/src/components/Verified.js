import React, { useEffect, useState } from "react";
import Modal from "react-bootstrap/Modal";
import Button from "react-bootstrap/Button";
import "../table.css";
import "../navbar.css";
import searchicon from "../img/icons8-search-100.png";
import { api, currentUser, mediaUrl } from "../api.js";

const POLL_INTERVAL_MS = 5000;

function Verified() {
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredData, setFilteredData] = useState([]);
  const [sortOrder, setSortOrder] = useState("asc");
  const [fullimg, setFullimg] = useState(null);
  const [show, setShow] = useState(false);
  const area = currentUser();

  const loadData = async () => {
    try {
      const response = await api.get(`/fetchv/${area}`);
      setData(response.data.data);
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ РїРѕРґС‚РІРµСЂР¶РґС‘РЅРЅС‹Рµ detections", error);
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

  // РЎРЅСЏС‚СЊ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ: РІРѕР·РІСЂР°С‰Р°РµРј detection РІ СЃС‚Р°С‚СѓСЃ В«РЅРѕРІРѕРµВ»
  const handleUnverify = async (row) => {
    try {
      await api.post(`/verify/${encodeURIComponent(row.image_path)}/${encodeURIComponent(row.location)}`);
      loadData();
    } catch (error) {
      console.error("РќРµ СѓРґР°Р»РѕСЃСЊ СЃРЅСЏС‚СЊ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёРµ", error);
    }
  };

  const openFullImage = (row) => {
    setFullimg(mediaUrl(row.image_path));
    setShow(true);
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
              <th>Verified</th>
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
                    <Button
                      type="button"
                      variant="success"
                      className="Verify"
                      onClick={() => handleUnverify(row)}
                    >
                      Verified
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
        aria-labelledby="verified-image-title"
      >
        <Modal.Header closeButton>
          <Modal.Title id="verified-image-title">Image Information</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <img alt="detection" width="600px" height="400px" src={fullimg || ""} />
        </Modal.Body>
      </Modal>
    </>
  );
}

export default Verified;
