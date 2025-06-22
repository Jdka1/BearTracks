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

  const handleGenerateSchedules = () => {
    const remainingReqs = majorRequirements[major].filter(
      (req) => !satisfied.includes(req)
    );

    const timeOptions = [
      ["MWF 9-10"],
      ["MWF 10-11"],
      ["MWF 11-12"],
      ["TuTh 9-10:30"],
      ["TuTh 11-12:30"],
      ["TuTh 1-2:30"],
      ["TuTh 3-4:30"],
    ];

    const allCourses = remainingReqs.map((req, idx) => {
      const timeBlock = timeOptions[idx % timeOptions.length];
      return {
        courseCode: req,
        courseName: `Course: ${req}`,
        department: major,
        description: "Auto-filled demo course",
        units: "4",
        days: timeBlock[0].split(" ")[0],
        startTime: timeBlock[0].split(" ")[1].split("-")[0],
        endTime: timeBlock[0].split(" ")[1].split("-")[1],
        times: timeBlock,
        location: "Dwinelle Hall",
        instructor: "Prof. AutoBot"
      };
    });

    const result = getSchedules(allCourses, 4).slice(0, 15); // limit to 15
    setSchedules(result);
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

      <button onClick={handleGenerateSchedules}>
        Generate Course Schedules
      </button>

      <br />
      <br />

      <div className="App">
        <h1>Sample Schedules</h1>

        {schedules.length > 0 ? (
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
