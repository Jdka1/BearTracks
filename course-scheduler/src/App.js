import React, { useState, useEffect } from "react";
import "./App.css";
import { supabase } from "./supabase";
import CourseCard from "./CourseCard";

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
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchRequirements = async () => {
      const { data, error } = await supabase
        .from("CourseRequirements")
        .select("*");
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
          reqMap[major] = Array.from(
            new Set((reqMap[major] || []).concat(reqs))
          );
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
      prev.includes(course)
        ? prev.filter((c) => c !== course)
        : [...prev, course]
    );
  };

  const handleGenerateSchedules = async () => {
    if (!major || !majorRequirements[major]) return;

    const notCompleted = majorRequirements[major].filter(
      (req) => !satisfied.includes(req)
    );

    const payload = {
      major,
      not_completed: notCompleted,
      user_input: preferences,
      num_courses: 4
    };

    setGenerating(true);
    setSchedules([]);

    try {
      const response = await fetch("http://192.168.86.40:5000/api/schedule", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      if (data && data.combinations) {
        setSchedules(data.combinations);
      } else {
        console.error("No combinations returned from API.");
      }
    } catch (error) {
      console.error("Failed to generate schedules:", error);
    } finally {
      setGenerating(false);
    }
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
        <label>Requirements already satisfied (check any):</label>
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
      <label>Preferences:</label>
      <textarea
        rows="3"
        value={preferences}
        onChange={(e) => setPreferences(e.target.value)}
        placeholder="e.g. No early morning classes, interested in machine learning. Want a balanced schedule with humanities/technical courses."
      />
    </div>


      <button onClick={handleGenerateSchedules}>
        Generate Course Schedules (only served locally)
      </button>

      <br />
      <br />

      <div className="App">
        <h1>Sample Schedules</h1>

        {generating ? (
          <p className="spinner">Generating schedules... (this may take ~30 seconds)</p>
        ) : schedules.length > 0 ? (
          <div className="scroll-container">
            <div className="scroll-track">
              {schedules.map((schedule, idx) => (
                <div key={idx} className="schedule-column">
                  {schedule.map((course, i) => (
                    <CourseCard key={i} course={course} />
                  ))}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p style={{ textAlign: "center" }}>No schedules yet.</p>
        )}
      </div>
    </div>
  );
}