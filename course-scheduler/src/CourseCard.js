import React from "react";
import "./CourseCard.css";

export default function CourseCard({ course }) {
  if (!course) return null;

  return (
    <div className="course-card-hover">
      <div className="course-card">
        <h2>{course.courseCode}: {course.courseName}</h2>
        <p><strong>Department:</strong> {course.department}</p>
        <p><strong>Description:</strong> {course.description}</p>
        <p><strong>Units:</strong> {course.units}</p>
        <p><strong>Schedule:</strong> {course.days} {course.startTime} – {course.endTime}</p>
        <p><strong>Location:</strong> {course.location}</p>
        <p><strong>Instructor:</strong> {course.instructor}</p>
      </div>
    </div>
  );
}
