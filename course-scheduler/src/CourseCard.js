import React from "react";
import "./CourseCard.css";

export default function CourseCard({ course }) {
  return (
    <div className="course-card">
      <div className="course-header">
        <strong>{course.name}</strong>
      </div>
      <div className="course-details">
        <div><strong>Department:</strong> {course.department}</div>
        <div><strong>Units:</strong> {course.units}</div>
        <div><strong>Days:</strong> {course.days}</div>
        <div><strong>Time:</strong> {course.startTime}–{course.endTime}</div>
        <div><strong>Location:</strong> {course.location || "TBD"}</div>
        <div><strong>Instructor:</strong> {course.instructor || "TBD"}</div>
      </div>
    </div>
  );
}
