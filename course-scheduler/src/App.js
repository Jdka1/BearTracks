import React, { useState, useEffect } from "react";
import "./App.css";
import { supabase } from "./supabase";


function hasTimeConflict(schedule) {
  const seen = new Set();
  for (const course of schedule) {
    for (const time of course.times) {
      if (seen.has(time)) return true;
      seen.add(time);
    }
  }
  return false;
}

function getSchedules(possibleCourses, size = 4) {
  const result = [];
  const dfs = (path, start) => {
    if (path.length === size) {
      if (!hasTimeConflict(path)) result.push([...path]);
      return;
    }
    for (let i = start; i < possibleCourses.length; i++) {
      path.push(possibleCourses[i]);
      dfs(path, i + 1);
      path.pop();
    }
  };
  dfs([], 0);
  return result;
}

export default function App() {
  const [major, setMajor] = useState("");
  const [satisfied, setSatisfied] = useState([]);
  const [preferences, setPreferences] = useState("");
  const [schedules, setSchedules] = useState([]);
  const [majorRequirements, setMajorRequirements] = useState({});
  const [availableMajors, setAvailableMajors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRequirements = async () => {
      const { data, error } = await supabase.from("CourseRequirements").select("*");
      if (error) {
        console.error("Supabase fetch error:", error.message);
        setLoading(false);
        return;
      }

      const reqMap = {};
      const majorsSeen = new Set();

      data.forEach(({ major, reqs }) => {
        if (!majorsSeen.has(major)) {
          reqMap[major] = Array.from(new Set(reqs));
          majorsSeen.add(major);
        } else {
          reqMap[major] = Array.from(new Set((reqMap[major] || []).concat(reqs)));
        }
      });

      const majors = Array.from(majorsSeen);
      setMajorRequirements(reqMap);
      setAvailableMajors(majors);
      setMajor(majors[0] || "");
      setLoading(false);
    };

    fetchRequirements();
  }, []);

  const handleCheckboxChange = (course) => {
    setSatisfied((prev) =>
      prev.includes(course) ? prev.filter((c) => c !== course) : [...prev, course]
    );
  };


  if (loading) return <div className="container">Loading requirements...</div>;

  return (
    <div className="container">
      <div className="header">
        <img src="/icon2.jpeg" alt="Logo" className="logo" />
        <h1>BearTracks</h1>
      </div>

      <div className="section">
        <label>Select Major:</label>
        <select
          value={major}
          onChange={(e) => {
            setMajor(e.target.value);
            setSatisfied([]);
            setSchedules([]);
          }}
        >
          {availableMajors.map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </div>

      <div className="section">
        <label>Requirements Already Satisfied (check any):</label>
        <div key={major} className="checkboxes">
          {majorRequirements[major]?.map((req) => (
            <label key={req} className="checkbox-item">
              <input
                type="checkbox"
                checked={satisfied.includes(req)}
                onChange={() => handleCheckboxChange(req)}
              />
              {req}
            </label>
          ))}
        </div>
      </div>

      <div className="section">
        <label>Preferences (e.g., “no early mornings”):</label>
        <textarea
          rows="3"
          value={preferences}
          onChange={(e) => setPreferences(e.target.value)}
        />
      </div>

      <button onClick={() => {}}>Generate Course Schedules</button>

      <div className="results">
        {schedules.map((schedule, idx) => (
          <div key={idx} className="schedule-card">
            <strong>Option {idx + 1}</strong>
            <ul>
              {schedule.map((c) => (
                <li key={c.code}>
                  {c.code} – {c.times.join(", ")}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
